#!/usr/bin/env python3
"""
LLM Insights Service - Generate AI-powered insights from expert routing patterns.
"""

from typing import List, Dict, Any
import json
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

Please analyze the expert routing patterns based on the user's request. Focus on discovering interesting patterns in how experts specialize in different categories, how routing patterns change across layers, and any semantic or linguistic insights you can derive from the context-target pairs and category distributions."""

        try:
            if provider == "openai":
                client = AsyncOpenAI(api_key=api_key)
                response = await client.chat.completions.create(
                    model="gpt-5",
                    messages=[{"role": "user", "content": context}]
                )
                return response.choices[0].message.content
            else:  # anthropic
                client = AsyncAnthropic(api_key=api_key)
                response = await client.messages.create(
                    model="claude-3-sonnet-20240229",
                    messages=[{"role": "user", "content": context}]
                )
                return response.content[0].text
                
        except Exception as e:
            logger.error(f"❌ LLM API error: {e}")
            return f"Error generating insights: {str(e)}"