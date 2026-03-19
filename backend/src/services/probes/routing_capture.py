#!/usr/bin/env python3
"""
Enhanced MoE routing capture with full routing weights and individual expert hooks.
Simple approach: register all hooks upfront, no complex dynamic registration.
"""

import torch
from typing import Dict, List, Optional, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from adapters.base_adapter import ModelAdapter


class EnhancedRoutingCapture:
    """
    Enhanced MoE routing capture for Concept MRI analysis.

    - Full routing weights vector capture (all experts)
    - All hooks registered upfront
    - Configurable layer windows for UI flexibility
    """
    
    def __init__(self, model, layers_to_capture: Optional[List[int]] = None,
                 adapter: Optional['ModelAdapter'] = None):
        self.model = model
        self.adapter = adapter
        self.hooks = []

        # Data storage organized for schema conversion
        self.routing_data = {}        # For RoutingRecord schema
        self.embedding_data = {}      # For EmbeddingRecord schema
        self.residual_stream_data = {} # For ResidualStreamState schema

        # Use adapter for defaults, fall back to legacy hardcoded values
        if layers_to_capture is None:
            layers_to_capture = adapter.layers_range() if adapter else list(range(24))

        self.layers_to_capture = layers_to_capture
        print(f"Enhanced capture for layers: {self.layers_to_capture}")
        
    def register_hooks(self):
        """Register all hooks upfront - simple approach."""
        for layer_idx in self.layers_to_capture:
            try:
                if self.adapter:
                    layer = self.adapter.get_layer(self.model, layer_idx)
                    moe_block = self.adapter.get_moe_block(layer)
                else:
                    layer = self.model.model.layers[layer_idx]
                    moe_block = layer.mlp

                # 1. MLP hook (captures both routing computation and output)
                mlp_hook = moe_block.register_forward_hook(
                    self._make_mlp_combined_hook(layer_idx)
                )
                self.hooks.append(mlp_hook)

                # 2. Decoder layer hook (captures full residual stream)
                residual_hook = layer.register_forward_hook(
                    self._make_residual_hook(layer_idx)
                )
                self.hooks.append(residual_hook)

                print(f"✅ Registered 2 hooks for layer {layer_idx} (MLP + residual)")

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
                
                # Compute routing weights via adapter or legacy manual path
                if self.adapter:
                    routing_weights = self.adapter.compute_routing_weights(module, hidden_states)
                else:
                    batch_size, seq_len, hidden_dim = hidden_states.shape
                    hidden_states_flat = hidden_states.reshape(-1, hidden_dim)
                    router_logits = torch.nn.functional.linear(
                        hidden_states_flat,
                        module.router.weight,
                        module.router.bias
                    )
                    router_logits = router_logits.reshape(batch_size, seq_len, -1)
                    routing_weights = torch.softmax(router_logits, dim=-1)
                
                # Convert to CPU for analysis
                routing_weights_cpu = routing_weights.detach().cpu()

                # Compute routing statistics
                gate_entropy = self._compute_entropy(routing_weights_cpu)

                # Store routing data for schema conversion
                self.routing_data[f"layer_{layer_id}"] = {
                    "routing_weights": routing_weights_cpu,      # Full [batch, seq, num_experts] weights
                    "gate_entropy": gate_entropy,              # [batch, seq]
                    "shape": routing_weights_cpu.shape,
                    "num_experts": routing_weights_cpu.shape[-1]
                }
                
                # Also store MLP output (collective expert output)
                if isinstance(output, tuple):
                    mlp_output = output[0]
                else:
                    mlp_output = output
                
                self.embedding_data[f"layer_{layer_id}"] = {
                    "embedding": mlp_output.detach().cpu(),
                    "shape": mlp_output.shape
                }
                
            except Exception as e:
                print(f"❌ MLP combined hook error (layer {layer_id}): {e}")
        
        return mlp_combined_hook
    
    
    def _make_residual_hook(self, layer_id: int):
        """Create hook for decoder layer to capture full residual stream."""
        def residual_hook(module, input, output):
            try:
                # GptOssDecoderLayer.forward() returns plain torch.Tensor
                # Handle both cases defensively
                if isinstance(output, tuple):
                    residual = output[0]
                else:
                    residual = output

                self.residual_stream_data[f"layer_{layer_id}"] = {
                    "residual_stream": residual.detach().cpu(),
                    "shape": residual.shape
                }

            except Exception as e:
                print(f"❌ Residual hook error (layer {layer_id}): {e}")

        return residual_hook

    def _compute_entropy(self, routing_weights: torch.Tensor) -> torch.Tensor:
        """Compute entropy of routing distribution. Input must be already softmaxed."""
        eps = 1e-8
        log_probs = torch.log(routing_weights + eps)
        entropy = -torch.sum(routing_weights * log_probs, dim=-1)
        return entropy
    
    def clear_data(self):
        """Clear all captured data."""
        self.routing_data.clear()
        self.embedding_data.clear()
        self.residual_stream_data.clear()
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
    
    def extract_highways(self, tokens: List[str], batch_idx: int = 0) -> List[str]:
        """Extract expert highway signatures using top-1 from full routing weights."""
        if not self.routing_data:
            return []

        highways = []
        seq_len = len(tokens)

        for pos in range(seq_len):
            highway_parts = []
            for layer in sorted(self.layers_to_capture):
                layer_key = f"layer_{layer}"
                if layer_key in self.routing_data:
                    weights = self.routing_data[layer_key]["routing_weights"]
                    top1_expert_id = weights[batch_idx, pos, :].argmax().item()
                    highway_parts.append(f"L{layer}E{top1_expert_id}")

            highway_signature = "→".join(highway_parts)
            highways.append(highway_signature)

        return highways
    
    def get_summary(self) -> Dict:
        """Get comprehensive summary of captured data."""
        summary = {
            "routing_summary": {},
            "activation_summary": {}
        }
        
        # Routing summary
        for layer_name, data in self.routing_data.items():
            # Expert usage statistics from argmax of full routing weights
            top1_experts = data["routing_weights"].argmax(dim=-1).flatten()
            expert_counts = torch.bincount(top1_experts, minlength=data["num_experts"])

            summary["routing_summary"][layer_name] = {
                "shape": data["shape"],
                "num_active_experts": len(torch.unique(top1_experts)),
                "mean_entropy": data["gate_entropy"].mean().item(),
                "expert_usage": expert_counts.tolist()
            }
        
        # Embedding summary
        for layer_name, data in self.embedding_data.items():
            summary["activation_summary"][layer_name] = {
                "shape": data["shape"],
                "activation_norm": torch.norm(data["embedding"]).item()
            }
        
        return summary