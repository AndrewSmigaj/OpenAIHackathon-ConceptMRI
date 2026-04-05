"""
Agent session endpoints — start, generate, stop.

The generate endpoint is the core Phase 4 pipeline:
generate text → parse harmony channels → forward pass with hooks →
extract at all target positions → write to Parquet → return analysis + action.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import torch
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_capture_service
from api.schemas import (
    AgentStartRequest, AgentStartResponse,
    AgentStopRequest, AgentStopResponse,
    AgentGenerateRequest, AgentGenerateResponse,
)
from services.probes.integrated_capture_service import IntegratedCaptureService, SessionState
from services.probes.probe_ids import generate_capture_id
from services.agent.harmony_parser import parse_harmony_channels

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/start", response_model=AgentStartResponse)
async def start_agent_session(
    request: AgentStartRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Create a new agent capture session."""
    session_id = service.session_mgr.create_agent_session(
        session_name=request.session_name,
        scenario_id=request.scenario_id,
        target_words=request.target_words,
        bootstrap_session_id=request.bootstrap_session_id,
        agent_name=request.agent_name,
        capture_type_config=request.capture_type_config,
    )

    return AgentStartResponse(
        session_id=session_id,
        session_name=request.session_name,
        target_words=request.target_words,
        scenario_id=request.scenario_id,
    )


@router.post("/stop", response_model=AgentStopResponse)
async def stop_agent_session(
    request: AgentStopRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Stop and finalize an agent session."""
    session_id = request.session_id

    status = service.session_mgr.validate_active_session(session_id)
    total_turns = status.current_turn_id

    # Flush and close writers
    if session_id in service.session_writers:
        service.session_writers[session_id].close_all()
        del service.session_writers[session_id]

    # Finalize session (writes manifest, updates state)
    service.session_mgr.finalize_session(session_id)

    return AgentStopResponse(
        session_id=session_id,
        state="completed",
        total_turns=total_turns,
    )


@router.post("/generate", response_model=AgentGenerateResponse)
async def agent_generate(
    request: AgentGenerateRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Execute one agent generate tick.

    Sequence: generate (hooks OFF) → parse harmony → forward pass (hooks ON) →
    extract at all target positions → write Parquet → return analysis + action.
    """
    session_id = request.session_id

    # 1. Validate session
    status = service.session_mgr.validate_active_session(session_id)
    session_file = service.session_mgr.sessions_dir / f"{session_id}.json"
    with open(session_file, "r") as f:
        metadata = json.load(f)
    if metadata.get("experiment_type") != "agent":
        raise HTTPException(status_code=400, detail="Session is not an agent session")

    # 2. Increment turn_id
    turn_id = status.current_turn_id
    status.current_turn_id += 1
    scenario_id = metadata.get("scenario_id", "")

    # 3. Tokenize prompt
    prompt_token_ids = service.processor.tokenizer.encode(
        request.prompt, add_special_tokens=False
    )
    prompt_token_count = len(prompt_token_ids)
    input_tensor = torch.tensor(
        [prompt_token_ids], device=service.orchestrator.model.device
    )

    # 4. Generate continuation (hooks OFF) — returns text + token IDs
    service.orchestrator.initialize_hooks(session_id)
    generated_text, generated_token_ids = service.orchestrator.generate_continuation_with_ids(
        input_tensor, max_new_tokens=request.max_new_tokens
    )

    # 5. Parse harmony channels
    channels = parse_harmony_channels(generated_text)

    # 6. Concatenate token ID lists (no BPE re-tokenization)
    full_token_ids = prompt_token_ids + generated_token_ids
    total_tokens = len(full_token_ids)
    full_tensor = torch.tensor(
        [full_token_ids], device=service.orchestrator.model.device
    )

    # 7. Forward pass with hooks ON
    service.orchestrator.clear_captured_data()
    service.orchestrator.run_forward_pass(full_tensor)

    # 8. Get captured data
    routing_data, embedding_data, residual_data = service.orchestrator.get_captured_data()

    # 9-11. Find target positions, convert to schemas, write to Parquet
    capture_id = generate_capture_id("capture")
    target_positions = {}

    # Ensure writers exist
    if session_id not in service.session_writers:
        from services.probes.integrated_capture_service import SessionBatchWriters
        service.session_writers[session_id] = SessionBatchWriters(
            session_id, service.session_mgr.data_lake_path,
            service.session_mgr.batch_size
        )

    for word in request.target_words:
        positions = service.processor.find_all_word_token_positions(full_token_ids, word)
        if not positions:
            logger.info(f"Target word '{word}' not found in tick {turn_id} — skipping")
            target_positions[word] = []
            continue

        word_positions = []
        for pos, token_id in positions:
            probe_id = generate_capture_id("probe")
            probe_data = service.processor.convert_to_schemas(
                probe_id=probe_id,
                session_id=session_id,
                input_text=request.prompt + generated_text,
                target_word=word,
                target_token_id=token_id,
                target_token_position=pos,
                total_tokens=total_tokens,
                routing_data=routing_data,
                embedding_data=embedding_data,
                residual_stream_data=residual_data,
                turn_id=turn_id,
                scenario_id=scenario_id,
                capture_type="reasoning",
            )
            service.session_writers[session_id].write_probe_data(probe_data)
            service.session_mgr.record_probe_success(session_id)
            word_positions.append(pos)

        target_positions[word] = word_positions

    # 12. Knowledge probe (optional)
    knowledge_capture_id = None
    if request.knowledge_probe:
        try:
            knowledge_probe_id, _ = service.capture_probe(
                session_id=session_id,
                input_text=request.knowledge_probe,
                target_word=request.target_words[0] if request.target_words else "",
                turn_id=turn_id,
                scenario_id=scenario_id,
                capture_type="knowledge_query",
            )
            knowledge_capture_id = knowledge_probe_id
        except Exception as e:
            logger.error(f"Knowledge probe failed for tick {turn_id}: {e}")

    # 13. Write tick log
    session_dir = Path(service.session_mgr.data_lake_path) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    tick_entry = {
        "turn_id": turn_id,
        "prompt": request.prompt,
        "analysis": channels["analysis"],
        "action": channels["action"],
        "capture_id": capture_id,
        "knowledge_capture_id": knowledge_capture_id,
        "generated_text": generated_text,
        "prompt_token_count": prompt_token_count,
        "target_positions": target_positions,
        "timestamp": datetime.now().isoformat(),
    }
    with open(session_dir / "tick_log.jsonl", "a") as f:
        f.write(json.dumps(tick_entry) + "\n")

    # 14. Return response
    return AgentGenerateResponse(
        analysis=channels["analysis"],
        action=channels["action"],
        capture_id=capture_id,
        generated_text=generated_text,
        turn_id=turn_id,
        knowledge_capture_id=knowledge_capture_id,
    )
