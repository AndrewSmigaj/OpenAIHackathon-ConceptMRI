#!/usr/bin/env python3
"""
Enhanced MoE routing capture with K=4 routing and individual expert hooks.
Simple approach: register all hooks upfront, no complex dynamic registration.
"""

import torch
from typing import Dict, List, Optional
import numpy as np


class EnhancedRoutingCapture:
    """
    Enhanced MoE routing capture for Concept MRI analysis.
    
    Simple fixes:
    - K=4 routing capture (fixed from prototype's K=1)
    - All hooks registered upfront
    - Individual expert FF intermediate state capture
    - Configurable layer windows for UI flexibility
    """
    
    def __init__(self, model, layers_to_capture: Optional[List[int]] = None):
        self.model = model
        self.hooks = []
        
        # Data storage organized for schema conversion
        self.routing_data = {}        # For RoutingRecord schema
        self.activation_data = {}     # For ExpertOutputState schema  
        self.expert_internal_data = {} # For ExpertInternalActivation schema
        
        # Default to first window [0,1,2] but configurable via UI
        if layers_to_capture is None:
            layers_to_capture = [0, 1, 2]  # First window for MVP
        
        self.layers_to_capture = layers_to_capture
        print(f"Enhanced capture for layers: {self.layers_to_capture}")
        
    def register_hooks(self):
        """Register all hooks upfront - simple approach."""
        for layer_idx in self.layers_to_capture:
            try:
                layer = self.model.model.layers[layer_idx]
                
                # 1. MLP hook (captures both routing computation and output)
                mlp_hook = layer.mlp.register_forward_hook(
                    self._make_mlp_combined_hook(layer_idx)
                )
                self.hooks.append(mlp_hook)
                
                # 3. Experts module hook (captures collective expert processing)
                # Note: Quantized model has single experts module, not individual experts
                experts_hook = layer.mlp.experts.register_forward_hook(
                    self._make_experts_collective_hook(layer_idx)
                )
                self.hooks.append(experts_hook)
                
                print(f"✅ Registered {1 + 1} hooks for layer {layer_idx} (mlp combined + experts)")
                
            except Exception as e:
                print(f"❌ Failed to register hooks for layer {layer_idx}: {e}")
    
    def _make_mlp_combined_hook(self, layer_id: int):
        """Create combined MLP hook that extracts routing and output data."""
        def mlp_combined_hook(module, input, output):
            try:
                # Extract input hidden states
                if isinstance(input, tuple):
                    hidden_states = input[0]
                else:
                    hidden_states = input
                
                # Compute routing weights manually (replicating MLP forward logic)
                batch_size, seq_len, hidden_dim = hidden_states.shape
                hidden_states_flat = hidden_states.reshape(-1, hidden_dim)
                
                # Compute router logits using router weights directly
                router_logits = torch.nn.functional.linear(
                    hidden_states_flat, 
                    module.router.weight, 
                    module.router.bias
                )
                
                # Reshape back to [batch, seq, num_experts]
                router_logits = router_logits.reshape(batch_size, seq_len, -1)
                
                # Convert to probabilities
                routing_weights = torch.softmax(router_logits, dim=-1)
                
                # Convert to CPU for analysis
                routing_weights_cpu = routing_weights.detach().cpu()
                
                # Get K=4 expert decisions
                top4_probs, top4_experts = torch.topk(routing_weights_cpu, k=4, dim=-1)
                
                # Compute routing statistics
                gate_entropy = self._compute_entropy(routing_weights_cpu)
                
                # Store routing data for schema conversion
                self.routing_data[f"layer_{layer_id}"] = {
                    "routing_weights": routing_weights_cpu,      # Full [batch, seq, 32] weights
                    "expert_top4_ids": top4_experts,           # [batch, seq, 4] 
                    "expert_top4_weights": top4_probs,         # [batch, seq, 4]
                    "gate_entropy": gate_entropy,              # [batch, seq]
                    "shape": routing_weights_cpu.shape,
                    "num_experts": routing_weights_cpu.shape[-1]
                }
                
                # Also store MLP output (collective expert output)
                if isinstance(output, tuple):
                    mlp_output = output[0]
                else:
                    mlp_output = output
                
                self.activation_data[f"layer_{layer_id}"] = {
                    "expert_output_state": mlp_output.detach().cpu(),  # Full 2880D
                    "shape": mlp_output.shape
                }
                
            except Exception as e:
                print(f"❌ MLP combined hook error (layer {layer_id}): {e}")
        
        return mlp_combined_hook
    
    
    def _make_experts_collective_hook(self, layer_id: int):
        """Create hook for collective experts module (quantized model)."""
        def experts_collective_hook(module, input, output):
            try:
                # Collective experts processing output
                if isinstance(output, tuple):
                    collective_expert_output = output[0]
                else:
                    collective_expert_output = output
                
                # Store collective expert processing data
                key = f"layer_{layer_id}_experts_collective"
                self.expert_internal_data[key] = {
                    "layer": layer_id,
                    "expert_type": "collective",  # Mark as collective rather than individual
                    "collective_output": collective_expert_output.detach().cpu(),
                    "shape": collective_expert_output.shape
                }
                
            except Exception as e:
                print(f"❌ Experts collective hook error (L{layer_id}): {e}")
        
        return experts_collective_hook
    
    def _compute_entropy(self, routing_weights: torch.Tensor) -> torch.Tensor:
        """Compute entropy of routing distribution."""
        eps = 1e-8
        probs = torch.softmax(routing_weights, dim=-1)
        log_probs = torch.log(probs + eps)
        entropy = -torch.sum(probs * log_probs, dim=-1)
        return entropy
    
    def clear_data(self):
        """Clear all captured data."""
        self.routing_data.clear()
        self.activation_data.clear()
        self.expert_internal_data.clear()
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
    
    def extract_highways(self, tokens: List[str], batch_idx: int = 0) -> List[str]:
        """Extract expert highway signatures using top-1 from K=4 data."""
        if not self.routing_data:
            return []
        
        highways = []
        seq_len = len(tokens)
        
        for pos in range(seq_len):
            highway_parts = []
            for layer in sorted(self.layers_to_capture):
                layer_key = f"layer_{layer}"
                if layer_key in self.routing_data:
                    # Get top-1 expert from K=4 data
                    top4_experts = self.routing_data[layer_key]["expert_top4_ids"]
                    top1_expert_id = top4_experts[batch_idx, pos, 0].item()  # First of top-4
                    highway_parts.append(f"L{layer}E{top1_expert_id}")
            
            highway_signature = "→".join(highway_parts)
            highways.append(highway_signature)
        
        return highways
    
    def get_summary(self) -> Dict:
        """Get comprehensive summary of captured data."""
        summary = {
            "routing_summary": {},
            "activation_summary": {},
            "expert_internal_summary": {}
        }
        
        # Routing summary
        for layer_name, data in self.routing_data.items():
            layer_id = int(layer_name.split('_')[1])
            
            # Expert usage statistics from top-4 data
            top4_experts = data["expert_top4_ids"].flatten()
            expert_counts = torch.bincount(top4_experts, minlength=data["num_experts"])
            
            summary["routing_summary"][layer_name] = {
                "shape": data["shape"],
                "num_active_experts": len(torch.unique(top4_experts)),
                "mean_entropy": data["gate_entropy"].mean().item(),
                "expert_usage": expert_counts.tolist()
            }
        
        # Activation summary  
        for layer_name, data in self.activation_data.items():
            summary["activation_summary"][layer_name] = {
                "shape": data["shape"],
                "activation_norm": torch.norm(data["expert_output_state"]).item()
            }
        
        # Expert internal summary - count captures per layer
        expert_count_by_layer = {}
        for key in self.expert_internal_data.keys():
            layer = key.split('_')[1]
            expert_count_by_layer[layer] = expert_count_by_layer.get(layer, 0) + 1
        
        summary["expert_internal_summary"] = {
            "total_expert_captures": len(self.expert_internal_data),
            "experts_per_layer": expert_count_by_layer
        }
        
        return summary