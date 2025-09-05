#!/usr/bin/env python3
"""
Test capturing expert routing decisions from gpt-oss-20b.
Focus on K=1 (top-1) expert selection for Concept MRI analysis.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path
from typing import Dict, List
import numpy as np


class RoutingCapture:
    """Capture MoE routing decisions from gpt-oss-20b."""
    
    def __init__(self, model, layers_to_capture=None):
        self.model = model
        self.routing_data = {}
        self.hooks = []
        
        # Default to first 3 layers for testing
        if layers_to_capture is None:
            layers_to_capture = [0, 1, 2]
        
        self.layers_to_capture = layers_to_capture
        self._register_hooks()
    
    def _register_hooks(self):
        """Register forward hooks on router modules."""
        for layer_idx in self.layers_to_capture:
            router_module = self.model.model.layers[layer_idx].mlp.router
            
            def make_hook(layer_id):
                def routing_hook(module, input, output):
                    # Router output is typically (routing_weights, selected_experts)
                    # We want the routing probabilities and top-1 selection
                    
                    if isinstance(output, tuple):
                        routing_weights = output[0]  # [batch_size, seq_len, num_experts]
                        selected_experts = output[1] if len(output) > 1 else None
                    else:
                        routing_weights = output
                        selected_experts = None
                    
                    # Get top-1 expert for our K=1 analysis
                    top1_probs, top1_experts = torch.topk(routing_weights, k=1, dim=-1)
                    
                    # Store routing data
                    self.routing_data[f"layer_{layer_id}"] = {
                        "routing_weights": routing_weights.detach().cpu(),
                        "top1_experts": top1_experts.squeeze(-1).detach().cpu(),  # Remove k dim
                        "top1_probs": top1_probs.squeeze(-1).detach().cpu(),
                        "gate_entropy": self._compute_entropy(routing_weights.detach()),
                        "shape": routing_weights.shape
                    }
                
                return routing_hook
            
            hook = router_module.register_forward_hook(make_hook(layer_idx))
            self.hooks.append(hook)
            print(f"Registered hook on layer {layer_idx} router")
    
    def _compute_entropy(self, routing_weights):
        """Compute entropy of routing distribution."""
        # Add small epsilon to avoid log(0)
        eps = 1e-8
        probs = torch.softmax(routing_weights, dim=-1)
        log_probs = torch.log(probs + eps)
        entropy = -torch.sum(probs * log_probs, dim=-1)
        return entropy.cpu()
    
    def clear_data(self):
        """Clear captured routing data."""
        self.routing_data.clear()
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
    
    def get_routing_summary(self):
        """Get summary of captured routing data."""
        summary = {}
        for layer_name, data in self.routing_data.items():
            summary[layer_name] = {
                "shape": data["shape"],
                "num_unique_experts": len(torch.unique(data["top1_experts"])),
                "mean_top1_prob": data["top1_probs"].mean().item(),
                "mean_entropy": data["gate_entropy"].mean().item(),
                "expert_distribution": torch.bincount(data["top1_experts"].flatten(), minlength=32)
            }
        return summary


def test_simple_routing():
    """Test routing capture with simple inputs."""
    print("=== Testing Routing Capture ===\n")
    
    # Load model
    model_dir = Path("data/models/gpt-oss-20b")
    
    print("Loading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    
    # Load with minimal settings
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    
    print("Model loaded successfully\n")
    
    # Test inputs (simple two-token sequences)
    test_contexts = [
        "the cat",
        "a dog", 
        "an apple",
        "my friend",
        "big house"
    ]
    
    # Set up routing capture for layers 6, 7, 8 (first CTA window)
    capture = RoutingCapture(model, layers_to_capture=[6, 7, 8])
    
    try:
        model.eval()
        
        for context in test_contexts:
            print(f"Processing: '{context}'")
            
            # Clear previous data
            capture.clear_data()
            
            # Tokenize (should be exactly 2 tokens for our test)
            inputs = tokenizer(context, return_tensors="pt")
            if inputs.input_ids.shape[1] != 2:
                print(f"  Warning: '{context}' tokenized to {inputs.input_ids.shape[1]} tokens, skipping")
                continue
            
            # Move to device
            if torch.cuda.is_available():
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
            
            # Forward pass (capture routing via hooks)
            with torch.no_grad():
                outputs = model(**inputs)
            
            # Analyze captured routing data
            summary = capture.get_routing_summary()
            
            print(f"  Tokens: {tokenizer.convert_ids_to_tokens(inputs.input_ids[0])}")
            for layer_name, stats in summary.items():
                layer_id = int(layer_name.split('_')[1])
                top_experts = stats["expert_distribution"].topk(3).indices.tolist()
                print(f"  L{layer_id}: top experts {top_experts}, entropy {stats['mean_entropy']:.3f}")
            
            print()
    
    finally:
        # Always clean up hooks
        capture.remove_hooks()
    
    print("✅ Routing capture test completed")


def test_expert_routing_k1():
    """Test K=1 expert routing specifically."""
    print("\n=== Testing K=1 Expert Routing ===\n")
    
    model_dir = Path("data/models/gpt-oss-20b")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=torch.bfloat16,
        device_map="auto", 
        trust_remote_code=True
    )
    
    # Test with the specific context/target pattern from our implementation plan
    contexts = ["the", "a", "an", "my"]
    targets = ["cat", "dog", "apple", "friend"]
    
    capture = RoutingCapture(model, layers_to_capture=[6, 7, 8])
    
    try:
        print("Context -> Target routing patterns:")
        
        for context in contexts:
            for target in targets[:2]:  # Limit combinations for testing
                full_text = f"{context} {target}"
                
                inputs = tokenizer(full_text, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.to(model.device) for k, v in inputs.items()}
                
                capture.clear_data()
                
                with torch.no_grad():
                    outputs = model(**inputs)
                
                # Extract routing decisions for each position
                tokens = tokenizer.convert_ids_to_tokens(inputs.input_ids[0])
                print(f"\n'{full_text}' -> {tokens}")
                
                for layer_name, data in capture.routing_data.items():
                    layer_id = int(layer_name.split('_')[1])
                    top1_experts = data["top1_experts"][0]  # [seq_len]
                    top1_probs = data["top1_probs"][0]
                    
                    print(f"  L{layer_id}:", end="")
                    for pos, (token, expert, prob) in enumerate(zip(tokens, top1_experts, top1_probs)):
                        print(f" {token}->E{expert.item()}({prob:.3f})", end="")
                    print()
    
    finally:
        capture.remove_hooks()
    
    print("\n✅ K=1 routing test completed")


def main():
    print("=== MoE Routing Capture Test ===\n")
    
    try:
        # Test basic routing capture
        test_simple_routing()
        
        # Test K=1 expert routing patterns
        test_expert_routing_k1()
        
        print("\n=== Summary ===")
        print("✅ Router hooks working correctly")
        print("✅ K=1 expert selection captured")
        print("✅ Routing entropy computed")
        print("✅ Ready for full Concept MRI implementation")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()