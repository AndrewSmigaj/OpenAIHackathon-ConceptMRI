#!/usr/bin/env python3
"""
Investigate the exact data flow through GptOssMLP to identify precise capture points.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils.quantization_config import Mxfp4Config


def investigate_moe_flow():
    """Investigate the flow through MoE layers to understand capture points."""
    print("=== MoE Flow Investigation ===\n")
    
    model_id = "openai/gpt-oss-20b"
    
    # Load model
    quantization_config = Mxfp4Config()
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        max_memory={0: "14GB", "cpu": "16GB"},
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Get a single layer to examine
    layer_0 = model.model.layers[0]
    mlp = layer_0.mlp
    router = mlp.router
    experts = mlp.experts
    
    print("=== MoE Components ===")
    print(f"MLP type: {type(mlp).__name__}")
    print(f"Router type: {type(router).__name__}")
    print(f"Experts type: {type(experts).__name__}")
    print(f"Router weight shape: {router.weight.shape}")  # [32, 2880]
    print(f"Router num_experts: {router.num_experts}")
    print(f"Router top_k: {router.top_k}")
    
    # Test with a simple input
    test_input = "The concept of"
    inputs = tokenizer(test_input, return_tensors="pt")
    
    # Move to same device as model
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    print(f"\n=== Input Analysis ===")
    print(f"Input text: '{test_input}'")
    print(f"Input tokens: {inputs['input_ids'][0].tolist()}")
    print(f"Input shape: {inputs['input_ids'].shape}")
    
    # Hook setup to trace data flow
    captured_data = {}
    
    def capture_router_output(module, input, output):
        """Capture router output (routing decisions)."""
        # Router output should be routing weights and selected experts
        captured_data['router_input'] = input[0].clone()
        captured_data['router_output'] = output
        print(f"Router input shape: {input[0].shape}")
        print(f"Router output type: {type(output)}")
        if hasattr(output, 'shape'):
            print(f"Router output shape: {output.shape}")
        elif isinstance(output, tuple):
            print(f"Router output tuple lengths: {[x.shape if hasattr(x, 'shape') else type(x) for x in output]}")
    
    def capture_experts_output(module, input, output):
        """Capture experts output (after expert computation)."""
        captured_data['experts_input'] = input[0].clone() if len(input) > 0 else None
        captured_data['experts_output'] = output
        print(f"Experts input: {type(input)} len={len(input)}")
        if len(input) > 0:
            print(f"Experts input[0] shape: {input[0].shape}")
        print(f"Experts output shape: {output.shape}")
    
    def capture_mlp_output(module, input, output):
        """Capture final MLP output (collective result)."""
        captured_data['mlp_input'] = input[0].clone()
        captured_data['mlp_output'] = output.clone()
        print(f"MLP input shape: {input[0].shape}")
        print(f"MLP output shape: {output.shape}")
    
    # Register hooks
    router_hook = router.register_forward_hook(capture_router_output)
    experts_hook = experts.register_forward_hook(capture_experts_output)
    mlp_hook = mlp.register_forward_hook(capture_mlp_output)
    
    try:
        # Run a forward pass through the first layer only
        with torch.no_grad():
            # Get embeddings
            embeddings = model.model.embed_tokens(inputs['input_ids'])
            
            # Apply input layer norm
            hidden_states = layer_0.input_layernorm(embeddings)
            
            # Apply attention
            attn_output = layer_0.self_attn(hidden_states)[0]
            
            # Add residual
            hidden_states = hidden_states + attn_output
            
            # Apply post-attention layer norm
            residual = hidden_states
            hidden_states = layer_0.post_attention_layernorm(hidden_states)
            
            print(f"\n=== Forward Pass Tracing ===")
            print(f"Pre-MLP hidden states shape: {hidden_states.shape}")
            
            # Apply MLP (this will trigger our hooks)
            mlp_output = mlp(hidden_states)
            
            print(f"Post-MLP output shape: {mlp_output.shape}")
            
    finally:
        # Clean up hooks
        router_hook.remove()
        experts_hook.remove()
        mlp_hook.remove()
    
    print(f"\n=== Captured Data Analysis ===")
    for key, value in captured_data.items():
        if hasattr(value, 'shape'):
            print(f"{key}: shape {value.shape}")
        elif isinstance(value, tuple):
            print(f"{key}: tuple with {len(value)} elements")
            for i, elem in enumerate(value):
                if hasattr(elem, 'shape'):
                    print(f"  [{i}]: shape {elem.shape}")
                else:
                    print(f"  [{i}]: {type(elem)}")
        else:
            print(f"{key}: {type(value)}")
    
    print(f"\n=== Capture Point Conclusions ===")
    print("1. ROUTING CAPTURE: model.layers.{i}.mlp.router")
    print("   - Hook forward pass to get routing weights and top-K expert selection")
    print("   - Output contains routing decisions for K=4 experts")
    
    print("2. EXPERT INTERNAL ACTIVATIONS: model.layers.{i}.mlp.experts")  
    print("   - Individual expert FF intermediate states")
    print("   - Need to hook specific experts or expert container")
    
    print("3. EXPERT OUTPUT STATES: model.layers.{i}.mlp")
    print("   - Hook the MLP forward pass output")
    print("   - This gives collective result after expert combination and weighting")
    print("   - This is the 'expert output state' for clustering analysis")


if __name__ == "__main__":
    investigate_moe_flow()