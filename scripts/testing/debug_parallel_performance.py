#!/usr/bin/env python3
"""
Debug script to profile parallel PDF processing performance.

Adds detailed timing instrumentation to understand where time is spent:
- Docling initialization
- PDF conversion
- Entity extraction
- Embedding generation
- File I/O

Run with: python debug_parallel_performance.py
"""

import time
import json
import sys
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config, get_storage_paths
from utils_classify import classify_pdf


def profile_digital_pdf(pdf_path: Path, config: Dict, worker_id: int) -> Dict:
    """
    Process a single digital PDF with detailed timing instrumentation.

    Returns timing breakdown for each stage.
    """
    timings = {
        "file": pdf_path.name,
        "worker_id": worker_id,
        "start_time": datetime.now().isoformat(),
        "stages": {}
    }

    total_start = time.time()

    try:
        # Stage 1: Import Docling (may involve lazy loading)
        stage_start = time.time()
        from docling.document_converter import DocumentConverter
        timings["stages"]["import_docling"] = time.time() - stage_start

        # Stage 2: Initialize DocumentConverter
        stage_start = time.time()
        converter = DocumentConverter()
        timings["stages"]["init_converter"] = time.time() - stage_start

        # Stage 3: Convert PDF
        stage_start = time.time()
        result = converter.convert(str(pdf_path))
        markdown_content = result.document.export_to_markdown()
        timings["stages"]["docling_convert"] = time.time() - stage_start
        timings["char_count"] = len(markdown_content)

        # Stage 4: Entity extraction (if enabled)
        enable_entities = config.get("entity_extraction", {}).get("enabled", False)
        if enable_entities:
            import os
            from utils_entity_integration import add_entities_to_chunks

            # Create dummy chunks for testing
            stage_start = time.time()
            chunks = [{"text": markdown_content[:2000], "metadata": {}}]  # Simplified
            api_key = config.get("entity_extraction", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            chunks, entity_stats = add_entities_to_chunks(chunks, enable_entities=True, api_key=api_key)
            timings["stages"]["entity_extraction"] = time.time() - stage_start
            timings["entity_count"] = entity_stats.get("entities_found", 0)
        else:
            timings["stages"]["entity_extraction"] = 0
            timings["entity_count"] = 0

        # Stage 5: Embedding generation (if enabled)
        enable_embeddings = config.get("embeddings", {}).get("enabled", False)
        if enable_embeddings:
            from utils_embeddings import EmbeddingGenerator

            stage_start = time.time()
            # Check if model needs to be loaded
            import_start = time.time()
            embedding_gen = EmbeddingGenerator(
                model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
            )
            timings["stages"]["embedding_model_load"] = time.time() - import_start

            # Generate embeddings for dummy chunks
            chunks = [{"text": markdown_content[:2000]}]
            chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)
            timings["stages"]["embedding_generation"] = time.time() - stage_start
            timings["embedding_dim"] = len(chunks[0].get("embedding", []))
        else:
            timings["stages"]["embedding_model_load"] = 0
            timings["stages"]["embedding_generation"] = 0
            timings["embedding_dim"] = 0

        # Stage 6: File I/O (simulate writing)
        stage_start = time.time()
        # Simulate write (we won't actually write to avoid cluttering)
        _ = json.dumps({"content": markdown_content[:1000]})
        timings["stages"]["file_io"] = time.time() - stage_start

        timings["total_time"] = time.time() - total_start
        timings["success"] = True
        timings["end_time"] = datetime.now().isoformat()

    except Exception as e:
        timings["total_time"] = time.time() - total_start
        timings["success"] = False
        timings["error"] = str(e)
        timings["end_time"] = datetime.now().isoformat()

    return timings


