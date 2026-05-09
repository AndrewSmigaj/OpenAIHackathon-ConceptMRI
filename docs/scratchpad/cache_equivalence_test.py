#!/usr/bin/env python3
"""Empirically verify cache-on (HarmonyKVChain) and cache-off (cumulative
apply_chat_template) produce identical residuals at the target word position
across all 24 layers, beyond the 128-token sliding window boundary."""

import sys
sys.path.insert(0, 'backend/src')

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from services.probes.harmony_kv_chain import HarmonyKVChain


MODEL_PATH = 'data/models/gpt-oss-20b'
DEVICE = 'cuda'

# Sentences chosen to push past the 128-token sliding window
SENTENCES = [
    "The hotel lobby displayed a floor-to-ceiling tank stocked with graceful moon jellyfish.",
    "She poured the dechlorinated water slowly into the freshly cycled tank.",
    "The hobbyist tested the ammonia levels in the tank every morning before leaving for work.",
    "In the dimly lit basement aquarium the new tank glowed with soft blue light.",
    "The aquarium curator transferred the rare seahorses to the temperature-controlled tank.",
    "Visitors crowded around the largest tank at the public aquarium opening.",
    "The commander ordered the tank to advance across the muddy terrain toward the enemy position.",
    "Veterans recalled how the tank's treads chewed through the frozen mud of the eastern front.",
]
TARGET = "tank"


def main():
    print("Loading model...")
    tok = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH, dtype=torch.float16, device_map="auto", trust_remote_code=True,
    )
    model.eval()
    print(f"Model loaded. Layers={model.config.num_hidden_layers}, sliding_window={model.config.sliding_window}")

    chain = HarmonyKVChain(tok)

    # === Cache-on path: HarmonyKVChain, past_kv chained ===
    cache_on_residuals = []   # one entry per step: dict[layer] -> residual at last token
    past_kv = None
    for i, sentence in enumerate(SENTENCES):
        if i == 0:
            token_ids = chain.first_step_tokens(sentence)
        else:
            token_ids = chain.next_step_tokens(sentence)

        ids = torch.tensor([token_ids], device=DEVICE)
        with torch.no_grad():
            out = model(ids, past_key_values=past_kv, use_cache=True, output_hidden_states=True)
        past_kv = out.past_key_values
        # hidden_states: tuple of (n_layers + 1) tensors, shape [1, seq, hidden]
        # Find target word position in this step's NEW tokens
        target_ids_with_space = tok.encode(' ' + TARGET, add_special_tokens=False)
        target_id = target_ids_with_space[0] if target_ids_with_space else None
        target_id_no_space = tok.encode(TARGET, add_special_tokens=False)
        target_id_alt = target_id_no_space[0] if target_id_no_space else None

        # Find last occurrence in token_ids
        target_pos = None
        for p, t in enumerate(token_ids):
            if t == target_id or t == target_id_alt:
                target_pos = p
        if target_pos is None:
            print(f"  [WARN] step {i}: target not found in step's tokens — skipping")
            cache_on_residuals.append(None)
            continue

        # Capture all layer residuals at target position (use hidden_states[1:] to skip embedding)
        step_residuals = {}
        for L, h in enumerate(out.hidden_states):
            step_residuals[L] = h[0, target_pos, :].cpu().float().numpy()
        cache_on_residuals.append(step_residuals)
        print(f"  cache-on step {i}: {len(token_ids)} new tokens, target at pos {target_pos}")

    # === Cache-off path: full cumulative tokenization each step, no cache ===
    cache_off_residuals = []
    cumulative = ""
    for i, sentence in enumerate(SENTENCES):
        cumulative = (cumulative + " " + sentence) if cumulative else sentence
        # Tokenize full prompt WITHOUT suffix (matching cache-on path)
        full_with_suffix = chain.first_step_tokens(cumulative)  # uses our suffix-stripping logic; gives prompt + cumulative content
        # Wait — first_step_tokens strips the suffix. So full_with_suffix is actually prompt + cumulative (no suffix).
        # That's what we want for cache-off comparison too (matching cache-on's seen tokens).
        token_ids = full_with_suffix

        # Find last occurrence of target
        target_ids_with_space = tok.encode(' ' + TARGET, add_special_tokens=False)
        target_id = target_ids_with_space[0] if target_ids_with_space else None
        target_id_no_space = tok.encode(TARGET, add_special_tokens=False)
        target_id_alt = target_id_no_space[0] if target_id_no_space else None
        target_pos = None
        for p, t in enumerate(token_ids):
            if t == target_id or t == target_id_alt:
                target_pos = p
        if target_pos is None:
            print(f"  [WARN] cache-off step {i}: target not found — skipping")
            cache_off_residuals.append(None)
            continue

        ids = torch.tensor([token_ids], device=DEVICE)
        with torch.no_grad():
            out = model(ids, use_cache=False, output_hidden_states=True)

        step_residuals = {}
        for L, h in enumerate(out.hidden_states):
            step_residuals[L] = h[0, target_pos, :].cpu().float().numpy()
        cache_off_residuals.append(step_residuals)
        print(f"  cache-off step {i}: {len(token_ids)} total tokens, target at pos {target_pos}")

    # === Compare ===
    import numpy as np

    print("\n=== Step-by-step cosine similarity at target word ===")
    print(f"{'step':<6}{'tokens':<8}", end="")
    for L in [0, 6, 12, 18, 23]:
        print(f"L{L:<6}", end="")
    print()

    all_diffs = []
    for i, (on_r, off_r) in enumerate(zip(cache_on_residuals, cache_off_residuals)):
        if on_r is None or off_r is None:
            print(f"step {i}: skipped")
            continue
        cosines = {}
        max_abs_diffs = {}
        for L in on_r:
            a, b = on_r[L], off_r[L]
            cos = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
            cosines[L] = cos
            max_abs_diffs[L] = np.abs(a - b).max()
        cum_tokens = sum(len(chain.first_step_tokens(SENTENCES[0])) if k == 0 else len(chain.next_step_tokens(SENTENCES[k])) for k in range(i+1))
        print(f"{i:<6}{cum_tokens:<8}", end="")
        for L in [0, 6, 12, 18, 23]:
            print(f"{cosines.get(L, 0):.4f} ", end="")
        print(f"  max|Δ| L23={max_abs_diffs.get(23, 0):.4f}")
        all_diffs.append((i, cosines, max_abs_diffs))

    # Overall summary
    print("\n=== Verdict ===")
    if not all_diffs:
        print("No comparable steps.")
        return
    min_cos_overall = min(min(c.values()) for _, c, _ in all_diffs)
    max_diff_overall = max(max(d.values()) for _, _, d in all_diffs)
    print(f"min cosine across all (step, layer): {min_cos_overall:.6f}")
    print(f"max abs-diff across all (step, layer): {max_diff_overall:.6f}")
    if min_cos_overall > 0.999:
        print("EQUIVALENT (cosine > 0.999 everywhere)")
    elif min_cos_overall > 0.99:
        print("VERY SIMILAR (cosine > 0.99) — fp16 noise OK")
    else:
        print("DIVERGE — investigation needed")


if __name__ == "__main__":
    main()
