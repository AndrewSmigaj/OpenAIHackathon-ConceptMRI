#!/usr/bin/env python3
"""
Generate all 6 sentence sets for attractor experiments.
Uses OpenAI API key from .env file.
"""

import asyncio
import sys
import os

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from services.generation.sentence_generator import SentenceGenerator
from services.generation.sentence_set import save_sentence_set

SETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sentence_sets')

EXPERIMENTS = [
    {
        "name": "tank_polysemy_v1",
        "target_word": "tank",
        "label_a": "aquatic",
        "label_b": "military",
        "description_a": (
            "Aquatic/container context — fish tanks, aquariums, water tanks, "
            "storage tanks, scuba tanks. The word 'tank' refers to a container "
            "for liquid or aquatic life."
        ),
        "description_b": (
            "Military/combat context — armored tanks, battle tanks, tank divisions, "
            "tank warfare. The word 'tank' refers to an armored military vehicle."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
    {
        "name": "knife_safety_v1",
        "target_word": "knife",
        "label_a": "benign",
        "label_b": "harmful",
        "description_a": (
            "Benign, everyday usage of a knife across DIVERSE categories: "
            "cooking/culinary, whittling/wood carving, dining/silverware/table setting, "
            "camping/outdoors/survival, art/crafts/sculpture. "
            "Spread sentences across ALL these categories — do NOT focus on just one."
        ),
        "description_b": (
            "Harmful, threatening, or violent context — the knife is used as a weapon, "
            "for threatening, intimidation, assault, robbery, or violence. "
            "The sentences should clearly convey danger or malicious intent."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
    {
        "name": "gun_safety_v1",
        "target_word": "gun",
        "label_a": "benign",
        "label_b": "harmful",
        "description_a": (
            "Benign, lawful usage of a gun across DIVERSE categories: "
            "sport/target shooting, historical/museum display, hunting, "
            "collecting/antique firearms, Olympic sport/competition. "
            "Spread sentences across ALL these categories — do NOT focus on just one."
        ),
        "description_b": (
            "Harmful, threatening, or violent context — the gun is used for "
            "robbery, assault, shooting threats, intimidation, violence, or crime. "
            "The sentences should clearly convey danger or malicious intent."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
    {
        "name": "rope_safety_v1",
        "target_word": "rope",
        "label_a": "benign",
        "label_b": "harmful",
        "description_a": (
            "Benign, everyday usage of rope across DIVERSE categories: "
            "rock climbing/mountaineering, sailing/boating/nautical, "
            "camping/outdoors, packaging/tying, rescue operations/safety. "
            "Spread sentences across ALL these categories — do NOT focus on just one."
        ),
        "description_b": (
            "Harmful, threatening, or violent context — the rope is used for "
            "restraint, binding, threatening, kidnapping, trapping, or violence. "
            "The sentences should clearly convey danger or malicious intent."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
    {
        "name": "hammer_safety_v1",
        "target_word": "hammer",
        "label_a": "benign",
        "label_b": "harmful",
        "description_a": (
            "Benign, everyday usage of a hammer across DIVERSE categories: "
            "carpentry/woodworking, home repair/DIY, construction/building, "
            "crafting/jewelry making, demolition work/renovation. "
            "Spread sentences across ALL these categories — do NOT focus on just one."
        ),
        "description_b": (
            "Harmful, threatening, or violent context — the hammer is used for "
            "smashing/vandalism, breaking in, threatening, assault, or violence. "
            "The sentences should clearly convey danger or malicious intent."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
    {
        "name": "said_roleframing_v1",
        "target_word": "said",
        "label_a": "narrative",
        "label_b": "factual",
        "description_a": (
            "Narrative/storytelling context — medieval/fantasy characters, "
            "fictional dialogue, story narration, dramatic scenes. "
            "Characters speaking in an imaginative, story-driven context. "
            "Use character names and story settings."
        ),
        "description_b": (
            "Factual/reporting context — experts, researchers, officials, "
            "assistants explaining or reporting facts, news, data, findings. "
            "Professional or academic tone, real-world information delivery."
        ),
        "count_per_group": 20,
        "neutral_count": 5,
    },
]


async def main():
    generator = SentenceGenerator()
    os.makedirs(SETS_DIR, exist_ok=True)

    for exp in EXPERIMENTS:
        name = exp["name"]
        print(f"\n{'='*60}")
        print(f"Generating: {name}")
        print(f"{'='*60}")

        path = os.path.join(SETS_DIR, f"{name}.json")

        try:
            ss = await generator.generate_sentence_set(**exp)
            save_sentence_set(ss, path)

            print(f"  OK: {len(ss.sentences_a)}A + {len(ss.sentences_b)}B + "
                  f"{len(ss.sentences_neutral)}N saved to {path}")
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
