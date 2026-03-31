"""
Pipeline Module — Orchestration for ingestion and evaluation workflows
"""
from foa_pipeline.tagging.hybrid import HybridSemanticTagger, apply_tags as apply_tags_legacy
from foa_pipeline.evaluator import TaggingEvaluator, load_evaluation_dataset


def run_evaluation(dataset_path: str, output_path: str, use_hybrid: bool = True):
    """
    Evaluate tagging pipeline on hand-labeled dataset.
    Computes precision, recall, F1 scores per category.
    """
    print(f"[Eval] Loading dataset: {dataset_path}")
    dataset = load_evaluation_dataset(dataset_path)
    
    evaluator = TaggingEvaluator()
    
    # Initialize tagger
    if use_hybrid:
        print("[Eval] Using hybrid semantic tagger")
        tagger = HybridSemanticTagger()
    else:
        print("[Eval] Using legacy rule-based tagger")
        tagger = None
    
    # Process each FOA
    for foa in dataset:
        foa_id = foa.get("foa_id", "UNKNOWN")
        title = foa.get("title", "")
        description = foa.get("description", "")
        gold_tags = foa.get("gold_tags", {})
        
        combined_text = f"{title} {description}"
        
        # Get predictions
        predicted_tags = tagger.apply_tags(combined_text) if use_hybrid else apply_tags_legacy(combined_text)
        
        # Evaluate each category
        for category in gold_tags.keys():
            gold = gold_tags.get(category, [])
            predicted = predicted_tags.get(category, [])
            evaluator.add_prediction(foa_id, category, predicted, gold)
    
    # Print and export results
    print("\n" + "="*60)
    evaluator.print_summary()
    evaluator.export_results(output_path)
    print("="*60 + "\n")


def run_ingestion(foa: dict, use_hybrid: bool = True) -> dict:
    """
    Apply semantic tags to an ingested FOA record.
    Returns FOA with tags field populated.
    """
    combined_text = f"{foa.get('title','')} {foa.get('description','')} {foa.get('eligibility','')}"
    
    if use_hybrid:
        tagger = HybridSemanticTagger()
        foa["tags"] = tagger.apply_tags(combined_text)
    else:
        foa["tags"] = apply_tags_legacy(combined_text)
    
    return foa
