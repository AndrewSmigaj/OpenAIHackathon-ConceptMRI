#!/usr/bin/env python3
"""
Simple WordNet mining for unambiguous semantic categories.
Provides synset-based word mining with single-sense filtering for clean demos.
"""

import nltk
from nltk.corpus import wordnet
from typing import List, Tuple, Dict


class WordNetMiner:
    """Simple WordNet mining with unambiguous word filtering."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self._ensure_wordnet_data()
    
    def _ensure_wordnet_data(self):
        """Download WordNet data if needed."""
        try:
            wordnet.synsets('test')
        except LookupError:
            print("📚 Downloading WordNet data...")
            nltk.download('wordnet')
            nltk.download('omw-1.4')  # Open Multilingual Wordnet
    
    def mine_unambiguous_words(self, synset_id: str, max_depth: int = 2) -> List[str]:
        """Mine globally unambiguous single-token words from synset hierarchy."""
        try:
            synset = wordnet.synset(synset_id)
        except Exception as e:
            raise ValueError(f"Invalid synset ID '{synset_id}': {e}")
        
        # Get hyponyms up to max_depth levels (substitution principle)
        all_hyponyms = [synset]  # Include root synset
        current_level = [synset]
        
        for depth in range(max_depth):
            next_level = []
            for current_synset in current_level:
                next_level.extend(current_synset.hyponyms())
            if not next_level:  # No more hyponyms
                break
            all_hyponyms.extend(next_level)
            current_level = next_level
        
        # Extract and filter words
        filtered_words = []
        for hyponym in all_hyponyms:
            for lemma in hyponym.lemmas():
                word = lemma.name().lower()
                
                # Skip multi-word terms
                if '_' not in word and ' ' not in word:
                    # Filter 1: Globally unambiguous (single word sense)
                    if len(wordnet.synsets(word)) == 1:
                        # Filter 2: Single token only
                        tokens = self.tokenizer.encode(word, add_special_tokens=False)
                        if len(tokens) == 1:
                            filtered_words.append(word)
        
        result = sorted(set(filtered_words))  # Remove duplicates and sort
        
        if not result:
            print(f"⚠️ Warning: No unambiguous words found for synset '{synset_id}'")
        
        return result

    def get_synset_label(self, synset_id: str) -> str:
        """Return full synset ID for transparency."""
        return synset_id
    
    def mine_pos_pure_words(self, pos: str, max_words: int = 30) -> List[str]:
        """Mine words that are ONLY this POS (noun, verb, adj, etc.)."""
        print(f"🔍 Mining words that are ONLY {pos}...")
        
        words_found = []
        checked_words = set()
        
        # Go through WordNet synsets for this POS
        for synset in list(wordnet.all_synsets(pos=pos))[:1000]:  # Limit for speed
            for lemma in synset.lemmas():
                word = lemma.name().lower()
                
                # Skip if already checked or has underscores/spaces
                if word in checked_words or '_' in word or ' ' in word:
                    continue
                
                checked_words.add(word)
                
                # Check: does this word ONLY appear as this POS?
                all_synsets = wordnet.synsets(word)
                all_pos = set(s.pos() for s in all_synsets)
                
                if len(all_pos) == 1 and pos in all_pos:  # Only this POS
                    # Check single token
                    try:
                        tokens = self.tokenizer.encode(word, add_special_tokens=False)
                        if len(tokens) == 1:
                            words_found.append(word)
                            
                            if len(words_found) >= max_words:
                                break
                    except Exception:
                        continue
            
            if len(words_found) >= max_words:
                break
        
        result = sorted(set(words_found))
        print(f"✅ Found {len(result)} pure {pos} words")
        return result
    
    def mine_pos_categories(self, pos_categories: List[str], max_words_per_pos: int = 30) -> Dict[str, List[str]]:
        """Mine POS-pure words for multiple POS categories."""
        results = {}
        
        for pos in pos_categories:
            try:
                words = self.mine_pos_pure_words(pos, max_words_per_pos)
                results[pos] = words
            except Exception as e:
                print(f"⚠️ Failed to mine POS '{pos}': {e}")
                results[pos] = []
        
        return results
    
    def mine_all_words(self, synset_id: str, max_depth: int = 2) -> List[str]:
        """Mine all single-token words from synset hierarchy, including ambiguous words."""
        try:
            synset = wordnet.synset(synset_id)
        except Exception as e:
            raise ValueError(f"Invalid synset ID '{synset_id}': {e}")
        
        # Get hyponyms up to max_depth levels
        all_hyponyms = [synset]  # Include root synset
        current_level = [synset]
        
        for depth in range(max_depth):
            next_level = []
            for current_synset in current_level:
                next_level.extend(current_synset.hyponyms())
            if not next_level:  # No more hyponyms
                break
            all_hyponyms.extend(next_level)
            current_level = next_level
        
        # Extract words (allowing ambiguous words)
        all_words = []
        for hyponym in all_hyponyms:
            for lemma in hyponym.lemmas():
                word = lemma.name().lower()
                
                # Skip multi-word terms
                if '_' not in word and ' ' not in word:
                    # Only filter for single token (allow ambiguous words)
                    try:
                        tokens = self.tokenizer.encode(word, add_special_tokens=False)
                        if len(tokens) == 1:
                            all_words.append(word)
                    except Exception:
                        continue
        
        result = sorted(set(all_words))  # Remove duplicates and sort
        
        if not result:
            print(f"⚠️ Warning: No single-token words found for synset '{synset_id}'")
        else:
            print(f"✅ Found {len(result)} words from synset '{synset_id}' (including ambiguous)")
        
        return result


# Convenience function for API usage
def mine_category_words(synset_id: str, tokenizer) -> Tuple[List[str], str]:
    """Mine unambiguous words and return with synset label."""
    miner = WordNetMiner(tokenizer)
    words = miner.mine_unambiguous_words(synset_id)
    label = miner.get_synset_label(synset_id)
    return words, label