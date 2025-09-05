#!/usr/bin/env python3
"""
Test MoE routing capture with the properly loaded dequantized gpt-oss-20b.
This implements the core routing capture functionality for Concept MRI.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np


class RoutingCapture:
    """Capture MoE routing decisions for Concept MRI analysis."""
    
    def __init__(self, model, layers_to_capture: Optional[List[int]] = None):
        self.model = model
        self.routing_data = {}
        self.activation_data = {}
        self.hooks = []
        
        # Default to first CTA window [6,7,8] as per implementation plan
        if layers_to_capture is None:
            layers_to_capture = [6, 7, 8]
        
        self.layers_to_capture = layers_to_capture
        print(f"Will capture routing for layers: {self.layers_to_capture}")
        
    def register_hooks(self):
        """Register forward hooks on router and MLP modules."""
        for layer_idx in self.layers_to_capture:
            try:
                # Get the layer
                layer = self.model.model.layers[layer_idx]
                router_module = layer.mlp.router
                mlp_module = layer.mlp
                
                # Hook for router (captures routing decisions)
                router_hook = router_module.register_forward_hook(
                    self._make_router_hook(layer_idx)
                )
                self.hooks.append(router_hook)
                
                # Hook for post-residual activations (for PCA features)
                activation_hook = mlp_module.register_forward_hook(
                    self._make_activation_hook(layer_idx)
                )
                self.hooks.append(activation_hook)
                
                print(f"✅ Registered hooks for layer {layer_idx}")
                
            except Exception as e:
                print(f"❌ Failed to register hooks for layer {layer_idx}: {e}")
    
    def _make_router_hook(self, layer_id: int):
        """Create routing hook for a specific layer."""
        def routing_hook(module, input, output):
            try:
                # Router output format varies, but typically:
                # output can be routing_weights or (routing_weights, selected_experts)
                if isinstance(output, tuple):
                    routing_weights = output[0]  # [batch_size, seq_len, num_experts]
                    selected_experts = output[1] if len(output) > 1 else None
                else:
                    routing_weights = output
                    selected_experts = None
                
                # Convert to CPU for analysis
                routing_weights_cpu = routing_weights.detach().cpu()
                
                # Get top-1 expert decisions (K=1 for Concept MRI)
                top1_probs, top1_experts = torch.topk(routing_weights_cpu, k=1, dim=-1)
                top1_experts = top1_experts.squeeze(-1)  # Remove k dimension [batch, seq]
                top1_probs = top1_probs.squeeze(-1)
                
                # Compute routing statistics
                gate_entropy = self._compute_entropy(routing_weights_cpu)
                margin = self._compute_margin(routing_weights_cpu)
                
                # Store routing data
                self.routing_data[f"layer_{layer_id}"] = {
                    "routing_weights": routing_weights_cpu,
                    "top1_experts": top1_experts,
                    "top1_probs": top1_probs,
                    "gate_entropy": gate_entropy,
                    "margin": margin,
                    "shape": routing_weights_cpu.shape,
                    "num_experts": routing_weights_cpu.shape[-1]
                }
                
            except Exception as e:
                print(f"❌ Router hook error (layer {layer_id}): {e}")
        
        return routing_hook
    
    def _make_activation_hook(self, layer_id: int):
        """Create activation hook for capturing post-residual features."""
        def activation_hook(module, input, output):
            try:
                # MLP output is typically the processed hidden states
                if isinstance(output, tuple):
                    hidden_states = output[0]
                else:
                    hidden_states = output
                
                # Store post-residual activations for PCA
                self.activation_data[f"layer_{layer_id}"] = {
                    "activations": hidden_states.detach().cpu(),
                    "shape": hidden_states.shape
                }
                
            except Exception as e:
                print(f"❌ Activation hook error (layer {layer_id}): {e}")
        
        return activation_hook
    
    def _compute_entropy(self, routing_weights: torch.Tensor) -> torch.Tensor:
        """Compute entropy of routing distribution."""
        eps = 1e-8
        probs = torch.softmax(routing_weights, dim=-1)
        log_probs = torch.log(probs + eps)
        entropy = -torch.sum(probs * log_probs, dim=-1)
        return entropy
    
    def _compute_margin(self, routing_weights: torch.Tensor) -> torch.Tensor:
        """Compute margin between top-1 and top-2 routing probabilities."""
        top2_probs, _ = torch.topk(routing_weights, k=2, dim=-1)
        margin = top2_probs[:, :, 0] - top2_probs[:, :, 1]  # top1 - top2
        return margin
    
    def clear_data(self):
        """Clear captured routing data."""
        self.routing_data.clear()
        self.activation_data.clear()
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
    
    def extract_highways(self, tokens: List[str]) -> List[str]:
        """Extract expert highway signatures for each token."""
        if not self.routing_data:
            return []
        
        highways = []
        seq_len = len(tokens)
        
        for pos in range(seq_len):
            highway_parts = []
            for layer in sorted(self.layers_to_capture):
                layer_key = f"layer_{layer}"
                if layer_key in self.routing_data:
                    expert_id = self.routing_data[layer_key]["top1_experts"][0, pos].item()
                    highway_parts.append(f"L{layer}E{expert_id}")
            
            highway_signature = "→".join(highway_parts)
            highways.append(highway_signature)
        
        return highways
    
    def get_summary(self) -> Dict:
        """Get summary of captured routing data."""
        summary = {}
        
        for layer_name, data in self.routing_data.items():
            layer_id = int(layer_name.split('_')[1])
            
            # Expert usage statistics
            expert_counts = torch.bincount(
                data["top1_experts"].flatten(), 
                minlength=data["num_experts"]
            )
            
            summary[layer_name] = {
                "shape": data["shape"],
                "num_unique_experts": len(torch.unique(data["top1_experts"])),
                "mean_top1_prob": data["top1_probs"].mean().item(),
                "mean_entropy": data["gate_entropy"].mean().item(),
                "mean_margin": data["margin"].mean().item(),
                "expert_usage": expert_counts.tolist()
            }
        
        return summary


def test_routing_capture():
    """Test MoE routing capture with properly loaded model."""
    print("=== MoE Routing Capture Test ===\n")
    
    # Load the dequantized model
    model_path = Path("data/models/gpt-oss-20b-dequantized")
    
    if not model_path.exists():
        print("❌ Dequantized model not found!")
        print("Run: python3 scripts/dequantize_model.py")
        return False
    
    print("Loading tokenizer and model...")
    
    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        print(f"✅ Tokenizer loaded")
        
        # Load model with conservative settings
        device_map = {
            "model.embed_tokens": 0,
            **{f"model.layers.{i}": 0 for i in range(15)},  # First 15 layers on GPU
            **{f"model.layers.{i}": "cpu" for i in range(15, 24)},  # Rest on CPU
            "model.norm": "cpu",
            "lm_head": "cpu"
        }
        
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_enable_fp32_cpu_offload=True
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            quantization_config=quantization_config,
            device_map=device_map,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        )
        
        print(f"✅ Model loaded with device mapping")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False
    
    # Set up routing capture
    capture = RoutingCapture(model, layers_to_capture=[6, 7, 8])
    capture.register_hooks()
    
    # Test contexts from implementation plan
    test_contexts = [
        "the cat",
        "a dog",
        "an apple", 
        "my friend"
    ]
    
    try:
        model.eval()
        
        print(f"\n=== Testing Routing Capture ===\n")
        
        for context in test_contexts:
            print(f"Processing: '{context}'")
            
            # Clear previous data
            capture.clear_data()
            
            # Tokenize
            inputs = tokenizer(context, return_tensors="pt")
            tokens = tokenizer.convert_ids_to_tokens(inputs.input_ids[0])
            
            # Move to device (embed_tokens device)
            inputs = {k: v.to(0) for k, v in inputs.items()}
            
            # Forward pass (capture routing via hooks)
            with torch.no_grad():
                outputs = model(**inputs)
            
            # Extract expert highways
            highways = capture.extract_highways(tokens)
            
            print(f"  Tokens: {tokens}")
            print(f"  Expert highways: {highways}")
            
            # Get routing summary
            summary = capture.get_summary()
            for layer_name, stats in summary.items():
                layer_id = int(layer_name.split('_')[1])
                print(f"  L{layer_id}: entropy={stats['mean_entropy']:.3f}, margin={stats['mean_margin']:.3f}")
            
            print()
        
        print("✅ Routing capture test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Routing capture failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        capture.remove_hooks()


def main():
    print("=== Fixed MoE Routing Capture ===\n")
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        print("❌ No GPU available")
        return
    
    # Test routing capture
    success = test_routing_capture()
    
    if success:
        print("\n" + "="*50)
        print("SUCCESS: MoE routing capture is working!")
        print("="*50)
        print("\nReady for:")
        print("1. Full probe capture service implementation")
        print("2. Expert highway analysis")
        print("3. Concept MRI pipeline")
    else:
        print("\n" + "="*50)
        print("FAILED: Routing capture needs debugging")
        print("="*50)


if __name__ == "__main__":
    main()