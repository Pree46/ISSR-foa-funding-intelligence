#!/usr/bin/env python3
"""
FOA Funding Intelligence Pipeline - CLI Entry Point
Main orchestrates ingestion, tagging, export, and evaluation workflows
"""
import argparse
import sys
from foa_pipeline.ingest.router import ingest as ingest_foa
from foa_pipeline.pipeline import run_ingestion, run_evaluation
from foa_pipeline.export import export





def main():
    parser = argparse.ArgumentParser(
        description="FOA Funding Intelligence Pipeline - Multi-source tagging with semantic embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "nsf24520"  # Ingest NSF FOA by solicitation number
  python main.py --url "R01CA123456"  # Ingest NIH grant
  python main.py --eval evaluation_dataset.json  # Evaluate on test set
  python main.py --url "nsf24520" --legacy  # Use rule-based tagging only
        """
    )
    parser.add_argument("--url",       help="FOA source (NSF solicitation, Grants.gov URL, or NIH grant ID)")
    parser.add_argument("--out_dir",   default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--hybrid",    action="store_true", default=True, help="Use hybrid tagging (default)")
    parser.add_argument("--legacy",    action="store_true", help="Use rule-based tagging instead")
    parser.add_argument("--eval",      help="Evaluate on hand-labeled dataset (JSON)")
    parser.add_argument("--eval_out",  default="./eval_results.json", help="Evaluation output file")
    
    args = parser.parse_args()

    # Evaluation mode
    if args.eval:
        print(f"\n{'='*60}")
        print("  EVALUATION MODE")
        print(f"  Dataset: {args.eval}")
        print(f"{'='*60}\n")
        run_evaluation(args.eval, args.eval_out, use_hybrid=(not args.legacy))
        return

    # FOA ingestion mode
    if not args.url:
        parser.print_help()
        sys.exit(1)

    use_hybrid = not args.legacy
    tagging_mode = "Hybrid (embeddings + keywords)" if use_hybrid else "Rule-based keywords"

    print(f"\n{'='*60}")
    print("  FOA Ingestion Pipeline")
    print(f"  URL/ID: {args.url}")
    print(f"  Tagging: {tagging_mode}")
    print(f"  Output: {args.out_dir}")
    print(f"{'='*60}\n")

    # Step 1: Fetch FOA
    print("[Step 1/3] Fetching FOA data...")
    foa = ingest_foa(args.url)
    print(f"[OK] Fetched: {foa['foa_id']} ({foa['agency']})")

    # Step 2: Apply semantic tags
    print("[Step 2/3] Applying semantic tags...")
    foa = run_ingestion(foa, use_hybrid=use_hybrid)
    print("[OK] Tagged")

    # Step 3: Export results
    print("[Step 3/3] Exporting results...")
    export(foa, args.out_dir)

    print(f"\n[OK] Complete!\n")
    print("-- Extracted FOA --")
    print(f"  ID:        {foa['foa_id']}")
    print(f"  Title:     {foa['title']}")
    print(f"  Agency:    {foa['agency']}")
    print(f"  Open:      {foa.get('open_date', 'N/A')}")
    print(f"  Close:     {foa.get('close_date', 'N/A')}")
    print(f"  Award:     {foa.get('award_range', 'N/A')}")
    print(f"\n-- Applied Tags --")
    for category, tags in foa.get("tags", {}).items():
        if tags:
            print(f"  {category}: {', '.join(tags)}")





if __name__ == "__main__":
    main()
