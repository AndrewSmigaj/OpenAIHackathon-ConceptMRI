#!/usr/bin/env python3
"""
Category Axis Analyzer - Groups categories into semantic axes for proper percentage calculations.
"""

from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


class CategoryAxisAnalyzer:
    """Analyzes categories along different semantic axes."""
    
    # Define category axes based on common linguistic dimensions
    CATEGORY_AXES = {
        "grammatical": {
            "name": "Grammatical Category",
            "categories": {"nouns", "verbs", "adjectives", "adverbs", "pronouns", 
                          "prepositions", "conjunctions", "determiners", "interjections"},
            "description": "Part of speech classification"
        },
        "sentiment": {
            "name": "Sentiment",
            "categories": {"positive", "negative", "neutral"},
            "description": "Emotional valence"
        },
        "semantic_abstraction": {
            "name": "Semantic Abstraction",
            "categories": {"concrete", "abstract"},
            "description": "Level of conceptual abstraction"
        },
        "formality": {
            "name": "Formality",
            "categories": {"formal", "informal", "slang"},
            "description": "Register and formality level"
        },
        "temporal": {
            "name": "Temporal Reference",
            "categories": {"past", "present", "future"},
            "description": "Temporal orientation"
        },
        "animacy": {
            "name": "Animacy",
            "categories": {"animate", "inanimate"},
            "description": "Living vs non-living entities"
        },
        "person": {
            "name": "Person",
            "categories": {"first_person", "second_person", "third_person"},
            "description": "Grammatical person"
        },
        "number": {
            "name": "Number",
            "categories": {"singular", "plural"},
            "description": "Grammatical number"
        }
    }
    
    def __init__(self):
        """Initialize the analyzer with category-to-axis mapping."""
        self.category_to_axis = {}
        for axis_name, axis_info in self.CATEGORY_AXES.items():
            for category in axis_info["categories"]:
                self.category_to_axis[category] = axis_name
    
    def analyze_category_distribution(
        self, 
        category_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Analyze category distribution across multiple axes.
        
        Args:
            category_counts: Dictionary of category -> count
            
        Returns:
            Dictionary with axis-based analysis
        """
        # Group categories by axis
        axis_distributions = defaultdict(lambda: {"counts": {}, "total": 0})
        unrecognized_categories = {}
        
        for category, count in category_counts.items():
            if category in self.category_to_axis:
                axis_name = self.category_to_axis[category]
                axis_distributions[axis_name]["counts"][category] = count
                axis_distributions[axis_name]["total"] += count
            else:
                unrecognized_categories[category] = count
        
        # Calculate percentages within each axis
        result = {
            "axes": {},
            "unrecognized": unrecognized_categories,
            "summary": {}
        }
        
        for axis_name, distribution in axis_distributions.items():
            axis_info = self.CATEGORY_AXES[axis_name]
            total = distribution["total"]
            
            if total == 0:
                continue
                
            # Calculate percentages
            percentages = {}
            for category, count in distribution["counts"].items():
                percentages[category] = (count / total) * 100
            
            # Find dominant category in this axis
            dominant = max(distribution["counts"].items(), key=lambda x: x[1])
            
            result["axes"][axis_name] = {
                "name": axis_info["name"],
                "description": axis_info["description"],
                "categories": distribution["counts"],
                "percentages": percentages,
                "total_tokens": total,
                "dominant": {
                    "category": dominant[0],
                    "count": dominant[1],
                    "percentage": (dominant[1] / total) * 100
                }
            }
        
        # Generate summary
        result["summary"] = self._generate_summary(result["axes"])
        
        return result
    
    def _generate_summary(self, axes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a human-readable summary of the multi-axis analysis."""
        summary = {
            "active_axes": list(axes.keys()),
            "dominant_characteristics": [],
            "description": ""
        }
        
        # Collect dominant characteristics from each axis
        for axis_name, axis_data in axes.items():
            if axis_data["dominant"]["percentage"] > 60:  # Strong dominance
                summary["dominant_characteristics"].append({
                    "axis": axis_data["name"],
                    "category": axis_data["dominant"]["category"],
                    "strength": "strong",
                    "percentage": axis_data["dominant"]["percentage"]
                })
            elif axis_data["dominant"]["percentage"] > 40:  # Moderate dominance
                summary["dominant_characteristics"].append({
                    "axis": axis_data["name"],
                    "category": axis_data["dominant"]["category"],
                    "strength": "moderate",
                    "percentage": axis_data["dominant"]["percentage"]
                })
        
        # Generate description
        if not summary["dominant_characteristics"]:
            summary["description"] = "Mixed distribution across all axes"
        else:
            strong = [c for c in summary["dominant_characteristics"] if c["strength"] == "strong"]
            moderate = [c for c in summary["dominant_characteristics"] if c["strength"] == "moderate"]
            
            desc_parts = []
            if strong:
                desc_parts.append(f"Strongly {', '.join(c['category'] for c in strong)}")
            if moderate:
                desc_parts.append(f"Moderately {', '.join(c['category'] for c in moderate)}")
            
            summary["description"] = " and ".join(desc_parts)
        
        return summary
    
    def format_for_llm(self, analysis: Dict[str, Any]) -> str:
        """
        Format the multi-axis analysis for LLM consumption.
        
        Args:
            analysis: Result from analyze_category_distribution
            
        Returns:
            Formatted string for LLM context
        """
        lines = ["CATEGORY DISTRIBUTION ANALYSIS:"]
        lines.append("=" * 50)
        
        for axis_name, axis_data in analysis["axes"].items():
            lines.append(f"\n{axis_data['name']} ({axis_data['description']}):")
            
            # Sort categories by percentage
            sorted_cats = sorted(
                axis_data["percentages"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for category, percentage in sorted_cats:
                count = axis_data["categories"][category]
                lines.append(f"  - {category}: {percentage:.1f}% ({count} tokens)")
            
            lines.append(f"  Dominant: {axis_data['dominant']['category']} "
                        f"({axis_data['dominant']['percentage']:.1f}%)")
        
        if analysis["unrecognized"]:
            lines.append(f"\nUnrecognized categories: {', '.join(analysis['unrecognized'].keys())}")
        
        lines.append(f"\nSummary: {analysis['summary']['description']}")
        
        return "\n".join(lines)
    
    def compare_distributions(
        self,
        dist1: Dict[str, int],
        dist2: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Compare two category distributions across axes.
        
        Args:
            dist1: First distribution (e.g., source cluster)
            dist2: Second distribution (e.g., target cluster)
            
        Returns:
            Comparison analysis
        """
        analysis1 = self.analyze_category_distribution(dist1)
        analysis2 = self.analyze_category_distribution(dist2)
        
        comparison = {
            "shifts": {},
            "maintained": [],
            "emerged": [],
            "disappeared": []
        }
        
        # Compare each axis
        all_axes = set(analysis1["axes"].keys()) | set(analysis2["axes"].keys())
        
        for axis_name in all_axes:
            if axis_name in analysis1["axes"] and axis_name in analysis2["axes"]:
                # Both have this axis - compare dominance
                dom1 = analysis1["axes"][axis_name]["dominant"]
                dom2 = analysis2["axes"][axis_name]["dominant"]
                
                if dom1["category"] != dom2["category"]:
                    comparison["shifts"][axis_name] = {
                        "from": dom1["category"],
                        "to": dom2["category"],
                        "change": dom2["percentage"] - dom1["percentage"]
                    }
                else:
                    comparison["maintained"].append({
                        "axis": axis_name,
                        "category": dom1["category"],
                        "change": dom2["percentage"] - dom1["percentage"]
                    })
            elif axis_name in analysis1["axes"]:
                comparison["disappeared"].append(axis_name)
            else:
                comparison["emerged"].append(axis_name)
        
        return comparison