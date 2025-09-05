#!/usr/bin/env python3
"""
Test simulation of actual MoE capture workflow over layers 1-3.
Simulates what really happens: one context-target pair → multiple linked records.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'backend' / 'src'))

import numpy as np
from datetime import datetime
from typing import List, Dict
import uuid

from core.parquet_writer import BatchWriter
from core.parquet_reader import read_records
from core.data_lake import get_schema_path

from schemas.tokens import TokenRecord
from schemas.routing import create_routing_record, RoutingRecord
from schemas.expert_output_states import create_expert_output_state, ExpertOutputState
from schemas.expert_internal_activations import create_expert_internal_activation, ExpertInternalActivation
from schemas.features_pca128 import create_pca_features, PCAFeatures


def simulate_moe_forward_pass(context_text: str, target_text: str, context_token_id: int, target_token_id: int) -> Dict:
    """
    Simulate a forward pass through MoE layers 1-3 for one context-target pair.
    
    Returns all the data that would be captured from the real model.
    """
    probe_id = f"probe_{uuid.uuid4().hex[:8]}"
    layers = [1, 2, 3]  # MVP window
    captured_at = datetime.now().isoformat()
    
    print(f"Simulating forward pass: '{context_text} {target_text}' → {probe_id}")
    
    captured_data = {
        "probe_id": probe_id,
        "token_record": None,
        "routing_records": [],
        "expert_output_records": [],
        "expert_internal_records": [],
        "pca_features_records": []
    }
    
    # 1. Token record (index linking probe_id to context-target pair)
    captured_data["token_record"] = TokenRecord(
        probe_id=probe_id,
        context_text=context_text,
        target_text=target_text, 
        context_token_id=context_token_id,
        target_token_id=target_token_id
    )
    
    # 2. Process through each layer (1, 2, 3)
    for layer in layers:
        print(f"  Processing layer {layer}...")
        
        # Simulate routing through 32 experts (K=4 selection)
        routing_weights = np.random.dirichlet(np.ones(32)).astype(np.float32)  # Sum to 1
        routing_record = create_routing_record(
            probe_id=probe_id,
            layer=layer,
            routing_weights=routing_weights,
            routing_aux_loss=np.random.uniform(0.01, 0.1),
            captured_at=captured_at
        )
        captured_data["routing_records"].append(routing_record)
        
        # Get top-4 experts for this layer
        top4_experts = routing_record.expert_top4_ids
        print(f"    Top-4 experts: {top4_experts}")
        
        # Simulate expert internal activations (only for active experts)
        for expert_id in top4_experts:
            # Simulate expert internal FF intermediate state
            ff_intermediate = np.random.randn(2, 4096).astype(np.float32)  # [seq_len=2, ff_dim=4096]
            expert_internal_record = create_expert_internal_activation(
                probe_id=probe_id,
                layer=layer,
                expert_id=expert_id,
                ff_intermediate_state=ff_intermediate,
                captured_at=captured_at
            )
            captured_data["expert_internal_records"].append(expert_internal_record)
        
        # Simulate collective expert output state (GptOssMLP output)
        expert_output = np.random.randn(2, 2880).astype(np.float32)  # [seq_len=2, hidden_dim=2880]
        expert_output_record = create_expert_output_state(
            probe_id=probe_id,
            layer=layer,
            expert_output_state=expert_output
        )
        captured_data["expert_output_records"].append(expert_output_record)
        
        # Simulate PCA128 features (dimensionality reduction: 2880 → 128)
        pca128_features = np.random.randn(128).astype(np.float32)
        pca_record = create_pca_features(
            probe_id=probe_id,
            layer=layer,
            pca128=pca128_features
        )
        captured_data["pca_features_records"].append(pca_record)
    
    print(f"  Captured: 1 token, {len(captured_data['routing_records'])} routing, " +
          f"{len(captured_data['expert_output_records'])} expert outputs, " +
          f"{len(captured_data['expert_internal_records'])} expert internals, " +
          f"{len(captured_data['pca_features_records'])} PCA features")
    
    return captured_data


def write_captured_data_to_lake(captured_data: Dict):
    """Write all captured data to the data lake using BatchWriter."""
    print("Writing captured data to data lake...")
    
    # Write token record
    with BatchWriter(str(get_schema_path("tokens"))) as writer:
        writer.add_record(captured_data["token_record"])
    
    # Write routing records
    with BatchWriter(str(get_schema_path("routing"))) as writer:
        for record in captured_data["routing_records"]:
            writer.add_record(record)
    
    # Write expert output records
    with BatchWriter(str(get_schema_path("expert_output_states"))) as writer:
        for record in captured_data["expert_output_records"]:
            writer.add_record(record)
    
    # Write expert internal records
    with BatchWriter(str(get_schema_path("expert_internal_activations"))) as writer:
        for record in captured_data["expert_internal_records"]:
            writer.add_record(record)
    
    # Write PCA features records
    with BatchWriter(str(get_schema_path("features_pca128"))) as writer:
        for record in captured_data["pca_features_records"]:
            writer.add_record(record)
    
    print("✅ All data written to lake")


def verify_data_linkage(probe_id: str):
    """Verify that all data is properly linked by probe_id."""
    print(f"Verifying data linkage for {probe_id}...")
    
    # Read all data back
    tokens = read_records(str(get_schema_path("tokens")), TokenRecord)
    routing = read_records(str(get_schema_path("routing")), RoutingRecord) 
    expert_outputs = read_records(str(get_schema_path("expert_output_states")), ExpertOutputState)
    expert_internals = read_records(str(get_schema_path("expert_internal_activations")), ExpertInternalActivation)
    pca_features = read_records(str(get_schema_path("features_pca128")), PCAFeatures)
    
    # Filter by probe_id
    probe_tokens = [r for r in tokens if r.probe_id == probe_id]
    probe_routing = [r for r in routing if r.probe_id == probe_id]
    probe_outputs = [r for r in expert_outputs if r.probe_id == probe_id]
    probe_internals = [r for r in expert_internals if r.probe_id == probe_id]  
    probe_pca = [r for r in pca_features if r.probe_id == probe_id]
    
    print(f"Found for {probe_id}:")
    print(f"  Tokens: {len(probe_tokens)} (expected: 1)")
    print(f"  Routing: {len(probe_routing)} (expected: 3 layers)")
    print(f"  Expert outputs: {len(probe_outputs)} (expected: 3 layers)")
    print(f"  Expert internals: {len(probe_internals)} (expected: ~12, top-4 × 3 layers)")
    print(f"  PCA features: {len(probe_pca)} (expected: 3 layers)")
    
    # Verify expected counts
    assert len(probe_tokens) == 1, f"Expected 1 token record, got {len(probe_tokens)}"
    assert len(probe_routing) == 3, f"Expected 3 routing records, got {len(probe_routing)}"  
    assert len(probe_outputs) == 3, f"Expected 3 expert output records, got {len(probe_outputs)}"
    assert len(probe_internals) == 12, f"Expected 12 expert internal records, got {len(probe_internals)}"
    assert len(probe_pca) == 3, f"Expected 3 PCA records, got {len(probe_pca)}"
    
    # Verify layer coverage
    routing_layers = sorted([r.layer for r in probe_routing])
    output_layers = sorted([r.layer for r in probe_outputs])
    pca_layers = sorted([r.layer for r in probe_pca])
    
    assert routing_layers == [1, 2, 3], f"Routing layers: {routing_layers}"
    assert output_layers == [1, 2, 3], f"Output layers: {output_layers}"  
    assert pca_layers == [1, 2, 3], f"PCA layers: {pca_layers}"
    
    # Verify expert internal distribution
    internals_by_layer = {}
    for record in probe_internals:
        if record.layer not in internals_by_layer:
            internals_by_layer[record.layer] = []
        internals_by_layer[record.layer].append(record.expert_id)
    
    for layer in [1, 2, 3]:
        layer_experts = internals_by_layer[layer]
        assert len(layer_experts) == 4, f"Layer {layer} has {len(layer_experts)} experts, expected 4"
        print(f"  Layer {layer} active experts: {sorted(layer_experts)}")
    
    print("✅ Data linkage verification passed")


def simulate_experiment_query(context_list: List[str], target_list: List[str]):
    """Simulate how an experiment would query the data lake."""
    print(f"Simulating experiment query: contexts={context_list}, targets={target_list}")
    
    # Read token index
    tokens = read_records(str(get_schema_path("tokens")), TokenRecord)
    
    # Find matching probe_ids
    matching_probe_ids = []
    for token_record in tokens:
        if token_record.context_text in context_list and token_record.target_text in target_list:
            matching_probe_ids.append(token_record.probe_id)
            print(f"  Found: {token_record.context_text} {token_record.target_text} → {token_record.probe_id}")
    
    print(f"Found {len(matching_probe_ids)} matching probes")
    
    # Now an experiment could get all activation data for these probe_ids
    if matching_probe_ids:
        example_probe_id = matching_probe_ids[0]
        routing = read_records(str(get_schema_path("routing")), RoutingRecord)
        probe_routing = [r for r in routing if r.probe_id == example_probe_id]
        
        print(f"Example routing data for {example_probe_id}:")
        for r in probe_routing:
            print(f"  Layer {r.layer}: Top-1 expert {r.expert_top1_id} (weight: {r.expert_top1_weight:.3f})")
    
    return matching_probe_ids


def main():
    """Run the full capture simulation test."""
    print("=== MoE Capture Simulation Test ===\n")
    
    try:
        # Simulate multiple context-target pairs  
        test_pairs = [
            ("the", "cat", 123, 456),
            ("a", "dog", 789, 101), 
            ("the", "house", 123, 999)
        ]
        
        all_probe_ids = []
        
        # 1. Simulate capture for each pair
        for context_text, target_text, context_id, target_id in test_pairs:
            captured_data = simulate_moe_forward_pass(context_text, target_text, context_id, target_id)
            write_captured_data_to_lake(captured_data)
            all_probe_ids.append(captured_data["probe_id"])
        
        print()
        
        # 2. Verify data linkage for each probe
        for probe_id in all_probe_ids:
            verify_data_linkage(probe_id)
            print()
        
        # 3. Simulate experiment queries
        simulate_experiment_query(["the", "a"], ["cat", "dog"])
        print()
        
        print("✅ MoE capture simulation test passed!")
        print("Ready to implement real capture service with PyTorch hooks.")
        
    except Exception as e:
        print(f"\n❌ Capture simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)