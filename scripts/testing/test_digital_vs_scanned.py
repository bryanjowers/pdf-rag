#!/usr/bin/env python3
"""
Validation Test: Digital vs Scanned Pipeline Comparison

Purpose: Validate assumptions about processing quality by comparing:
- Digital PDF → Docling (ground truth)
- Scanned PDF → OlmOCR (current scanned pipeline)

This is a research test to understand trade-offs, NOT a pipeline change.
"""

import json
import sys
import time
import shutil
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF not installed. Install with: pip install PyMuPDF")
    sys.exit(1)


def convert_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300, max_pages: int = 10) -> List[Path]:
    """
    Convert PDF pages to high-resolution images (simulates scanning).

    Args:
        pdf_path: Input PDF file
        output_dir: Directory for output images
        dpi: Resolution (300 = typical scanner quality)
        max_pages: Maximum pages to convert

    Returns:
        List of created image paths
    """
    print(f"\n📄 Converting PDF to images (simulating scan at {dpi} DPI)...")

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    image_paths = []

    num_pages = min(len(doc), max_pages)
    print(f"   Processing {num_pages} pages...")

    for page_num in range(num_pages):
        page = doc[page_num]

        # Render at specified DPI
        zoom = dpi / 72  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Save as PNG
        image_path = output_dir / f"page_{page_num:03d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)

        print(f"      Page {page_num + 1}: {image_path.name} ({pix.width}x{pix.height}px)")

    doc.close()

    print(f"   ✅ Created {len(image_paths)} images")
    return image_paths


def process_digital_pdf(pdf_path: Path, output_base: Path) -> Dict:
    """
    Process PDF through digital pipeline (Docling).

    Returns:
        Processing results and paths
    """
    print(f"\n🔷 Processing DIGITAL PDF (Docling pipeline)...")
    print(f"   Input: {pdf_path.name}")

    from handlers.pdf_digital import process_digital_pdf as process_digital
    from utils_config import load_config

    config = load_config()

    output_dir = output_base / "digital_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    result = process_digital(
        pdf_path=pdf_path,
        output_dir=output_dir,
        config=config,
        batch_id="validation_digital"
    )

    duration = time.time() - start_time

    print(f"   ✅ Digital processing complete in {duration:.1f}s")
    print(f"      Processor: {result.get('processor')}")
    print(f"      Chunks: {result.get('chunk_count')}")
    print(f"      Characters: {result.get('char_count'):,}")
    print(f"      JSONL: {result.get('jsonl_path')}")

    return {
        "result": result,
        "duration": duration,
        "jsonl_path": result.get("jsonl_path"),
        "markdown_path": result.get("markdown_path")
    }


def process_scanned_images(image_paths: List[Path], output_base: Path) -> Dict:
    """
    Process images through scanned pipeline (OlmOCR).

    Note: Currently our pipeline expects PDFs, not individual images.
    We'll need to use OlmOCR directly or convert images to PDF first.

    Returns:
        Processing results and paths
    """
    print(f"\n🔶 Processing SCANNED IMAGES (OlmOCR pipeline)...")
    print(f"   Input: {len(image_paths)} images")

    # For this test, we'll use the image handler if available,
    # or convert images to a PDF and process as scanned

    # Option 1: Convert images to PDF first
    temp_pdf = output_base / "scanned_temp.pdf"

    print(f"   📦 Combining images into PDF...")
    doc = fitz.open()
    for img_path in image_paths:
        img_doc = fitz.open(img_path)
        pdf_bytes = img_doc.convert_to_pdf()
        img_pdf = fitz.open("pdf", pdf_bytes)
        doc.insert_pdf(img_pdf)
        img_pdf.close()
        img_doc.close()

    doc.save(str(temp_pdf))
    doc.close()
    print(f"      Created: {temp_pdf.name}")

    # Process through scanned PDF handler
    from handlers.pdf_scanned import process_scanned_pdf
    from utils_config import load_config

    config = load_config()

    output_dir = output_base / "scanned_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    result = process_scanned_pdf(
        pdf_path=temp_pdf,
        output_dir=output_dir,
        config=config,
        batch_id="validation_scanned",
        apply_preprocessing=False
    )

    duration = time.time() - start_time

    print(f"   ✅ Scanned processing complete in {duration:.1f}s")
    print(f"      Processor: {result.get('processor')}")
    print(f"      Chunks: {result.get('chunk_count')}")
    print(f"      Characters: {result.get('char_count'):,}")
    print(f"      JSONL: {result.get('jsonl_path')}")

    return {
        "result": result,
        "duration": duration,
        "jsonl_path": result.get("jsonl_path"),
        "markdown_path": result.get("markdown_path"),
        "temp_pdf": temp_pdf
    }


