"""
Export Module — Convert FOA records to JSON and CSV
"""
import os
import json
import csv


def export(record: dict, out_dir: str):
    """Export FOA record to JSON and CSV files"""
    os.makedirs(out_dir, exist_ok=True)

    # JSON export
    json_path = os.path.join(out_dir, "foa.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"[Export] JSON saved -> {json_path}")

    # CSV export
    csv_path = os.path.join(out_dir, "foa.csv")
    flat = {k: v for k, v in record.items() if k != "tags"}
    for category, values in record.get("tags", {}).items():
        flat[f"tag_{category}"] = "; ".join(values)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        writer.writeheader()
        writer.writerow(flat)
    print(f"[Export] CSV saved -> {csv_path}")
