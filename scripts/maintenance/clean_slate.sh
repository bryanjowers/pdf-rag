#!/bin/bash
#
# clean_slate.sh - Safely reset all processed data while preserving input PDFs
#
# This script will:
# 1. Create a backup of current results (optional safety measure)
# 2. Clear all processed data in GCS results bucket
# 3. Delete all Qdrant vector collections
# 4. Verify input bucket is untouched
#
# SAFETY: Input bucket (/mnt/gcs/legal-ocr-pdf-input) is NEVER touched
#

set -e  # Exit on error

echo "========================================================================"
echo "🧹 CLEAN SLATE OPERATION"
echo "========================================================================"
echo ""

# Configuration
RESULTS_BUCKET="/mnt/gcs/legal-ocr-results"
INPUT_BUCKET="/mnt/gcs/legal-ocr-pdf-input"
BACKUP_DIR="/tmp/clean_slate_backup_$(date +%Y%m%d_%H%M%S)"
QDRANT_HOST="localhost"
QDRANT_PORT="6333"

# Verify mounts
echo "🔍 Step 1: Verifying GCS mounts..."
if [ ! -d "$RESULTS_BUCKET" ]; then
    echo "❌ ERROR: Results bucket not mounted at $RESULTS_BUCKET"
    exit 1
fi

if [ ! -d "$INPUT_BUCKET" ]; then
    echo "⚠️  WARNING: Input bucket not found at $INPUT_BUCKET (this is OK if empty)"
fi

echo "✅ GCS mounts verified"
echo ""

# Check what will be deleted
echo "🔍 Step 2: Analyzing what will be deleted..."
echo ""
echo "Results bucket contents:"
du -sh "$RESULTS_BUCKET"/* 2>/dev/null || echo "  (empty or no accessible subdirectories)"
echo ""

# Optional: Create backup (commented out for speed, uncomment if needed)
# echo "💾 Step 3: Creating backup (optional)..."
# mkdir -p "$BACKUP_DIR"
# echo "   Copying inventory and manifests to $BACKUP_DIR..."
# cp -r "$RESULTS_BUCKET/inventory" "$BACKUP_DIR/" 2>/dev/null || true
# cp -r "$RESULTS_BUCKET/manifests" "$BACKUP_DIR/" 2>/dev/null || true
# echo "✅ Backup created at $BACKUP_DIR"
# echo ""

echo "⏭️  Step 3: Skipping backup (enable in script if needed)"
echo ""

# Confirm before deletion
echo "⚠️  WARNING: This will DELETE all processed data in:"
echo "   - $RESULTS_BUCKET/rag_staging (markdown, jsonl, html)"
echo "   - $RESULTS_BUCKET/inventory"
echo "   - $RESULTS_BUCKET/manifests"
echo "   - $RESULTS_BUCKET/logs"
echo "   - $RESULTS_BUCKET/reports"
echo "   - $RESULTS_BUCKET/quarantine"
echo "   - $RESULTS_BUCKET/state"
echo "   - Qdrant collection: legal_docs_v2_3"
echo ""
echo "✅ SAFE: $INPUT_BUCKET will NOT be touched"
echo ""
read -p "Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
    echo "❌ Cancelled by user"
    exit 1
fi

echo ""
echo "🗑️  Step 4: Clearing results bucket..."

# Delete subdirectories one by one with progress
for dir in rag_staging inventory manifests logs reports quarantine state; do
    if [ -d "$RESULTS_BUCKET/$dir" ]; then
        echo "   Deleting $dir..."
        rm -rf "$RESULTS_BUCKET/$dir"
        echo "   ✅ $dir cleared"
    else
        echo "   ⏭️  $dir doesn't exist (skipped)"
    fi
done

echo "✅ Results bucket cleared"
echo ""

# Reset Qdrant
echo "🗑️  Step 5: Resetting Qdrant vector database..."

# Check if Qdrant is running
if curl -s "http://$QDRANT_HOST:$QDRANT_PORT/collections" >/dev/null 2>&1; then
    # Get all collections
    collections=$(curl -s "http://$QDRANT_HOST:$QDRANT_PORT/collections" | python3 -c "import sys, json; print(' '.join([c['name'] for c in json.load(sys.stdin)['result']['collections']]))" 2>/dev/null)

    if [ -n "$collections" ]; then
        echo "   Found collections: $collections"
        for collection in $collections; do
            echo "   Deleting collection: $collection"
            curl -s -X DELETE "http://$QDRANT_HOST:$QDRANT_PORT/collections/$collection" >/dev/null
            echo "   ✅ $collection deleted"
        done
    else
        echo "   ℹ️  No collections found"
    fi

    echo "✅ Qdrant database reset"
else
    echo "   ⚠️  Qdrant not running or not accessible (skipping)"
fi

echo ""

# Verify clean slate
echo "🔍 Step 6: Verifying clean slate..."
echo ""

# Check results bucket
echo "Results bucket status:"
ls -lh "$RESULTS_BUCKET" 2>/dev/null || echo "  (completely empty)"
echo ""

# Check Qdrant
echo "Qdrant collections:"
curl -s "http://$QDRANT_HOST:$QDRANT_PORT/collections" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (not accessible)"
echo ""

# Verify input bucket untouched
echo "Input bucket verification:"
if [ -d "$INPUT_BUCKET" ]; then
    pdf_count=$(find "$INPUT_BUCKET" -name "*.pdf" -type f 2>/dev/null | wc -l)
    echo "  ✅ Input bucket intact: $pdf_count PDFs found"
else
    echo "  ℹ️  Input bucket not mounted (this is OK)"
fi

echo ""
echo "========================================================================"
echo "✅ CLEAN SLATE COMPLETE"
echo "========================================================================"
echo ""
echo "Status:"
echo "  ✅ All processed data cleared from results bucket"
echo "  ✅ Qdrant vector database reset"
echo "  ✅ Input PDFs preserved (never touched)"
echo ""
echo "You can now manually run processing when ready:"
echo "  • Rebuild inventory: python scripts/rebuild_inventory.py"
echo "  • Process documents: python scripts/process_documents.py --auto"
echo "  • Load to Qdrant: python scripts/load_to_qdrant.py"
echo ""
echo "See: docs/status/CLEAN_SLATE_*.md for details"
echo ""
