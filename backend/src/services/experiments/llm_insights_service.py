#!/usr/bin/env python3
"""
LLM Insights Service - Generate AI-powered insights from expert routing patterns.
"""

from typing import List, Dict, Any, Optional
import json
import re
import logging
import math
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class LLMInsightsService:
    """Service for generating LLM-powered insights from MoE expert routing patterns."""
    
    def __init__(self, data_lake_path: str):
        self.data_lake_path = data_lake_path
    
    async def analyze_routing_patterns(
        self, 
        windows: List[Dict[str, Any]],
        user_prompt: str,
        api_key: str,
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """
        Generate LLM insights from expert routing data using user's custom prompt.
        
        Args:
            windows: List of complete RouteAnalysisResponse objects for each window
            user_prompt: User's custom analysis prompt
            api_key: OpenAI or Anthropic API key
            provider: "openai" or "anthropic"
            
        Returns:
            Dict containing narrative and basic statistics
        """
        logger.info(f"🔍 Generating LLM insights for {len(windows)} routing windows")
        
        # Pass complete window data directly to LLM
        data_summary = {
            "windows": windows,
            "total_windows": len(windows)
        }
        
        # Generate LLM analysis with user's prompt
        narrative = await self._generate_llm_analysis(data_summary, user_prompt, api_key, provider)
        
        return {
            "narrative": narrative,
            "statistics": {
                "total_windows": len(windows)
            }
        }
    
    def _calculate_entropy(self, distribution: Dict[str, int]) -> float:
        """Calculate Shannon entropy of a category distribution."""
        if not distribution:
            return 0.0
        
        total = sum(distribution.values())
        if total == 0:
            return 0.0
        
        # Calculate probabilities
        probabilities = [count / total for count in distribution.values() if count > 0]
        if not probabilities:
            return 0.0
        
        # Shannon entropy
        return -sum(p * math.log2(p) for p in probabilities)
    
    async def _generate_llm_analysis(
        self,
        data_summary: Dict[str, Any],
        user_prompt: str,
        api_key: str,
        provider: str
    ) -> str:
        """Generate analysis narrative using LLM."""
        
        # Build context with the data
        context = f"""You are analyzing expert routing patterns in a Mixture of Experts (MoE) neural network.

You have been provided with complete routing data from {data_summary['total_windows']} consecutive layer transitions (windows).

IMPORTANT - CATEGORY AXES:
Categories are organized into opposing axes. When analyzing percentages, calculate within each axis:
- Grammatical axis: nouns vs verbs (should sum to 100% within grammatical tokens)
- Sentiment axis: positive vs negative vs neutral (should sum to 100% within sentiment tokens)
- Abstraction axis: concrete vs abstract (should sum to 100% within abstraction tokens)
- Conceptual axis: temporal vs cognitive (should sum to 100% within conceptual tokens)

For example, if an expert has 60 nouns and 40 verbs, it's 60% nouns ON THE GRAMMATICAL AXIS.
If it also has 30 positive and 10 negative tokens, it's 75% positive ON THE SENTIMENT AXIS.
These are SEPARATE calculations - don't mix axes when computing percentages.

ROUTING WINDOWS DATA:
Each window contains:
- nodes: Expert nodes with their category distributions and context-target pairs
- links: Routing connections between experts with flow values and probabilities
- top_routes: Most frequent routing patterns with example tokens
- statistics: Coverage and confidence metrics

COMPLETE DATA:
{json.dumps(data_summary['windows'], indent=2)}

USER'S ANALYSIS REQUEST:
{user_prompt}

Please analyze the expert routing patterns based on the user's request. When discussing category distributions, be careful to calculate percentages within each axis separately. Focus on discovering interesting patterns in how experts specialize in different categories, how routing patterns change across layers, and any semantic or linguistic insights you can derive from the context-target pairs and category distributions."""

        try:
            if provider == "openai":
                client = AsyncOpenAI(api_key=api_key)
                response = await client.chat.completions.create(
                    model="gpt-5",
                    max_completion_tokens=16384,
                    messages=[{"role": "user", "content": context}]
                )
                return response.choices[0].message.content
            else:  # anthropic
                client = AsyncAnthropic(api_key=api_key)
                response = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=16384,
                    messages=[{"role": "user", "content": context}]
                )
                return response.content[0].text
                
        except Exception as e:
            logger.error(f"❌ LLM API error: {e}")
            return f"Error generating insights: {str(e)}"

    async def run_scaffold_step(
        self,
        prompt: str,
        data_sources: List[str],
        output_type: str,
        expert_windows: Optional[List[Dict]] = None,
        cluster_windows: Optional[List[Dict]] = None,
        previous_outputs: Optional[List[str]] = None,
        api_key: str = "",
        provider: str = "openai",
    ) -> Dict[str, Any]:
        """
        Run a single scaffold step: combine prompt + data context, call LLM,
        return either a narrative string or parsed element_labels dict.

        Raises on any error (does NOT swallow exceptions).
        """
        # --- Build data context ---
        context_parts: List[str] = []

        if "expert_routes" in data_sources and expert_windows:
            context_parts.append(
                "EXPERT ROUTING DATA:\n" + json.dumps(expert_windows, indent=2)
            )

        if "cluster_routes" in data_sources and cluster_windows:
            context_parts.append(
                "CLUSTER ROUTING DATA:\n" + json.dumps(cluster_windows, indent=2)
            )

        if previous_outputs:
            context_parts.append(
                "PREVIOUS STEP OUTPUTS:\n" + "\n---\n".join(previous_outputs)
            )

        data_context = "\n\n".join(context_parts)

        # --- Compose final prompt ---
        if output_type == "element_labels":
            label_instruction = (
                "\n\nReturn your answer as a JSON object mapping element IDs "
                "to short label strings, e.g. {\"L0E5\": \"Verb specialist\", ...}. "
                "Return ONLY the JSON object, no other text."
            )
        else:
            label_instruction = ""

        full_prompt = f"{prompt}\n\n{data_context}{label_instruction}"

        # --- Call LLM ---
        if provider == "openai":
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model="gpt-5.4",
                max_completion_tokens=16384,
                messages=[{"role": "user", "content": full_prompt}],
            )
            raw_text = response.choices[0].message.content
        else:  # anthropic
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16384,
                messages=[{"role": "user", "content": full_prompt}],
            )
            raw_text = response.content[0].text

        # --- Parse output ---
        if output_type == "element_labels":
            element_labels = self._parse_json_labels(raw_text)
            return {"element_labels": element_labels}
        else:
            return {"narrative": raw_text}

    def _parse_json_labels(self, raw: str) -> Dict[str, str]:
        """
        Parse a JSON dict from LLM output, stripping markdown code blocks
        and trying multiple keys (pattern from sentence_generator).
        """
        text = raw.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines[1:] if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {text[:300]}...")

        # If the response is already a flat dict of str->str, use it directly
        if isinstance(data, dict):
            # Check if all values are strings (flat label dict)
            if all(isinstance(v, str) for v in data.values()):
                return data
            # Otherwise look for a nested key
            for key in ["labels", "element_labels", "results", "data"]:
                if key in data and isinstance(data[key], dict):
                    return data[key]
            # Fallback: return the dict as-is, converting values to strings
            return {k: str(v) for k, v in data.items()}

        raise ValueError(f"Expected JSON object, got {type(data).__name__}")