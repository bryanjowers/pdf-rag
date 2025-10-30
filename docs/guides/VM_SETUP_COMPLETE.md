# Complete VM Setup Guide - Disaster Recovery

**Purpose:** Rebuild the entire pipeline on a fresh VM from scratch
**Time Required:** ~2-3 hours
**Last Updated:** October 31, 2025

---

## 🎯 Prerequisites

- **VM Specs:** NVIDIA GPU with minimum 15GB VRAM (L4 24GB recommended)
- **Disk Space:** Minimum 30GB available
- **OS:** Ubuntu 22.04 LTS (recommended)
- **Python:** Python 3.11 (required for OlmOCR)
- **CUDA:** CUDA 12.8 support (installed via PyTorch)
- **Access:** SSH access, sudo privileges
- **GCS Access:** Service account credentials for GCS buckets

**Hardware Reference:** [OlmOCR Requirements](https://github.com/allenai/olmocr?tab=readme-ov-file#system-requirements)

---

## 📋 Complete Setup Checklist

### Phase 1: System Dependencies (30 min)

#### 1.1 Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 1.2 Install NVIDIA Drivers + CUDA 12.8
**CRITICAL:** OlmOCR requires CUDA 12.8 specifically for GPU acceleration.

```bash
# Check if GPU is detected
lspci | grep -i nvidia

# Install NVIDIA drivers (if not pre-installed)
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Reboot
sudo reboot

# Verify after reboot
nvidia-smi

# Verify VRAM (OlmOCR requires minimum 15GB, L4 has 24GB)
nvidia-smi --query-gpu=memory.total --format=csv,noheader
```

**Note:** OlmOCR uses CUDA 12.8 via PyTorch wheel. This will be installed in Phase 3.

#### 1.3 Install Docker + Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

#### 1.4 Install System Utilities
```bash
sudo apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev
```

#### 1.5 Install OlmOCR System Dependencies
**CRITICAL:** OlmOCR requires PDF rendering and font packages:
```bash
sudo apt-get install -y \
    poppler-utils \
    ttf-mscorefonts-installer \
    fonts-crosextra-caladea \
    fonts-crosextra-carlito \
    gsfonts \
    lcdf-typetools

# Accept the EULA for MS fonts when prompted
```

**Reference:** [OlmOCR GitHub](https://github.com/allenai/olmocr)

---

### Phase 2: GCS Setup (15 min)

#### 2.1 Install GCS FUSE
```bash
# Add Google Cloud SDK repo
export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
echo "deb https://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Install gcsfuse
sudo apt-get update
sudo apt-get install -y gcsfuse
```

#### 2.2 Configure GCS Mounts
```bash
# Create mount points
sudo mkdir -p /mnt/gcs/legal-ocr-pdf-input
sudo mkdir -p /mnt/gcs/legal-ocr-results

# Set ownership
sudo chown -R $USER:$USER /mnt/gcs

# Authenticate (requires service account key)
gcloud auth login
# OR with service account:
# gcloud auth activate-service-account --key-file=/path/to/key.json

# Mount buckets
gcsfuse legal-ocr-pdf-input /mnt/gcs/legal-ocr-pdf-input
gcsfuse legal-ocr-results /mnt/gcs/legal-ocr-results

# Verify mounts
df -h | grep gcs
```

#### 2.3 Auto-mount on Boot (Optional)
```bash
# Add to /etc/fstab
echo "legal-ocr-pdf-input /mnt/gcs/legal-ocr-pdf-input gcsfuse rw,user,_netdev 0 0" | sudo tee -a /etc/fstab
echo "legal-ocr-results /mnt/gcs/legal-ocr-results gcsfuse rw,user,_netdev 0 0" | sudo tee -a /etc/fstab
```

---

### Phase 3: Python Environment (45 min)

#### 3.1 Install Miniconda
```bash
# Download Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Install
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda

# Initialize
~/miniconda/bin/conda init bash
source ~/.bashrc
```

#### 3.2 Create Environment from File
```bash
# Clone repository first
cd ~
git clone <your-repo-url> pdf-rag
cd pdf-rag

# Option A: Create from full environment file (exact versions)
conda env create -f olmocr-optimized-env.yml

# Option B: Create fresh environment (if Option A fails)
conda create -n olmocr-optimized python=3.11 -y
conda activate olmocr-optimized
pip install -r requirements.txt  # See updated requirements.txt below
```

#### 3.3 Install OlmOCR with GPU Support
**CRITICAL:** OlmOCR must be installed with GPU support and CUDA 12.8.

```bash
conda activate olmocr-optimized

# Install OlmOCR with GPU support (CUDA 12.8)
# This will install PyTorch 2.8.0+cu128 (latest stable)
pip install olmocr[gpu] --extra-index-url https://download.pytorch.org/whl/cu128

# Verify OlmOCR installation
python -c "import olmocr; import torch; print(f'✅ PyTorch: {torch.__version__}'); print('✅ OlmOCR installed successfully')"
```

**Important PyTorch Version Notes:**
- **Recommended:** PyTorch **2.7+** with CUDA 12.8 (OlmOCR is flexible on exact version)
- **Tested working version:** PyTorch **2.8.0+cu128** (current stable)
- The `--extra-index-url` pulls the latest CUDA 12.8 PyTorch wheel automatically
- **DO NOT install FlashInfer** - it downgrades PyTorch to 2.4.x and breaks the setup
- If you need to pin PyTorch version (not recommended unless needed):
  ```bash
  pip install 'torch>=2.7,<3.0' --extra-index-url https://download.pytorch.org/whl/cu128
  pip install olmocr[gpu] --extra-index-url https://download.pytorch.org/whl/cu128
  ```

**Installation Details:**
- Requires ~3GB download
- Installs PyTorch with CUDA 12.8 support automatically
- FlashInfer optimization deliberately skipped (causes version conflicts)

**Reference:** [OlmOCR Installation Guide](https://github.com/allenai/olmocr?tab=readme-ov-file#installation)

#### 3.4 Install Additional Dependencies
```bash
# Core pipeline dependencies
pip install docling qdrant-client

# Verify critical packages
pip list | grep -E "docling|qdrant|olmocr|sentence-transformers|openai"
```

---

### Phase 4: Qdrant Vector Database (10 min)

#### 4.1 Start Qdrant with Docker Compose
```bash
cd ~/pdf-rag

# Create docker-compose.yml (see below)
# Or use existing if in repo

# Start Qdrant
docker-compose up -d qdrant

# Verify running
curl http://localhost:6333/collections
```

#### 4.2 Docker Compose File
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT_LOG_LEVEL=INFO
    restart: unless-stopped
```

---

### Phase 5: Environment Variables (5 min)

#### 5.1 Set OpenAI API Key
```bash
# Add to ~/.bashrc
echo 'export OPENAI_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $OPENAI_API_KEY
```

#### 5.2 Other Environment Variables
```bash
# If needed for your setup
echo 'export QDRANT_HOST=localhost' >> ~/.bashrc
echo 'export QDRANT_PORT=6333' >> ~/.bashrc
source ~/.bashrc
```

---

### Phase 6: Repository Setup (10 min)

#### 6.1 Clone Repository
```bash
cd ~
git clone <your-repo-url> pdf-rag
cd pdf-rag
```

#### 6.2 Verify Configuration
```bash
# Check config exists
ls -l config/default.yaml

# Verify paths in config match your setup
cat config/default.yaml | grep -E "gcs_mount_base|input_bucket"
```

#### 6.3 Test Installation
```bash
# Activate environment
conda activate olmocr-optimized

# Test critical imports
python -c "import docling; import qdrant_client; import olmocr; print('✅ All imports successful')"

# Verify OlmOCR GPU access
python -c "import torch; print(f'✅ CUDA available: {torch.cuda.is_available()}'); print(f'✅ GPU count: {torch.cuda.device_count()}')"

# Verify VRAM
python -c "import torch; print(f'✅ GPU VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')"

# Test Qdrant connection
python -c "from qdrant_client import QdrantClient; client = QdrantClient('localhost', port=6333); print('✅ Qdrant connected')"
```

---

## 🧪 Verification Steps

### Test 1: Process Single PDF
```bash
conda activate olmocr-optimized
cd ~/pdf-rag

# Process one PDF to verify pipeline works
python scripts/process_documents.py <path-to-test-pdf>
```

### Test 2: Qdrant Connection
```bash
python scripts/load_to_qdrant.py
```

### Test 3: Query System
```bash
python scripts/query_cli.py
```

---

## 📦 Updated requirements.txt

```
# Core pipeline
docling>=1.0.0
qdrant-client>=1.7.0
olmocr
sentence-transformers>=2.2.0
openai>=1.0.0

# Document processing
beautifulsoup4
pdf2image
opencv-python-headless
PyMuPDF
python-docx>=1.0.0
openpyxl>=3.1.0

# ML/AI
torch
transformers

# Utilities
filelock>=3.13.0
psutil>=5.9.0
PyYAML>=6.0
pandas>=2.0.0

# Deprecated (for backward compatibility)
haystack-ai  # Used in earlier phases, may remove
```

---

## 🚨 Common Issues & Solutions

### Issue: PyTorch Version Conflict (CRITICAL)
**Symptom:** OlmOCR fails or performance degrades after installing additional packages

```bash
# Check current PyTorch version
python -c "import torch; print(torch.__version__)"

# Should show: 2.8.0+cu128
# If showing 2.4.x or 2.7.x, you have a downgrade issue

# Fix: Reinstall correct PyTorch
pip uninstall torch torchvision torchaudio -y
pip install torch --extra-index-url https://download.pytorch.org/whl/cu128

# Verify
python -c "import torch; print(f'✅ PyTorch: {torch.__version__}')"
```

**Prevention:**
- **NEVER install FlashInfer** (downgrades PyTorch to 2.4.x)
- Always use `--extra-index-url https://download.pytorch.org/whl/cu128` when installing PyTorch-dependent packages

### Issue: CUDA Out of Memory
```bash
# Reduce GPU memory in config/default.yaml
processors:
  olmocr:
    gpu_memory_utilization: 0.6  # Lower from 0.8
```

### Issue: GCS Mount Fails
```bash
# Check auth
gcloud auth list

# Remount with debug
gcsfuse --debug_fuse legal-ocr-results /mnt/gcs/legal-ocr-results
```

### Issue: Qdrant Won't Start
```bash
# Check port not in use
sudo lsof -i :6333

# Restart with logs
docker-compose up qdrant
```

### Issue: Import Errors
```bash
# Reinstall in correct order
pip uninstall -y docling qdrant-client
pip install docling qdrant-client
```

---

## ⏱️ Time Estimates

| Phase | Task | Time |
|-------|------|------|
| 1 | System dependencies | 30 min |
| 2 | GCS setup | 15 min |
| 3 | Python environment | 45 min |
| 4 | Qdrant setup | 10 min |
| 5 | Environment variables | 5 min |
| 6 | Repository setup | 10 min |
| **Total** | **Complete rebuild** | **~2 hours** |

---

## 📋 Quick Recovery Checklist

- [ ] VM created with 15GB+ VRAM GPU (L4 24GB recommended)
- [ ] 30GB+ disk space available
- [ ] NVIDIA drivers installed (`nvidia-smi` works)
- [ ] VRAM verified (15GB+ required)
- [ ] Docker + Docker Compose installed
- [ ] **poppler-utils** and font packages installed
- [ ] GCS buckets mounted at `/mnt/gcs/*`
- [ ] Miniconda installed (Python 3.11)
- [ ] Conda environment created (`olmocr-optimized`)
- [ ] **OlmOCR with GPU support** installed (CUDA 12.8)
- [ ] **docling** and **qdrant-client** installed
- [ ] PyTorch CUDA verified (`torch.cuda.is_available() == True`)
- [ ] Qdrant running (`curl localhost:6333/collections`)
- [ ] OPENAI_API_KEY set
- [ ] Repository cloned
- [ ] Test scanned PDF processed successfully (OlmOCR)

---

## 🔗 Related Documentation

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development standards
- [README.md](../../readme.md) - Project overview
- [Infrastructure Setup](SETUP_INFRASTRUCTURE.md) - Original Qdrant setup
- [OlmOCR GitHub](https://github.com/allenai/olmocr) - Official OlmOCR documentation

---

**Last Tested:** October 31, 2025
**Platform:** Ubuntu 22.04 LTS with NVIDIA L4 GPU (24GB VRAM)
