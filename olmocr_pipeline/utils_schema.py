#!/usr/bin/env python3
"""
utils_schema.py - JSONL schema validation and QA utilities

Validates JSONL records against unified schema v2.2.0 and performs
token range quality assurance checks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def validate_jsonl_record(record: Dict, config: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a single JSONL record against schema requirements.

    Args:
        record: JSONL record dictionary
        config: Configuration dictionary

    Returns:
        Tuple of (valid: bool, errors: list[str])
    """
    errors = []

    # Get required fields from config
    required_fields = config.get("schema", {}).get("required_fields", [
        "id", "doc_id", "chunk_index", "text", "attrs", "source", "metadata"
    ])

    # Check required top-level fields
    for field in required_fields:
        if field not in record:
            errors.append(f"Missing required field: {field}")

    # Validate id format (should be doc_id_NNNN)
    if "id" in record and "doc_id" in record:
        expected_prefix = record["doc_id"]
        if not record["id"].startswith(expected_prefix):
            errors.append(f"Invalid id format: {record['id']} (expected to start with {expected_prefix})")

    # Validate chunk_index is non-negative integer
    if "chunk_index" in record:
        if not isinstance(record["chunk_index"], int) or record["chunk_index"] < 0:
            errors.append(f"Invalid chunk_index: {record['chunk_index']} (must be non-negative integer)")

    # Validate text is non-empty string
    if "text" in record:
        if not isinstance(record["text"], str) or not record["text"].strip():
            errors.append("Text field is empty or invalid")

    # Validate attrs structure
    if "attrs" in record:
        attrs = record["attrs"]
        if not isinstance(attrs, dict):
            errors.append("attrs must be a dictionary")
        else:
            # Check for token_count
            if "token_count" not in attrs:
                errors.append("attrs.token_count is required")
            elif not isinstance(attrs["token_count"], int) or attrs["token_count"] <= 0:
                errors.append(f"Invalid token_count: {attrs['token_count']}")

    # Validate source structure
    if "source" in record:
        source = record["source"]
        if not isinstance(source, dict):
            errors.append("source must be a dictionary")
        else:
            for field in ["file_path", "file_name", "file_type", "mime_type"]:
                if field not in source:
                    errors.append(f"source.{field} is required")

    # Validate metadata structure
    if "metadata" in record:
        metadata = record["metadata"]
        if not isinstance(metadata, dict):
            errors.append("metadata must be a dictionary")
        else:
            required_metadata = config.get("schema", {}).get("metadata_fields", [
                "schema_version", "file_type", "hash_input_sha256", "processor", "batch_id"
            ])
            for field in required_metadata:
                if field not in metadata:
                    errors.append(f"metadata.{field} is required")

    return len(errors) == 0, errors


def validate_jsonl_file(jsonl_path: Path, config: Dict) -> Dict:
    """
    Validate entire JSONL file and return summary.

    Args:
        jsonl_path: Path to JSONL file
        config: Configuration dictionary

    Returns:
        Validation summary dictionary:
        {
            "valid": bool,
            "total_records": int,
            "valid_records": int,
            "invalid_records": int,
            "errors": list[dict],  # [{record_index, errors}]
            "warnings": list[str]
        }

    Raises:
        FileNotFoundError: If JSONL file doesn't exist
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    total_records = 0
    valid_records = 0
    invalid_records = 0
    all_errors = []
    warnings = []

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
                total_records += 1

                # Validate record
                is_valid, errors = validate_jsonl_record(record, config)

                if is_valid:
                    valid_records += 1
                else:
                    invalid_records += 1
                    all_errors.append({
                        "record_index": total_records - 1,
                        "line_number": line_num,
                        "errors": errors
                    })

            except json.JSONDecodeError as e:
                total_records += 1
                invalid_records += 1
                all_errors.append({
                    "record_index": total_records - 1,
                    "line_number": line_num,
                    "errors": [f"JSON parse error: {e}"]
                })

    return {
        "valid": invalid_records == 0,
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "errors": all_errors,
        "warnings": warnings
    }


def validate_markdown_tables(markdown_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate markdown table structure (column consistency).

    Args:
        markdown_path: Path to markdown file

    Returns:
        Tuple of (valid: bool, errors: list[str])
    """
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

    errors = []
    content = markdown_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    current_table = []
    table_start_line = None

    for line_num, line in enumerate(lines, 1):
        # Detect table lines (contain pipe characters)
        if "|" in line and line.strip().startswith("|"):
            if not current_table:
                table_start_line = line_num

            # Count columns
            col_count = len([c for c in line.split("|") if c.strip()])
            current_table.append((line_num, col_count, line.strip()))

        else:
            # End of table
            if current_table:
                # Validate column consistency
                if len(current_table) > 1:
                    # Get column count from first row
                    first_row_cols = current_table[0][1]

                    # Check all rows have same column count
                    for row_line_num, row_cols, row_text in current_table:
                        if row_cols != first_row_cols:
                            errors.append(
                                f"Line {row_line_num}: Inconsistent column count "
                                f"({row_cols} cols, expected {first_row_cols})"
                            )

                current_table = []
                table_start_line = None

    return len(errors) == 0, errors


