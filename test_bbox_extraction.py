#!/usr/bin/env python
"""
Bbox Extraction Spike Test
Tests if Docling exposes bounding box coordinates in its output
"""

import json
from docling.document_converter import DocumentConverter

def find_bbox_fields(obj, path="", depth=0, max_depth=10):
    """Recursively search for bbox-related fields"""
    if depth > max_depth:
        return

    bbox_keywords = ['bbox', 'bound', 'coord', 'position', 'rect', 'x0', 'y0', 'x1', 'y1']

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key

            # Check if key contains bbox-related terms
            if any(keyword in key.lower() for keyword in bbox_keywords):
                print(f"✅ Found bbox-related field: {new_path}")
                print(f"   Type: {type(value)}")
                print(f"   Sample: {str(value)[:200]}")
                print()

            find_bbox_fields(value, new_path, depth + 1, max_depth)

    elif isinstance(obj, list) and obj:
        # Only check first item in lists
        find_bbox_fields(obj[0], f"{path}[0]", depth + 1, max_depth)


def test_docling_bbox(pdf_path):
    """Test Docling's bbox extraction capabilities"""

    print("=" * 80)
    print("DOCLING BBOX EXTRACTION SPIKE TEST")
    print("=" * 80)
    print(f"\nTesting PDF: {pdf_path}\n")

    # Convert document
    print("Converting document with Docling...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    print(f"✅ Conversion complete\n")

    # Export to dict
    doc_dict = result.document.export_to_dict()

    print("=" * 80)
    print("SEARCHING FOR BBOX FIELDS")
    print("=" * 80)
    print()

    # Search for bbox fields
    find_bbox_fields(doc_dict, max_depth=8)

    print("=" * 80)
    print("DOCUMENT STRUCTURE OVERVIEW")
    print("=" * 80)
    print()

    # Show top-level structure
    print("Top-level keys:")
    for key in doc_dict.keys():
        value = doc_dict[key]
        val_type = type(value).__name__

        if isinstance(value, list):
            length = len(value)
            print(f"  - {key}: {val_type} (length: {length})")
        elif isinstance(value, dict):
            keys = list(value.keys())[:5]
            print(f"  - {key}: {val_type} (keys: {keys}...)")
        else:
            preview = str(value)[:50]
            print(f"  - {key}: {val_type} (value: {preview}...)")

    print()

    # Check for chunks/pages
    if 'pages' in doc_dict:
        print(f"✅ Found 'pages' field")
        pages = doc_dict['pages']
        if pages and len(pages) > 0:
            print(f"   Total pages: {len(pages)}")
            print(f"   First page keys: {list(pages[0].keys())}")
            print()

            # Check first page for bbox info
            first_page = pages[0]
            if 'elements' in first_page:
                print(f"   Page has {len(first_page['elements'])} elements")
                if first_page['elements']:
                    elem = first_page['elements'][0]
                    print(f"   First element keys: {list(elem.keys())}")
                    print(f"   First element sample: {json.dumps(elem, indent=2)[:500]}")

    print()
    print("=" * 80)
    print("RAW DOCLING RESULT ATTRIBUTES")
    print("=" * 80)
    print()

    # Check result object attributes
    print("DocumentConversionResult attributes:")
    result_attrs = [attr for attr in dir(result) if not attr.startswith('_')]
    for attr in result_attrs[:20]:  # First 20 attributes
        try:
            value = getattr(result, attr)
            if not callable(value):
                print(f"  - {attr}: {type(value).__name__}")
        except:
            pass

    print()

    # Check document object
    if hasattr(result, 'document'):
        doc = result.document
        print("Document object attributes:")
        doc_attrs = [attr for attr in dir(doc) if not attr.startswith('_')]
        for attr in doc_attrs[:20]:
            try:
                value = getattr(doc, attr)
                if not callable(value):
                    print(f"  - {attr}: {type(value).__name__}")
            except:
                pass

    print()
    print("=" * 80)
    print("BBOX EXTRACTION TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "pdf_input/checkpoint4_test/simple.pdf"

    test_docling_bbox(pdf_path)
