"""
Hybrid semantic tagging using rule-based keywords + sentence-transformers embeddings
"""
import numpy as np
from sentence_transformers import SentenceTransformer, util
from typing import Dict, List, Tuple

from foa_pipeline.tagging.ontology import ONTOLOGY
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)


class HybridSemanticTagger:
    """
    Hybrid tagger combining rule-based keywords and embedding similarity.
    
    Approach:
    1. Rule-based: Keyword matching (fast, explicit)
    2. Embedding-based: Sentence similarity (semantic, catches paraphrases)
    3. Hybrid score: Combine both signals
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", rule_weight: float = 0.4):
        """
        Args:
            model_name: Hugging Face sentence-transformers model
            rule_weight: Weight for rule-based matching (0-1), 
                        embedding weight = 1 - rule_weight
        """
        log.info("Loading sentence-transformers model: %s...", model_name)
        self.model = SentenceTransformer(model_name)
        self.rule_weight = rule_weight
        self.embedding_weight = 1 - rule_weight
        
        # Pre-compute embeddings for all ontology terms
        self._compute_ontology_embeddings()
    
    def _compute_ontology_embeddings(self):
        """Pre-compute embeddings for all ontology keywords"""
        log.info("Pre-computing ontology embeddings...")
        
        self.category_embeddings = {}  # {category: {label: embedding}}
        
        for category, labels in ONTOLOGY.items():
            self.category_embeddings[category] = {}
            for label, spec in labels.items():
                # Use the label (category name) as the representative embedding
                # Could also embed keywords for a more robust matching
                formatted_label = label.replace('_', ' ')
                embedding = self.model.encode(formatted_label, convert_to_tensor=True)
                self.category_embeddings[category][label] = embedding
                
        count = sum(len(labels) for labels in self.category_embeddings.values())
        log.info("Pre-computed embeddings for %d ontology terms", count)
    
    def apply_tags(self, text: str, threshold_rule: float = 0.3, 
                   threshold_embedding: float = 0.3) -> Dict[str, List[str]]:
        """
        Apply hybrid semantic tags to text.
        
        Args:
            text: FOA text (title + description + eligibility)
            threshold_rule: Confidence threshold for rule-based matching
            threshold_embedding: Cosine similarity threshold for embedding matching
            
        Returns:
            {category: [matched_labels]}
        """
        text_lower = text.lower()
        text_embedding = self.model.encode(text, convert_to_tensor=True)
        
        tags = {}
        
        for category, labels in ONTOLOGY.items():
            matched = []
            
            for label, spec in labels.items():
                keywords = spec.get("keywords", [])
                
                # 1. Rule-based: keyword matching
                rule_score = self._rule_based_match(text_lower, keywords)
                
                # 2. Embedding-based: semantic similarity
                embedding_score = self._embedding_based_match(
                    text_embedding,
                    self.category_embeddings[category][label]
                )
                
                # 3. Hybrid score
                hybrid_score = (
                    self.rule_weight * rule_score +
                    self.embedding_weight * float(embedding_score)
                )
                
                # Apply tag if either signal is strong enough
                if rule_score >= threshold_rule or embedding_score >= threshold_embedding:
                    matched.append((label, hybrid_score))
            
            # Sort by score and keep only labels
            matched.sort(key=lambda x: x[1], reverse=True)
            tags[category] = [label for label, _ in matched]
        
        return tags
    
    @staticmethod
    def _rule_based_match(text_lower: str, keywords: List[str]) -> float:
        """
        Rule-based keyword matching.
        Returns: confidence score 0-1 based on keyword presence
        """
        matches = sum(1 for kw in keywords if kw in text_lower)
        return min(1.0, matches / len(keywords)) if keywords else 0.0
    
    def _embedding_based_match(self, text_embedding, label_embedding) -> float:
        """
        Embedding-based semantic similarity.
        Returns: cosine similarity 0-1
        """
        similarity = util.pytorch_cos_sim(text_embedding, label_embedding)
        return float(similarity[0][0]) if similarity is not None else 0.0


def apply_tags(text: str) -> Dict[str, List[str]]:
    """Legacy rule-based tagging for backward compatibility. 
    Use tags from rule_tagger directly for dictionary FOA representation."""
    text_lower = text.lower()
    tags = {}
    for category, labels in ONTOLOGY.items():
        matched = []
        for label, spec in labels.items():
            keywords = spec.get("keywords", [])
            if any(kw in text_lower for kw in keywords):
                matched.append(label)
        tags[category] = matched
    return tags


def get_hybrid_tagger() -> HybridSemanticTagger:
    """Factory function to get a hybrid tagger instance"""
    return HybridSemanticTagger()
