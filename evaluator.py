"""
Evaluation framework for FOA semantic tagging
Measures precision, recall, and F1 for tag predictions
"""
import json
import csv
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import precision_score, recall_score, f1_score
import numpy as np


class TaggingEvaluator:
    """Evaluate tagging accuracy using precision/recall metrics"""
    
    def __init__(self):
        self.predictions = []  # List of (foa_id, category, predicted_tags, gold_tags)
    
    def add_prediction(self, foa_id: str, category: str, 
                      predicted_tags: List[str], gold_tags: List[str]):
        """
        Add a single prediction for evaluation.
        
        Args:
            foa_id: FOA identifier
            category: Tag category (e.g., "research_domains")
            predicted_tags: Predicted tags
            gold_tags: Ground truth tags
        """
        self.predictions.append({
            "foa_id": foa_id,
            "category": category,
            "predicted": set(predicted_tags),
            "gold": set(gold_tags),
        })
    
    def evaluate(self, category: Optional[str] = None) -> Dict:
        """
        Calculate precision, recall, F1 for all predictions or a specific category.
        
        Args:
            category: If specified, evaluate only this category
            
        Returns:
            {"precision": float, "recall": float, "f1": float, ...}
        """
        if not self.predictions:
            return {"error": "No predictions to evaluate"}
        
        # Filter by category if specified
        preds = self.predictions
        if category:
            preds = [p for p in preds if p["category"] == category]
            if not preds:
                return {"error": f"No predictions for category: {category}"}
        
        all_labels = set()
        for p in preds:
            all_labels.update(p["gold"])
            all_labels.update(p["predicted"])
        
        all_labels = sorted(list(all_labels))
        
        # Convert to binary format for sklearn
        y_true = []
        y_pred = []
        
        for p in preds:
            y_true_row = [1 if label in p["gold"] else 0 for label in all_labels]
            y_pred_row = [1 if label in p["predicted"] else 0 for label in all_labels]
            y_true.append(y_true_row)
            y_pred.append(y_pred_row)
        
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Calculate metrics
        precision = precision_score(y_true, y_pred, average="micro", zero_division=0)
        recall = recall_score(y_true, y_pred, average="micro", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="micro", zero_division=0)
        
        # Per-label metrics
        per_label = {}
        for i, label in enumerate(all_labels):
            per_label[label] = {
                "precision": precision_score(y_true[:, i], y_pred[:, i], zero_division=0),
                "recall": recall_score(y_true[:, i], y_pred[:, i], zero_division=0),
                "f1": f1_score(y_true[:, i], y_pred[:, i], zero_division=0),
            }
        
        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "num_predictions": len(preds),
            "num_labels": len(all_labels),
            "per_label_metrics": per_label,
        }
    
    def evaluate_all_categories(self) -> Dict[str, Dict]:
        """Evaluate each category separately"""
        categories = set(p["category"] for p in self.predictions)
        results = {}
        
        for cat in categories:
            results[cat] = self.evaluate(category=cat)
        
        # Overall metrics
        overall = self.evaluate()
        results["overall"] = overall
        
        return results
    
    def export_results(self, filepath: str):
        """Export evaluation results to JSON"""
        results = self.evaluate_all_categories()
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"[Eval] Results exported to: {filepath}")
    
    def print_summary(self):
        """Print evaluation summary"""
        results = self.evaluate_all_categories()
        
        print("\n" + "="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        
        overall = results.get("overall", {})
        if "error" not in overall:
            print(f"\nOverall Metrics:")
            print(f"  Precision: {overall.get('precision', 0):.3f}")
            print(f"  Recall:    {overall.get('recall', 0):.3f}")
            print(f"  F1-Score:  {overall.get('f1', 0):.3f}")
            print(f"  Samples:   {overall.get('num_predictions', 0)}")
        
        print(f"\nPer-Category Results:")
        for category in sorted(results.keys()):
            if category not in ["overall"]:
                metrics = results[category]
                if "error" not in metrics:
                    print(f"\n  {category}:")
                    print(f"    Precision: {metrics.get('precision', 0):.3f}")
                    print(f"    Recall:    {metrics.get('recall', 0):.3f}")
                    print(f"    F1-Score:  {metrics.get('f1', 0):.3f}")


def load_evaluation_dataset(filepath: str) -> List[Dict]:
    """
    Load hand-labeled evaluation dataset (JSON format).
    
    Expected format:
    [
        {
            "foa_id": "NSF-24-520",
            "title": "...",
            "description": "...",
            "gold_tags": {
                "research_domains": ["environment", "education"],
                "methods": ["experimental"],
                "populations": ["youth"],
                "sponsor_themes": ["basic_research"]
            }
        },
        ...
    ]
    """
    with open(filepath, "r") as f:
        return json.load(f)


def save_evaluation_dataset(dataset: List[Dict], filepath: str):
    """Save evaluation dataset to JSON"""
    with open(filepath, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"[Eval] Dataset saved: {filepath}")


def create_csv_template(num_samples: int = 5) -> str:
    """Create a CSV template for hand-labeling"""
    template = "foa_id,title,description,research_domains,methods,populations,sponsor_themes\n"
    
    for i in range(num_samples):
        template += f"FOA-{i+1},[title],[description],[tag1;tag2],[tag1;tag2],[tag1],[tag1;tag2]\n"
    
    return template
