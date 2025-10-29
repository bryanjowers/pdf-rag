#!/usr/bin/env python3
"""
utils_config.py - Configuration management utilities

Loads and validates YAML configuration with hash computation for reproducibility.
"""

import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: Path | str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file and compute hash for reproducibility.

    Args:
        config_path: Path to config file (default: config/default.yaml)

    Returns:
        Configuration dictionary with computed config_hash

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config is invalid YAML
    """
    if config_path is None:
        # Default to config/default.yaml relative to project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "default.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load YAML
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Compute config hash for reproducibility
    config_content = config_path.read_text(encoding="utf-8")
    config_hash = hashlib.sha256(config_content.encode()).hexdigest()

    # Inject computed hash
    if "metadata" not in config:
        config["metadata"] = {}
    config["metadata"]["config_hash"] = config_hash[:16]  # First 16 chars for brevity

    return config


def get_config_version(config: Dict) -> str:
    """
    Extract config version for logging.

    Args:
        config: Configuration dictionary

    Returns:
        Version string (e.g., "2.2.0")
    """
    return config.get("metadata", {}).get("config_version", "unknown")


def get_config_hash(config: Dict) -> str:
    """
    Extract config hash for logging.

    Args:
        config: Configuration dictionary

    Returns:
        Config hash (truncated SHA256)
    """
    return config.get("metadata", {}).get("config_hash", "unknown")


def validate_config(config: Dict) -> tuple[bool, list[str]]:
    """
    Validate that required config sections and keys exist.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (valid: bool, errors: list[str])
    """
    errors = []

    # Required top-level sections
    required_sections = [
        "classification",
        "chunking",
        "xlsx",
        "tables",
        "processors",
        "schema",
        "storage"
    ]

    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required config section: {section}")

    # Validate critical thresholds
    try:
        max_pages = config["classification"]["max_pages_absolute"]
        if not isinstance(max_pages, int) or max_pages <= 0:
            errors.append("classification.max_pages_absolute must be a positive integer")
    except KeyError:
        errors.append("Missing required key: classification.max_pages_absolute")

    try:
        percent_cutoff = config["classification"]["percent_digital_cutoff"]
        if not isinstance(percent_cutoff, (int, float)) or not 0 <= percent_cutoff <= 1:
            errors.append("classification.percent_digital_cutoff must be between 0 and 1")
    except KeyError:
        errors.append("Missing required key: classification.percent_digital_cutoff")

    return len(errors) == 0, errors


def get_storage_paths(config: Dict) -> Dict[str, Path]:
    """
    Extract all storage paths from config as Path objects.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary mapping storage keys to Path objects
    """
    storage = config.get("storage", {})
    base = Path(storage.get("gcs_mount_base", "/mnt/gcs/legal-ocr-results"))

    return {
        "gcs_mount_base": base,
        "input_bucket": Path(storage.get("input_bucket", "/mnt/gcs/legal-ocr-pdf-input")),
        "rag_staging": base / storage.get("rag_staging", "rag_staging"),
        "html_output": base / storage.get("html_output", "rag_staging/html"),
        "markdown_output": base / storage.get("markdown_output", "rag_staging/markdown"),
        "jsonl_output": base / storage.get("jsonl_output", "rag_staging/jsonl"),
        "log_dir": base / storage.get("log_dir", "logs"),
        "report_dir": base / storage.get("report_dir", "reports"),
        "manifest_dir": base / storage.get("manifest_dir", "manifests"),
        "inventory_dir": base / storage.get("inventory_dir", "inventory"),
        "quarantine_dir": base / storage.get("quarantine_dir", "quarantine"),
        "lock_file": base / storage.get("lock_file", ".process_documents.lock")
    }


def print_config_summary(config: Dict) -> None:
    """
    Print human-readable config summary for logging.

    Args:
        config: Configuration dictionary
    """
    version = get_config_version(config)
    config_hash = get_config_hash(config)

    print(f"📋 Configuration Loaded")
    print(f"   Version: {version}")
    print(f"   Hash: {config_hash}")
    print(f"   Max PDF Pages: {config.get('classification', {}).get('max_pages_absolute', 'N/A')}")
    print(f"   Digital Cutoff: {config.get('classification', {}).get('percent_digital_cutoff', 'N/A')}")
    print(f"   Token Range: {config.get('chunking', {}).get('token_min', 'N/A')}-{config.get('chunking', {}).get('token_max', 'N/A')}")
    print()