def load_jsonl(jsonl_path: Path) -> List[Dict]:
    """Load JSONL chunks into list."""
    chunks = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def compare_outputs(digital_jsonl: Path, scanned_jsonl: Path) -> Dict:
    """
    Compare outputs from digital vs scanned pipelines.

    Returns:
        Comparison metrics
    """
    print(f"\n📊 COMPARING OUTPUTS...")
    print("=" * 70)

    digital_chunks = load_jsonl(digital_jsonl)
    scanned_chunks = load_jsonl(scanned_jsonl)

    # Extract full text from each
    digital_text = "\n\n".join([c["text"] for c in digital_chunks])
    scanned_text = "\n\n".join([c["text"] for c in scanned_chunks])

    # Text similarity
    similarity = SequenceMatcher(None, digital_text, scanned_text).ratio()

    # Bbox coverage
    digital_bbox_count = sum(1 for c in digital_chunks if c["attrs"].get("bbox") is not None)
    scanned_bbox_count = sum(1 for c in scanned_chunks if c["attrs"].get("bbox") is not None)

    # Bbox precision
    digital_precise_bbox = sum(
        1 for c in digital_chunks
        if c["attrs"].get("bbox") and c["attrs"]["bbox"].get("x0") is not None
    )
    scanned_precise_bbox = sum(
        1 for c in scanned_chunks
        if c["attrs"].get("bbox") and c["attrs"]["bbox"].get("x0") is not None
    )

    # Table detection
    digital_tables = sum(1 for c in digital_chunks if c["attrs"].get("table", False))
    scanned_tables = sum(1 for c in scanned_chunks if c["attrs"].get("table", False))

    metrics = {
        "digital_chunks": len(digital_chunks),
        "scanned_chunks": len(scanned_chunks),
        "text_similarity": similarity,
        "digital_chars": len(digital_text),
        "scanned_chars": len(scanned_text),
        "char_diff": abs(len(digital_text) - len(scanned_text)),
        "digital_bbox_coverage": digital_bbox_count / len(digital_chunks) if digital_chunks else 0,
        "scanned_bbox_coverage": scanned_bbox_count / len(scanned_chunks) if scanned_chunks else 0,
        "digital_precise_bbox": digital_precise_bbox,
        "scanned_precise_bbox": scanned_precise_bbox,
        "digital_tables": digital_tables,
        "scanned_tables": scanned_tables
    }

    # Print comparison
    print(f"\n📈 Chunk Comparison:")
    print(f"   Digital chunks:  {metrics['digital_chunks']}")
    print(f"   Scanned chunks:  {metrics['scanned_chunks']}")
    print(f"   Difference:      {abs(metrics['digital_chunks'] - metrics['scanned_chunks'])}")

    print(f"\n📝 Text Quality:")
    print(f"   Digital chars:   {metrics['digital_chars']:,}")
    print(f"   Scanned chars:   {metrics['scanned_chars']:,}")
    print(f"   Char difference: {metrics['char_diff']:,}")
    print(f"   Text similarity: {metrics['text_similarity']:.1%}")

    print(f"\n📍 Bbox Coverage:")
    print(f"   Digital bbox:    {metrics['digital_bbox_coverage']:.1%} ({digital_bbox_count}/{len(digital_chunks)})")
    print(f"   Scanned bbox:    {metrics['scanned_bbox_coverage']:.1%} ({scanned_bbox_count}/{len(scanned_chunks)})")

    print(f"\n🎯 Bbox Precision:")
    print(f"   Digital precise: {digital_precise_bbox}/{len(digital_chunks)} chunks")
    print(f"   Scanned precise: {scanned_precise_bbox}/{len(scanned_chunks)} chunks")

    print(f"\n📊 Table Detection:")
    print(f"   Digital tables:  {digital_tables}")
    print(f"   Scanned tables:  {scanned_tables}")

    # Sample chunks for detailed comparison
    print(f"\n🔍 Sample Chunk Comparison:")
    print("-" * 70)

    if digital_chunks and scanned_chunks:
        print(f"\nDigital Chunk 0 (first 200 chars):")
        print(f"   {digital_chunks[0]['text'][:200]}...")
        print(f"   Bbox: {digital_chunks[0]['attrs'].get('bbox')}")

        print(f"\nScanned Chunk 0 (first 200 chars):")
        print(f"   {scanned_chunks[0]['text'][:200]}...")
        print(f"   Bbox: {scanned_chunks[0]['attrs'].get('bbox')}")

    return metrics


