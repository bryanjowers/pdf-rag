#!/usr/bin/env python3
"""
utils_state.py - Processing state management using _SUCCESS markers

Tracks processed files by reading _SUCCESS markers as the source of truth.
Provides fast filtering to avoid reprocessing files.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional
import json
import time


def get_processed_hashes(
    jsonl_dir: Path,
    use_cache: bool = True,
    cache_path: Optional[Path] = None
) -> Set[str]:
    """
    Get set of hashes for successfully processed files.

    Scans _SUCCESS markers in the JSONL directory to determine which files
    have been successfully processed. Optionally caches results for performance.

    Args:
        jsonl_dir: Directory containing JSONL outputs and _SUCCESS markers
        use_cache: Whether to use cached index (default: True)
        cache_path: Path to cache file (default: auto-detect)

    Returns:
        Set of SHA256 hashes for processed files

    Example:
        >>> processed = get_processed_hashes(Path("/mnt/gcs/.../jsonl"))
        >>> print(f"Found {len(processed)} processed files")
    """
    # Default cache path
    if cache_path is None:
        cache_path = jsonl_dir.parent / "state" / "processed_hashes.json"

    # Try cache first if enabled
    if use_cache:
        cached_hashes = _load_cache(cache_path, jsonl_dir)
        if cached_hashes is not None:
            return cached_hashes

    # Cold scan: read all _SUCCESS markers
    processed_hashes = set()
    success_markers = list(jsonl_dir.glob("*_SUCCESS"))

    for marker in success_markers:
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            file_hash = data.get("file_hash")
            if file_hash:
                processed_hashes.add(file_hash)
        except Exception as e:
            # Silently skip corrupted markers
            continue

    # Write cache if enabled
    if use_cache:
        _write_cache(cache_path, processed_hashes, jsonl_dir)

    return processed_hashes


def filter_unprocessed_files(
    inventory: List[Dict],
    processed_hashes: Set[str]
) -> List[Dict]:
    """
    Filter inventory to only unprocessed files.

    Args:
        inventory: List of inventory records (from utils_inventory.load_inventory)
        processed_hashes: Set of processed file hashes (from get_processed_hashes)

    Returns:
        Filtered inventory with only unprocessed files

    Example:
        >>> inventory = load_inventory(inv_path)
        >>> processed = get_processed_hashes(jsonl_dir)
        >>> unprocessed = filter_unprocessed_files(inventory, processed)
        >>> print(f"Remaining: {len(unprocessed)}/{len(inventory)}")
    """
    return [
        record for record in inventory
        if record.get("hash_sha256") not in processed_hashes
    ]


def clear_processed_state(
    jsonl_dir: Path,
    hash_sha256: Optional[str] = None,
    cache_path: Optional[Path] = None
) -> int:
    """
    Clear processing state for reprocessing files.

    Deletes _SUCCESS markers to allow files to be reprocessed.
    Also clears the cache.

    Args:
        jsonl_dir: Directory containing _SUCCESS markers
        hash_sha256: If provided, only clear this specific hash (prefix match supported).
                     If None, clear all markers.
        cache_path: Path to cache file (default: auto-detect)

    Returns:
        Number of markers deleted

    Example:
        >>> # Clear specific file
        >>> cleared = clear_processed_state(jsonl_dir, hash_sha256="abc123")
        >>>
        >>> # Clear all files
        >>> cleared = clear_processed_state(jsonl_dir)
    """
    if cache_path is None:
        cache_path = jsonl_dir.parent / "state" / "processed_hashes.json"

    deleted = 0

    if hash_sha256:
        # Find and delete specific marker(s) matching hash prefix
        for marker in jsonl_dir.glob("*_SUCCESS"):
            try:
                data = json.loads(marker.read_text(encoding="utf-8"))
                marker_hash = data.get("file_hash", "")

                # Support prefix matching (user can provide first 16 chars)
                if marker_hash.startswith(hash_sha256):
                    marker.unlink()
                    deleted += 1
            except Exception:
                continue
    else:
        # Delete all markers
        for marker in jsonl_dir.glob("*_SUCCESS"):
            try:
                marker.unlink()
                deleted += 1
            except Exception:
                continue

    # Clear cache
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception:
            pass

    return deleted


def _load_cache(cache_path: Path, jsonl_dir: Path) -> Optional[Set[str]]:
    """
    Load cached hash set if valid.

    Cache is considered valid if the count of SUCCESS markers matches
    the cached count. This is more reliable than directory mtime on GCS mounts.
    """
    if not cache_path.exists():
        return None

    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))

        # Count current SUCCESS markers
        current_marker_count = len(list(jsonl_dir.glob("*_SUCCESS")))
        cached_marker_count = cache_data.get("marker_count", -1)

        if current_marker_count != cached_marker_count:
            # Cache stale (marker count changed)
            return None

        return set(cache_data.get("processed_hashes", []))

    except Exception:
        # Corrupted cache, ignore
        return None


def _write_cache(cache_path: Path, hashes: Set[str], jsonl_dir: Path) -> None:
    """
    Write hash set to cache file.

    Uses atomic rename pattern to avoid corrupted cache on crash.
    """
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        marker_count = len(list(jsonl_dir.glob("*_SUCCESS")))

        cache_data = {
            "processed_hashes": sorted(list(hashes)),  # Sort for diff-friendly output
            "built_at": time.time(),
            "marker_count": marker_count,  # Used for cache invalidation
            "count": len(hashes)
        }

        # Atomic write (write to temp, then rename)
        tmp_path = cache_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        tmp_path.rename(cache_path)

    except Exception:
        # Cache write failure is non-fatal, just slower next time
        pass