def run_profiling_test(num_workers: int = 2, num_files: int = 10):
    """
    Run profiling test with specified number of workers.
    """
    print(f"\n{'='*80}")
    print(f"🔍 Profiling Parallel Performance - {num_workers} workers, {num_files} files")
    print(f"{'='*80}\n")

    # Load config
    config = load_config()
    paths = get_storage_paths(config)

    # Read from existing inventory
    print("📋 Reading inventory...")
    import csv
    inventory_path = paths["inventory_dir"] / "inventory.csv"

    if not inventory_path.exists():
        print(f"❌ Inventory not found at {inventory_path}")
        return

    digital_pdfs = []
    with inventory_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("classification_type") == "pdf_digital" and row.get("allowed") == "True":
                # Remove quotes from path if present
                pdf_path = row["file_path"].strip('"')
                digital_pdfs.append(Path(pdf_path))
                if len(digital_pdfs) >= num_files:
                    break

    if not digital_pdfs:
        print("❌ No digital PDFs found in inventory")
        return

    print(f"✅ Found {len(digital_pdfs)} digital PDFs\n")

    # Test 1: Sequential (baseline)
    print(f"\n{'='*80}")
    print("TEST 1: Sequential Processing (baseline)")
    print(f"{'='*80}\n")

    sequential_timings = []
    seq_start = time.time()

    for idx, pdf_path in enumerate(digital_pdfs[:num_files], 1):
        print(f"[{idx}/{num_files}] Processing: {pdf_path.name}")
        timing = profile_digital_pdf(pdf_path, config, worker_id=0)
        sequential_timings.append(timing)

    seq_total = time.time() - seq_start

    print(f"\n✅ Sequential Test Complete: {seq_total:.1f}s")

    # Test 2: Parallel
    print(f"\n{'='*80}")
    print(f"TEST 2: Parallel Processing ({num_workers} workers)")
    print(f"{'='*80}\n")

    parallel_timings = []
    par_start = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_pdf = {
            executor.submit(profile_digital_pdf, pdf, config, idx): (idx, pdf)
            for idx, pdf in enumerate(digital_pdfs[:num_files], 1)
        }

        for future in as_completed(future_to_pdf):
            idx, pdf_path = future_to_pdf[future]
            print(f"[{idx}/{num_files}] Completed: {pdf_path.name}")
            timing = future.result()
            parallel_timings.append(timing)

    par_total = time.time() - par_start

    print(f"\n✅ Parallel Test Complete: {par_total:.1f}s")
    print(f"   Speedup: {seq_total/par_total:.2f}x")

    # Analyze results
    print(f"\n{'='*80}")
    print("📊 TIMING ANALYSIS")
    print(f"{'='*80}\n")

    # Sequential averages
    seq_avg = {}
    for timing in sequential_timings:
        if timing.get("success"):
            for stage, duration in timing["stages"].items():
                if stage not in seq_avg:
                    seq_avg[stage] = []
                seq_avg[stage].append(duration)

    print("Sequential Average Times (per file):")
    seq_total_avg = 0
    for stage in sorted(seq_avg.keys()):
        avg_time = sum(seq_avg[stage]) / len(seq_avg[stage])
        seq_total_avg += avg_time
        print(f"  {stage:.<35} {avg_time:>8.3f}s ({avg_time/seq_total_avg*100:>5.1f}%)")
    print(f"  {'Total':.<35} {seq_total_avg:>8.3f}s")

    # Parallel averages
    par_avg = {}
    for timing in parallel_timings:
        if timing.get("success"):
            for stage, duration in timing["stages"].items():
                if stage not in par_avg:
                    par_avg[stage] = []
                par_avg[stage].append(duration)

    print(f"\nParallel Average Times (per file):")
    par_total_avg = 0
    for stage in sorted(par_avg.keys()):
        avg_time = sum(par_avg[stage]) / len(par_avg[stage])
        par_total_avg += avg_time
        speedup = (sum(seq_avg.get(stage, [0])) / len(seq_avg.get(stage, [1]))) / avg_time if avg_time > 0 else 0
        print(f"  {stage:.<35} {avg_time:>8.3f}s ({avg_time/par_total_avg*100:>5.1f}%) [speedup: {speedup:.2f}x]")
    print(f"  {'Total':.<35} {par_total_avg:>8.3f}s")

    # Identify bottleneck
    print(f"\n{'='*80}")
    print("🔍 BOTTLENECK ANALYSIS")
    print(f"{'='*80}\n")

    # Find stage with worst speedup
    worst_speedup = float('inf')
    worst_stage = None

    for stage in seq_avg.keys():
        if stage in par_avg:
            seq_time = sum(seq_avg[stage]) / len(seq_avg[stage])
            par_time = sum(par_avg[stage]) / len(par_avg[stage])
            speedup = seq_time / par_time if par_time > 0 else 0

            if speedup < worst_speedup and seq_time > 0.1:  # Ignore trivial stages
                worst_speedup = speedup
                worst_stage = stage

    print(f"Bottleneck: {worst_stage}")
    print(f"  Sequential: {sum(seq_avg[worst_stage])/len(seq_avg[worst_stage]):.3f}s")
    print(f"  Parallel: {sum(par_avg[worst_stage])/len(par_avg[worst_stage]):.3f}s")
    print(f"  Speedup: {worst_speedup:.2f}x (expected ~{num_workers:.1f}x)")

    if worst_speedup < num_workers * 0.7:
        print(f"\n⚠️  Poor speedup detected! This stage is not scaling well.")
        print(f"   Possible causes:")
        if "entity" in worst_stage.lower():
            print(f"   - OpenAI API rate limiting or serialization")
            print(f"   - Consider batching or caching entity extractions")
        elif "embedding" in worst_stage.lower():
            print(f"   - Model loading overhead (each worker loads its own copy)")
            print(f"   - Consider pre-loading model or using a model server")
        elif "docling" in worst_stage.lower() or "convert" in worst_stage.lower():
            print(f"   - Docling initialization overhead per worker")
            print(f"   - GPU contention if Docling uses GPU")
            print(f"   - Consider reusing converter instances")

    # Save detailed report
    report_path = Path("profiling_report.json")
    report = {
        "config": {
            "num_workers": num_workers,
            "num_files": num_files
        },
        "results": {
            "sequential": {
                "total_time": seq_total,
                "timings": sequential_timings
            },
            "parallel": {
                "total_time": par_total,
                "speedup": seq_total / par_total,
                "timings": parallel_timings
            }
        },
        "analysis": {
            "bottleneck_stage": worst_stage,
            "bottleneck_speedup": worst_speedup,
            "expected_speedup": num_workers
        }
    }

    with report_path.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: {report_path}")


if __name__ == "__main__":
    import sys

    num_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    num_files = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    run_profiling_test(num_workers=num_workers, num_files=num_files)