def main():
    """Run the validation test."""

    print("=" * 70)
    print("VALIDATION TEST: Digital vs Scanned Pipeline Comparison")
    print("=" * 70)
    print("\n⚠️  This is a research test to validate assumptions.")
    print("    NOT changing the current pipeline strategy.\n")

    # Configuration
    test_output_dir = Path("/home/bryanjowers/pdf-rag/test_output/validation_test")

    # Find a complex digital PDF for testing
    # Use a real legal document, not simple.pdf
    test_pdf_candidates = [
        Path("/home/bryanjowers/pdf-rag/pdf_input/SDTO_170.0 ac 12-5-2022.pdf"),
        Path("/home/bryanjowers/pdf-rag/pdf_input/21-316_WD_Reeves H M to Willis W A et al.pdf"),
        Path("/home/bryanjowers/pdf-rag/pdf_input/checkpoint4_test/simple.pdf")
    ]

    test_pdf = None
    for candidate in test_pdf_candidates:
        if candidate.exists():
            test_pdf = candidate
            break

    if not test_pdf:
        print("❌ No test PDF found. Please provide a complex digital PDF.")
        print(f"   Expected locations: {[str(p) for p in test_pdf_candidates]}")
        return 1

    print(f"📄 Test PDF: {test_pdf.name}")

    # Clean output directory
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Convert PDF to images (simulate scanning)
        images_dir = test_output_dir / "scanned_images"
        image_paths = convert_pdf_to_images(test_pdf, images_dir, dpi=300, max_pages=28)  # Process all 28 pages

        # Step 2: Process through digital pipeline
        digital_result = process_digital_pdf(test_pdf, test_output_dir)

        # Step 3: Process through scanned pipeline
        scanned_result = process_scanned_images(image_paths, test_output_dir)

        # Step 4: Compare outputs
        metrics = compare_outputs(
            digital_result["jsonl_path"],
            scanned_result["jsonl_path"]
        )

        # Step 5: Summary
        print("\n" + "=" * 70)
        print("VALIDATION TEST SUMMARY")
        print("=" * 70)

        print(f"\n⏱️  Performance:")
        print(f"   Digital pipeline:  {digital_result['duration']:.1f}s")
        print(f"   Scanned pipeline:  {scanned_result['duration']:.1f}s")
        print(f"   Speed ratio:       {scanned_result['duration'] / digital_result['duration']:.1f}x slower")

        print(f"\n🎯 Key Findings:")
        print(f"   ✅ Text similarity: {metrics['text_similarity']:.1%}")
        print(f"   ✅ Digital bbox precision: {metrics['digital_precise_bbox']}/{metrics['digital_chunks']}")
        print(f"   ⚠️  Scanned bbox precision: {metrics['scanned_precise_bbox']}/{metrics['scanned_chunks']} (page-level only)")

        # Verdict
        print(f"\n💡 Conclusions:")
        if metrics['text_similarity'] > 0.95:
            print(f"   ✅ Text quality: OlmOCR produces highly similar text ({metrics['text_similarity']:.1%})")
        else:
            print(f"   ⚠️  Text quality: Noticeable differences ({metrics['text_similarity']:.1%} similarity)")

        if metrics['digital_precise_bbox'] > 0:
            print(f"   ✅ Digital PDFs: Full bbox precision available")

        if metrics['scanned_precise_bbox'] == 0:
            print(f"   ℹ️  Scanned PDFs: Page-level bbox only (as expected in MVP)")

        print(f"\n📁 Output files saved to: {test_output_dir}")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
