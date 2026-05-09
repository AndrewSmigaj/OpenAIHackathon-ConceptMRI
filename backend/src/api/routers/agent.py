"""
Agent session endpoints — start, generate, stop.

The generate endpoint is the core Phase 4 pipeline:
generate text → parse harmony channels → forward pass with hooks →
extract at all target positions → write to Parquet → return analysis + action.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import torch
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_capture_service
from api.schemas import (
    AgentStartRequest, AgentStartResponse,
    AgentStopRequest, AgentStopResponse,
    AgentGenerateRequest, AgentGenerateResponse,
    AgentResumeRequest,
)
from services.probes.integrated_capture_service import IntegratedCaptureService, SessionState
from services.probes.probe_ids import generate_capture_id
from services.agent.harmony_parser import parse_harmony_channels
from services.agent.agent_loop import AgentLoop, DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# Single-agent enforcement: only one loop at a time (single GPU, single model)
_active_loops: Dict[str, AgentLoop] = {}
_active_tasks: Dict[str, asyncio.Task] = {}


async def _run_and_cleanup(loop: AgentLoop, session_id: str, service: IntegratedCaptureService):
    """Wrap agent loop with cleanup on natural completion."""
    try:
        await loop.run()
    except Exception:
        logger.error(f"Agent loop crashed for {session_id}", exc_info=True)
    finally:
        _active_loops.pop(session_id, None)
        _active_tasks.pop(session_id, None)
        if session_id in service.session_writers:
            service.session_writers[session_id].close_all()
            del service.session_writers[session_id]
        try:
            service.session_mgr.finalize_session(session_id)
        except Exception:
            logger.error(f"Failed to finalize {session_id}", exc_info=True)


@router.post("/start", response_model=AgentStartResponse)
async def start_agent_session(
    request: AgentStartRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Create a new agent capture session."""
    # Single-agent enforcement
    if _active_loops:
        active_id = next(iter(_active_loops))
        raise HTTPException(
            status_code=409,
            detail=f"Agent loop already running for session {active_id}. Stop it first.",
        )

    session_id = service.session_mgr.create_agent_session(
        session_name=request.session_name,
        scenario_id=request.scenario_id,
        target_words=request.target_words,
        bootstrap_session_id=request.bootstrap_session_id,
        agent_name=request.agent_name,
        capture_type_config=request.capture_type_config,
    )

    # Launch agent loop as background task if requested
    if request.auto_start:
        loop = AgentLoop(
            session_id=session_id,
            scenario_id=request.scenario_id,
            target_words=request.target_words,
            agent_name=request.agent_name,
            service=service,
            scenario_list=request.scenario_list,
            data_lake_path=str(service.data_lake_path),
            evennia_username=request.evennia_username,
            evennia_password=request.evennia_password,
            system_prompt=request.system_prompt,
            session_name=request.session_name,
        )
        task = asyncio.create_task(_run_and_cleanup(loop, session_id, service))
        _active_loops[session_id] = loop
        _active_tasks[session_id] = task
        logger.info(f"Auto-started agent loop for session {session_id}")

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

    # Stop the agent loop if running
    if session_id in _active_loops:
        await _active_loops[session_id].stop()
        # Wait for the task to finish (with timeout)
        task = _active_tasks.get(session_id)
        if task and not task.done():
            try:
                await asyncio.wait_for(task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(f"Agent loop task for {session_id} did not stop within 10s")
                task.cancel()
        _active_loops.pop(session_id, None)
        _active_tasks.pop(session_id, None)
        logger.info(f"Stopped agent loop for session {session_id}")

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


@router.post("/resume", response_model=AgentStartResponse)
async def resume_agent_session(
    request: AgentResumeRequest,
    service: IntegratedCaptureService = Depends(get_capture_service),
):
    """Resume a completed agent session with additional scenarios."""
    if _active_loops:
        active_id = next(iter(_active_loops))
        raise HTTPException(
            status_code=409,
            detail=f"Agent loop already running for session {active_id}. Stop it first.",
        )

    try:
        status = service.session_mgr.reactivate_session(request.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    session_file = service.session_mgr.sessions_dir / f"{request.session_id}.json"
    with open(session_file, "r") as f:
        metadata = json.load(f)

    loop = AgentLoop(
        session_id=request.session_id,
        scenario_id=metadata.get("scenario_id", ""),
        target_words=metadata.get("target_words", []),
        agent_name=metadata.get("agent_name", "agent"),
        service=service,
        scenario_list=request.scenario_list,
        data_lake_path=str(service.data_lake_path),
        evennia_username=request.evennia_username,
        evennia_password=request.evennia_password,
        system_prompt=request.system_prompt,
        session_name=metadata.get("session_name", request.session_id),
    )
    task = asyncio.create_task(_run_and_cleanup(loop, request.session_id, service))
    _active_loops[request.session_id] = loop
    _active_tasks[request.session_id] = task
    logger.info(f"Resumed agent loop for session {request.session_id} with {len(request.scenario_list)} scenarios")

    return AgentStartResponse(
        session_id=request.session_id,
        session_name=metadata.get("session_name", ""),
        target_words=metadata.get("target_words", []),
        scenario_id=metadata.get("scenario_id", ""),
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

    # 3. Tokenize prompt with Harmony chat template
    tokenizer = service.orchestrator.tokenizer
    messages = [
        {"role": "developer", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": request.prompt},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        return_dict=True, return_tensors="pt",
        model_identity="You are an agent exploring a world.",
    )
    prompt_token_ids = inputs["input_ids"][0].tolist()
    prompt_token_count = len(prompt_token_ids)

    # 4. Generate continuation (hooks OFF) — returns text + token IDs
    generated_text, generated_token_ids = service.generate(
        prompt_token_ids, max_new_tokens=request.max_new_tokens,
        skip_special_tokens=False,
    )

    # 5. Parse harmony channels
    channels = parse_harmony_channels(generated_text)

    # 6. Concatenate prompt + generation; capture all target occurrences,
    #    labeling positions >= prompt_token_count as "generation".
    full_token_ids = prompt_token_ids + generated_token_ids

    capture_id = generate_capture_id("capture")
    records, _ = service.capture_step(
        session_id, full_token_ids, request.target_words,
        target_occurrence="all",
        prompt_token_count=prompt_token_count,
        metadata={
            "turn_id": turn_id,
            "scenario_id": scenario_id,
            "input_text": request.prompt + generated_text,
            "capture_type": "reasoning",  # default; positions >= prompt_end auto-relabel "generation"
        },
    )
    # Re-build target_positions for the response from the records returned
    target_positions: dict = {}
    for w in request.target_words:
        target_positions[w] = [r.target_token_position for r in records if r.target_word == w]

    # 12. Knowledge probe (optional)
    knowledge_capture_id = None
    if request.knowledge_probe and request.target_words:
        try:
            kp_enc = tokenizer.apply_chat_template(
                [{"role": "user", "content": request.knowledge_probe}],
                tokenize=True, add_generation_prompt=True,
                return_tensors="pt", return_dict=True,
            )
            kp_token_ids = kp_enc["input_ids"][0].tolist()
            kp_records, _ = service.capture_step(
                session_id, kp_token_ids, [request.target_words[0]],
                metadata={
                    "turn_id": turn_id,
                    "scenario_id": scenario_id,
                    "input_text": request.knowledge_probe,
                    "capture_type": "knowledge_query",
                },
            )
            if kp_records:
                knowledge_capture_id = kp_records[0].probe_id
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
