"""
Hybrid semantic tagging using rule-based keywords + sentence-transformers embeddings
"""
import numpy as np
from sentence_transformers import SentenceTransformer, util
from typing import Dict, List, Tuple


# Define ontology with expanding context
ONTOLOGY = {
    "research_domains": {
        "machine_learning": [
            "machine learning", "deep learning", "neural network", "artificial intelligence",
            "ai", "nlp", "natural language", "computer vision", "nlp tasks"
        ],
        "public_health": [
            "health", "disease", "clinical", "epidemiology", "biomedical", "medicine",
            "patient", "cancer", "healthcare", "public health", "preventive medicine"
        ],
        "education": [
            "education", "learning outcomes", "curriculum", "student", "teacher", "school",
            "pedagogy", "educational research", "STEM education"
        ],
        "environment": [
            "environment", "climate", "sustainability", "ecology", "carbon", "renewable",
            "biodiversity", "environmental science", "conservation", "ecological"
        ],
        "cybersecurity": [
            "cybersecurity", "security", "privacy", "encryption", "network security",
            "vulnerability", "cyber threat", "data protection"
        ],
        "social_science": [
            "social", "behavior", "psychology", "community", "equity", "diversity",
            "inclusion", "social systems", "human behavior"
        ],
        "engineering": [
            "engineering", "robotics", "manufacturing", "materials", "mechanical",
            "electrical", "civil engineering", "systems engineering"
        ],
        "data_science": [
            "data science", "big data", "analytics", "visualization", "database",
            "statistics", "data mining", "statistical analysis"
        ],
    },
    "methods": {
        "experimental": [
            "experiment", "randomized", "controlled trial", "lab study", "empirical",
            "experimental design", "hypothesis testing"
        ],
        "computational": [
            "computational", "simulation", "modeling", "algorithm", "software",
            "high-performance computing", "computational methods"
        ],
        "survey_qualitative": [
            "survey", "interview", "qualitative", "ethnograph", "case study",
            "focus group", "qualitative research", "phenomenological"
        ],
        "mixed_methods": [
            "mixed method", "quantitative and qualitative", "multi-method",
            "triangulation"
        ],
    },
    "populations": {
        "youth": [
            "youth", "children", "adolescent", "K-12", "undergraduate", "student",
            "young people", "teenagers", "school-age"
        ],
        "underserved": [
            "underserved", "underrepresented", "low-income", "minority", "rural",
            "disadvantaged", "marginalized", "vulnerable populations"
        ],
        "veterans": [
            "veteran", "military", "armed forces", "service member", "defense"
        ],
        "elderly": [
            "elderly", "aging", "older adult", "senior", "geriatric", "age-related"
        ],
        "general_public": [
            "public", "community", "citizen", "population", "general population"
        ],
    },
    "sponsor_themes": {
        "workforce_development": [
            "workforce", "job training", "career", "employment", "skill development",
            "professional development", "labor market"
        ],
        "innovation": [
            "innovation", "entrepreneurship", "startup", "commercialization",
            "technology transfer", "innovation ecosystem"
        ],
        "basic_research": [
            "basic research", "fundamental", "discovery", "exploratory",
            "fundamental science"
        ],
        "applied_research": [
            "applied research", "translational", "implementation", "deployment",
            "real-world application"
        ],
        "infrastructure": [
            "infrastructure", "facility", "equipment", "instrumentation",
            "research infrastructure"
        ],
    }
}


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
        print(f"[Tagger] Loading sentence-transformers model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.rule_weight = rule_weight
        self.embedding_weight = 1 - rule_weight
        
        # Pre-compute embeddings for all ontology terms
        self._compute_ontology_embeddings()
    
    def _compute_ontology_embeddings(self):
        """Pre-compute embeddings for all ontology keywords"""
        print("[Tagger] Pre-computing ontology embeddings...")
        
        self.category_embeddings = {}  # {category: {label: embedding}}
        
        for category, labels in ONTOLOGY.items():
            self.category_embeddings[category] = {}
            
            for label, keywords in labels.items():
                # Use the label (category name) as the representative embedding
                embedding = self.model.encode(label, convert_to_tensor=True)
                self.category_embeddings[category][label] = embedding
        
        print(f"[Tagger] Pre-computed embeddings for {sum(len(labels) for labels in self.category_embeddings.values())} ontology terms")
    
    def apply_tags(self, text: str, threshold_rule: float = 0.5, 
                   threshold_embedding: float = 0.5) -> Dict[str, List[str]]:
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
            
            for label, keywords in labels.items():
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


# Keep backward compatibility with old apply_tags function
def apply_tags(text: str) -> Dict[str, List[str]]:
    """Legacy rule-based tagging for backward compatibility"""
    text_lower = text.lower()
    tags = {}
    for category, labels in ONTOLOGY.items():
        matched = []
        for label, keywords in labels.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(label)
        tags[category] = matched
    return tags


def get_hybrid_tagger() -> HybridSemanticTagger:
    """Factory function to get a hybrid tagger instance"""
    return HybridSemanticTagger()
