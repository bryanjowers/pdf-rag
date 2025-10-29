#!/bin/bash
# cleanup_rag_staging.sh
# Cleans up all processed outputs in rag_staging to allow reprocessing
# Preserves directory structure but removes all files

set -e

RAG_STAGING="/mnt/gcs/legal-ocr-results/rag_staging"

echo "🧹 Cleaning up rag_staging contents..."
echo "Target: $RAG_STAGING"
echo ""

# Confirm before proceeding
read -p "This will delete all processed files. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

# Remove all files from subdirectories
echo "Removing done_flags..."
rm -f "$RAG_STAGING/done_flags"/*.flag

echo "Removing html outputs..."
rm -f "$RAG_STAGING/html"/*.html

echo "Removing jsonl files..."
rm -f "$RAG_STAGING/jsonl"/*.jsonl

echo "Removing markdown files..."
rm -f "$RAG_STAGING/markdown"/*.md

echo "Removing results..."
rm -f "$RAG_STAGING/results"/*

echo "Removing worker locks..."
rm -f "$RAG_STAGING/worker_locks"/*

echo "Removing work index..."
rm -f "$RAG_STAGING/work_index_list.csv.zstd"

# Also clean up logs and reports
echo "Removing logs..."
rm -f /mnt/gcs/legal-ocr-results/logs/*.log
rm -f /mnt/gcs/legal-ocr-results/logs/*_summary.json

echo "Removing reports..."
rm -f /mnt/gcs/legal-ocr-results/reports/*.json

echo ""
echo "✅ Cleanup complete! rag_staging is ready for reprocessing."
echo ""
echo "Directory structure preserved:"
ls -la "$RAG_STAGING"
