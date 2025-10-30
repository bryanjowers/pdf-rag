#!/usr/bin/env python3
"""
rebuild_inventory.py - Rebuild inventory with new classification logic

This script rebuilds the inventory using the improved PDF classifier
with image detection, which can now detect pre-OCR'd scanned PDFs.

Usage:
  python scripts/rebuild_inventory.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent / "olmocr_pipeline"))

from utils_config import load_config, get_storage_paths
from utils_inventory import build_inventory, get_inventory_stats

def main():
    print("="*70)
    print("Rebuilding Inventory with Improved Classification")
    print("="*70)
    print()

    # Load config
    config = load_config()
    paths = get_storage_paths(config)

    # Input directory
    input_dir = Path(config.get("storage", {}).get("input_bucket", "/mnt/gcs/legal-ocr-pdf-input"))

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return 1

    print(f"Input directory: {input_dir}")
    print(f"Output path: {Path(paths['gcs_mount_base']) / paths['inventory_dir'] / 'inventory.csv'}")
    print()

    # Build inventory with parallelization
    start = datetime.now()
    print(f"Started at: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    inventory_path = build_inventory(
        input_dir=input_dir,
        config=config,
        output_path=None,  # Use default
        sort_by="name",
        parallel=True  # Enable parallelization
    )

    end = datetime.now()
    elapsed = (end - start).total_seconds()

    if not inventory_path:
        print("\n❌ Failed to build inventory")
        return 1

    print(f"\nCompleted at: {end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {elapsed:.1f} seconds")
    print()

    # Load and display stats
    from utils_inventory import load_inventory
    inventory = load_inventory(inventory_path)
    stats = get_inventory_stats(inventory)

    print("="*70)
    print("Inventory Statistics")
    print("="*70)
    print(f"Total files:       {stats['total_files']}")
    print(f"Allowed:           {stats['allowed']}")
    print(f"Rejected:          {stats['rejected']}")
    print()

    print("By File Type:")
    print("-"*70)
    for file_type, count in sorted(stats['file_types'].items()):
        print(f"  {file_type:12s} {count:6d}")
    print()

    print("PDF Classification:")
    print("-"*70)
    print(f"  {'digital':15s} {stats['pdf_digital']:6d}")
    print(f"  {'scanned':15s} {stats['pdf_scanned']:6d}")
    print()

    print("="*70)
    print("✅ Inventory rebuilt successfully!")
    print("="*70)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
