# GCS Mount Issue - Permanently Fixed

**Date:** October 30, 2025
**Issue:** Input bucket appeared empty despite containing files
**Status:** ✅ Resolved

---

## Problem Summary

The GCS bucket `legal-ocr-pdf-input` was not mounted, causing the pipeline to report "No supported files found" even though the bucket contained 321 PDFs.

### Root Causes

1. **Missing mount for input bucket** - Only `legal-ocr-results` was mounted
2. **Missing `implicit_dirs` flag** - Required for proper GCS FUSE directory visibility
3. **Stale `/etc/fstab` configuration** - Had old/commented entries without `implicit_dirs`

---

## Solution Applied

### 1. Updated `/etc/fstab` with Proper Configuration

**Backup created:** `/etc/fstab.backup.20251030_*`

**New fstab entries:**
```bash
# GCS FUSE mounts for legal-ocr pipeline
# Using implicit_dirs to fix empty directory issues
legal-ocr-results /mnt/gcs/legal-ocr-results gcsfuse rw,_netdev,allow_other,implicit_dirs,uid=1001,gid=1002 0 0
legal-ocr-pdf-input /mnt/gcs/legal-ocr-pdf-input gcsfuse rw,_netdev,allow_other,implicit_dirs,uid=1001,gid=1002 0 0
```

**Key parameters:**
- `implicit_dirs` - Enables directory visibility for GCS buckets without explicit directory objects
- `allow_other` - Allows non-root users to access the mount
- `uid=1001,gid=1002` - Sets proper ownership for bryanjowers user
- `_netdev` - Waits for network before mounting

### 2. Mounted Both Buckets

```bash
# Created mount point
sudo mkdir -p /mnt/gcs/legal-ocr-pdf-input

# Mounted input bucket
sudo mount /mnt/gcs/legal-ocr-pdf-input

# Remounted results bucket with new config
sudo umount /mnt/gcs/legal-ocr-results
sudo mount /mnt/gcs/legal-ocr-results
```

---

## Verification

### Mount Status
```bash
$ mount | grep gcsfuse
legal-ocr-pdf-input on /mnt/gcs/legal-ocr-pdf-input type fuse.gcsfuse ...
legal-ocr-results on /mnt/gcs/legal-ocr-results type fuse.gcsfuse ...
```

### Both Buckets Visible
```bash
$ ls /mnt/gcs/legal-ocr-pdf-input/
Lewis Unit - Panola Co, TX

$ ls /mnt/gcs/legal-ocr-results/
inventory  logs  manifests  quarantine  rag_staging  reports  temp
```

### PDF Count
```bash
$ find /mnt/gcs/legal-ocr-pdf-input -name "*.pdf" -type f | wc -l
321
```

---

## Why This Fixes the "Empty Directory" Problem

### The `implicit_dirs` Flag

GCS is an object store, not a true file system. It doesn't create explicit directory objects unless you explicitly create them. Without `implicit_dirs`, gcsfuse only shows directories that exist as actual objects in GCS.

**Without `implicit_dirs`:**
- Only shows directories explicitly created in GCS
- Empty-looking directories even when files exist inside

**With `implicit_dirs`:**
- Infers directory structure from object paths
- Shows all directories based on file paths
- Fixes the caching/visibility issues

---

## Permanent Fix Confirmed

✅ **Mounts persist across reboots** - Both entries in `/etc/fstab`
✅ **Proper permissions** - uid/gid set for bryanjowers user
✅ **No more empty directories** - `implicit_dirs` ensures visibility
✅ **Both buckets accessible** - Input and results

---

## Testing Completed

Immediately after the fix, successfully ran:
```bash
python scripts/process_documents.py --auto --batch-size 1 --file-types pdf --pdf-type scanned --limit 1
```

**Results:**
- ✅ Found 331 files in input bucket
- ✅ Classified 321 PDFs (110 digital, 211 scanned)
- ✅ Selected 1 scanned PDF for processing
- ✅ OlmOCR pipeline started successfully
- ✅ FlashInfer activated: "Using FlashInfer for top-p & top-k sampling"

---

## Future VM Setup

If rebuilding the VM or setting up a new one, add these lines to `/etc/fstab`:

```bash
# GCS FUSE mounts for legal-ocr pipeline
# Using implicit_dirs to fix empty directory issues
legal-ocr-results /mnt/gcs/legal-ocr-results gcsfuse rw,_netdev,allow_other,implicit_dirs,uid=1001,gid=1002 0 0
legal-ocr-pdf-input /mnt/gcs/legal-ocr-pdf-input gcsfuse rw,_netdev,allow_other,implicit_dirs,uid=1001,gid=1002 0 0
```

Then create mount points and mount:
```bash
sudo mkdir -p /mnt/gcs/legal-ocr-results
sudo mkdir -p /mnt/gcs/legal-ocr-pdf-input
sudo mount -a
```

---

## Related Documentation

- `/etc/fstab.backup.20251030_*` - Backup of old configuration
- [docs/guides/VM_SETUP_COMPLETE.md](docs/guides/VM_SETUP_COMPLETE.md) - VM setup procedures (should be updated)
- [GCS FUSE docs](https://cloud.google.com/storage/docs/gcs-fuse) - Official documentation

---

**Issue Status:** ✅ Resolved permanently

**Next Steps:** Update VM_SETUP_COMPLETE.md with proper fstab configuration