def compute_chunk_stats(jsonl_path: Path, config: Dict) -> Dict:
    """
    Compute token distribution statistics for chunks.

    Args:
        jsonl_path: Path to JSONL file
        config: Configuration dictionary

    Returns:
        Statistics dictionary:
        {
            "total_chunks": int,
            "min_tokens": int,
            "max_tokens": int,
            "avg_tokens": float,
            "median_tokens": int,
            "out_of_range_count": int,
            "out_of_range_percent": float,
            "token_distribution": dict  # {range: count}
        }

    Raises:
        FileNotFoundError: If JSONL file doesn't exist
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    # Get token range from config
    chunking_config = config.get("chunking", {})
    token_min = chunking_config.get("token_min", 800)
    token_max = chunking_config.get("token_max", 2000)

    token_counts = []

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
                token_count = record.get("attrs", {}).get("token_count", 0)
                token_counts.append(token_count)
            except json.JSONDecodeError:
                continue

    if not token_counts:
        return {
            "total_chunks": 0,
            "min_tokens": 0,
            "max_tokens": 0,
            "avg_tokens": 0.0,
            "median_tokens": 0,
            "out_of_range_count": 0,
            "out_of_range_percent": 0.0,
            "token_distribution": {}
        }

    # Compute statistics
    total_chunks = len(token_counts)
    min_tokens = min(token_counts)
    max_tokens = max(token_counts)
    avg_tokens = sum(token_counts) / total_chunks
    sorted_tokens = sorted(token_counts)
    median_tokens = sorted_tokens[total_chunks // 2]

    # Count out of range
    out_of_range = sum(1 for t in token_counts if t < token_min or t > token_max)
    out_of_range_percent = (out_of_range / total_chunks) * 100

    # Token distribution by range
    distribution = {
        "< 500": sum(1 for t in token_counts if t < 500),
        "500-800": sum(1 for t in token_counts if 500 <= t < 800),
        "800-1200": sum(1 for t in token_counts if 800 <= t < 1200),
        "1200-1600": sum(1 for t in token_counts if 1200 <= t < 1600),
        "1600-2000": sum(1 for t in token_counts if 1600 <= t < 2000),
        "2000-2500": sum(1 for t in token_counts if 2000 <= t < 2500),
        "> 2500": sum(1 for t in token_counts if t >= 2500)
    }

    return {
        "total_chunks": total_chunks,
        "min_tokens": min_tokens,
        "max_tokens": max_tokens,
        "avg_tokens": avg_tokens,
        "median_tokens": median_tokens,
        "out_of_range_count": out_of_range,
        "out_of_range_percent": out_of_range_percent,
        "token_distribution": distribution
    }


def check_token_range_qa(jsonl_path: Path, config: Dict) -> Tuple[str, str]:
    """
    Perform QA checks on token ranges and return status + message.

    Args:
        jsonl_path: Path to JSONL file
        config: Configuration dictionary

    Returns:
        Tuple of (status: "pass"|"warn"|"fail", message: str)
    """
    stats = compute_chunk_stats(jsonl_path, config)

    if stats["total_chunks"] == 0:
        return "fail", "No chunks found in JSONL file"

    # Get QA thresholds
    chunking_config = config.get("chunking", {})
    qa_warn_below = chunking_config.get("qa_warn_below", 700)
    qa_warn_above = chunking_config.get("qa_warn_above", 2200)
    qa_warn_threshold = chunking_config.get("qa_warn_threshold", 0.05)  # 5%
    qa_fail_threshold = chunking_config.get("qa_fail_threshold", 0.10)  # 10%

    out_of_range_percent = stats["out_of_range_percent"]

    # Check thresholds
    if out_of_range_percent > qa_fail_threshold * 100:
        return "fail", (
            f"FAIL: {out_of_range_percent:.1f}% of chunks out of range "
            f"(threshold: {qa_fail_threshold*100}%)"
        )
    elif out_of_range_percent > qa_warn_threshold * 100:
        return "warn", (
            f"WARNING: {out_of_range_percent:.1f}% of chunks out of range "
            f"(threshold: {qa_warn_threshold*100}%)"
        )
    else:
        return "pass", (
            f"PASS: {out_of_range_percent:.1f}% out of range "
            f"(min: {stats['min_tokens']}, max: {stats['max_tokens']}, avg: {stats['avg_tokens']:.0f})"
        )


def print_validation_summary(validation_result: Dict) -> None:
    """
    Print human-readable validation summary.

    Args:
        validation_result: Result from validate_jsonl_file()
    """
    status = "✅ VALID" if validation_result["valid"] else "❌ INVALID"
    print(f"\n{status} - JSONL Validation Summary")
    print(f"   Total records: {validation_result['total_records']}")
    print(f"   Valid: {validation_result['valid_records']}")
    print(f"   Invalid: {validation_result['invalid_records']}")

    if validation_result["errors"]:
        print(f"\n   Errors found:")
        for error_info in validation_result["errors"][:5]:  # Show first 5
            print(f"      Record {error_info['record_index']} (line {error_info['line_number']}):")
            for err in error_info["errors"]:
                print(f"         - {err}")

        if len(validation_result["errors"]) > 5:
            print(f"      ... and {len(validation_result['errors']) - 5} more errors")

    if validation_result["warnings"]:
        print(f"\n   Warnings:")
        for warning in validation_result["warnings"]:
            print(f"      - {warning}")


def print_chunk_stats(stats: Dict) -> None:
    """
    Print human-readable chunk statistics.

    Args:
        stats: Result from compute_chunk_stats()
    """
    print(f"\n📊 Chunk Token Statistics")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Token range: {stats['min_tokens']} - {stats['max_tokens']}")
    print(f"   Average: {stats['avg_tokens']:.0f}")
    print(f"   Median: {stats['median_tokens']}")
    print(f"   Out of range: {stats['out_of_range_count']} ({stats['out_of_range_percent']:.1f}%)")

    print(f"\n   Distribution:")
    for range_label, count in stats['token_distribution'].items():
        if count > 0:
            percent = (count / stats['total_chunks']) * 100
            bar = "█" * int(percent / 2)  # Scale to fit
            print(f"      {range_label:12s}: {count:3d} ({percent:5.1f}%) {bar}")
