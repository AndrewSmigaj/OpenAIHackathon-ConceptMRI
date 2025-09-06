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
        
        # Default to first window [1,2,3] but configurable via UI
        if layers_to_capture is None:
            layers_to_capture = [1, 2, 3]  # First window for MVP
        
        self.layers_to_capture = layers_to_capture
        print(f"Enhanced capture for layers: {self.layers_to_capture}")
        
    def register_hooks(self):
        """Register all hooks upfront - simple approach."""
        for layer_idx in self.layers_to_capture:
            try:
                layer = self.model.model.layers[layer_idx]
                
                # 1. Router hook (K=4 routing)
                router_hook = layer.mlp.router.register_forward_hook(
                    self._make_router_hook(layer_idx)
                )
                self.hooks.append(router_hook)
                
                # 2. MLP collective output hook  
                mlp_hook = layer.mlp.register_forward_hook(
                    self._make_activation_hook(layer_idx)
                )
                self.hooks.append(mlp_hook)
                
                # 3. All 32 expert hooks (only K=4 will fire per layer)
                for expert_id in range(32):
                    expert_hook = layer.mlp.experts[expert_id].register_forward_hook(
                        self._make_expert_internal_hook(layer_idx, expert_id)
                    )
                    self.hooks.append(expert_hook)
                
                print(f"✅ Registered {1 + 1 + 32} hooks for layer {layer_idx}")
                
            except Exception as e:
                print(f"❌ Failed to register hooks for layer {layer_idx}: {e}")
    
    def _make_router_hook(self, layer_id: int):
        """Create K=4 routing hook for a specific layer."""
        def routing_hook(module, input, output):
            try:
                # Router output is routing weights
                if isinstance(output, tuple):
                    routing_weights = output[0]  # [batch_size, seq_len, num_experts]
                else:
                    routing_weights = output
                
                # Convert to CPU for analysis
                routing_weights_cpu = routing_weights.detach().cpu()
                
                # Get K=4 expert decisions (FIXED: was K=1 in prototype)
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
                
            except Exception as e:
                print(f"❌ Router hook error (layer {layer_id}): {e}")
        
        return routing_hook
    
    def _make_activation_hook(self, layer_id: int):
        """Create activation hook for capturing collective expert output states."""
        def activation_hook(module, input, output):
            try:
                # MLP output is the collective expert output (post-routing combination)
                if isinstance(output, tuple):
                    expert_output_state = output[0]
                else:
                    expert_output_state = output
                
                # Store collective expert output for ExpertOutputState schema
                self.activation_data[f"layer_{layer_id}"] = {
                    "expert_output_state": expert_output_state.detach().cpu(),  # Full 2880D
                    "shape": expert_output_state.shape
                }
                
            except Exception as e:
                print(f"❌ Activation hook error (layer {layer_id}): {e}")
        
        return activation_hook
    
    def _make_expert_internal_hook(self, layer_id: int, expert_id: int):
        """Create hook for individual expert FF intermediate states."""
        def expert_internal_hook(module, input, output):
            try:
                # Expert FF intermediate state (before output projection)
                if isinstance(output, tuple):
                    ff_intermediate = output[0]
                else:
                    ff_intermediate = output
                
                # Store for ExpertInternalActivation schema
                key = f"layer_{layer_id}_expert_{expert_id}"
                self.expert_internal_data[key] = {
                    "layer": layer_id,
                    "expert_id": expert_id,
                    "ff_intermediate_state": ff_intermediate.detach().cpu(),
                    "shape": ff_intermediate.shape
                }
                
            except Exception as e:
                print(f"❌ Expert internal hook error (L{layer_id}E{expert_id}): {e}")
        
        return expert_internal_hook
    
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