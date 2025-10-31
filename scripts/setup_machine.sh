#!/bin/bash
#
# Machine Setup Script for PDF RAG Pipeline
# Supports both GPU (OCR) and CPU (enrichment) machine roles
#
# Usage:
#   ./scripts/setup_machine.sh --role gpu
#   ./scripts/setup_machine.sh --role cpu
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ROLE=""
CONDA_ENV_NAME="pdf-rag"
MINICONDA_VERSION="latest"
PYTHON_VERSION="3.11"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --role)
            ROLE="$2"
            shift 2
            ;;
        --env-name)
            CONDA_ENV_NAME="$2"
            shift 2
            ;;
        --python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --role [gpu|cpu] [OPTIONS]"
            echo ""
            echo "Required:"
            echo "  --role [gpu|cpu]       Machine role (gpu=OCR, cpu=enrichment)"
            echo ""
            echo "Optional:"
            echo "  --env-name NAME        Conda environment name (default: pdf-rag)"
            echo "  --python VERSION       Python version (default: 3.11)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --role gpu"
            echo "  $0 --role cpu --env-name rag-cpu"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate role
if [[ "$ROLE" != "gpu" && "$ROLE" != "cpu" ]]; then
    echo -e "${RED}Error: --role must be either 'gpu' or 'cpu'${NC}"
    echo "Run with --help for usage information"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF RAG Pipeline - Machine Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Role: ${GREEN}$ROLE${NC}"
echo -e "Environment: ${GREEN}$CONDA_ENV_NAME${NC}"
echo -e "Python: ${GREEN}$PYTHON_VERSION${NC}"
echo ""

# Function to print section headers
section() {
    echo ""
    echo -e "${BLUE}==> $1${NC}"
}

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
}

#
# 1. System Update
#
section "Updating system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tmux \
    ca-certificates \
    gnupg \
    lsb-release
success "Base system packages updated"

# Install gcsfuse from Google Cloud repository
section "Installing gcsfuse"
export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s)
echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update -qq
sudo apt-get install -y -qq gcsfuse
success "gcsfuse installed"

#
# 2. Install Miniconda (if not present)
#
section "Installing Miniconda"
if [ -d "$HOME/miniconda" ]; then
    warning "Miniconda already installed at $HOME/miniconda"
else
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    wget -q "$MINICONDA_URL" -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$HOME/miniconda"
    rm /tmp/miniconda.sh
    success "Miniconda installed"
fi

# Initialize conda for bash (with first-run setup)
source "$HOME/miniconda/etc/profile.d/conda.sh"
conda config --set auto_activate_base false
conda init bash --no-user 2>/dev/null || conda init bash
success "Conda initialized for bash"

# Source the updated bashrc to get conda in current shell
source "$HOME/.bashrc" 2>/dev/null || true
eval "$($HOME/miniconda/bin/conda shell.bash hook)"

#
# 3. Create Conda Environment
#
section "Creating conda environment: $CONDA_ENV_NAME"
if conda env list | grep -q "^$CONDA_ENV_NAME "; then
    warning "Environment '$CONDA_ENV_NAME' already exists"
    read -p "Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n "$CONDA_ENV_NAME" -y
        success "Removed existing environment"
    else
        error "Skipping environment creation"
        exit 1
    fi
fi

conda create -n "$CONDA_ENV_NAME" python="$PYTHON_VERSION" -y
success "Created environment: $CONDA_ENV_NAME"

# Activate environment
conda activate "$CONDA_ENV_NAME"
success "Activated environment: $CONDA_ENV_NAME"

#
# 4. Install Common Dependencies
#
section "Installing common dependencies"
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet \
    pyyaml \
    python-dotenv \
    tqdm \
    pandas \
    openpyxl \
    requests

success "Common dependencies installed"

#
# 5. Install Role-Specific Dependencies
#
if [[ "$ROLE" == "gpu" ]]; then
    section "Installing GPU-specific dependencies (OCR workload)"

    # PyTorch with CUDA support
    echo "Installing PyTorch with CUDA..."
    pip install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    success "PyTorch (CUDA 12.1) installed"

    # vLLM for model serving
    echo "Installing vLLM..."
    pip install --quiet vllm
    success "vLLM installed"

    # OlmOCR for OCR
    echo "Installing OlmOCR..."
    pip install --quiet olmocr
    success "OlmOCR installed"

    # PDF processing tools
    pip install --quiet pypdf PyMuPDF pillow
    success "PDF processing tools installed"

    # Google Cloud Storage
    pip install --quiet google-cloud-storage
    success "Google Cloud Storage client installed"

    echo ""
    success "GPU machine setup complete!"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Mount GCS buckets (if not already mounted)"
    echo "  2. Clone your repository: git clone <repo>"
    echo "  3. Run OCR processing:"
    echo "     python scripts/process_documents.py --auto --ingest-only --file-types pdf"

elif [[ "$ROLE" == "cpu" ]]; then
    section "Installing CPU-specific dependencies (enrichment workload)"

    # PyTorch (CPU-only)
    echo "Installing PyTorch (CPU-only)..."
    pip install --quiet torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    success "PyTorch (CPU-only) installed"

    # spaCy for NER
    echo "Installing spaCy..."
    pip install --quiet spacy
    python -m spacy download en_core_web_lg --quiet
    success "spaCy and en_core_web_lg model installed"

    # sentence-transformers for embeddings
    echo "Installing sentence-transformers..."
    pip install --quiet sentence-transformers
    success "sentence-transformers installed"

    # Qdrant for vector storage
    echo "Installing qdrant-client..."
    pip install --quiet qdrant-client
    success "qdrant-client installed"

    # LangChain for RAG (optional)
    echo "Installing LangChain..."
    pip install --quiet langchain langchain-openai langchain-community
    success "LangChain installed"

    # Google Cloud Storage
    pip install --quiet google-cloud-storage
    success "Google Cloud Storage client installed"

    echo ""
    success "CPU machine setup complete!"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Mount GCS buckets (if not already mounted)"
    echo "  2. Clone your repository: git clone <repo>"
    echo "  3. Set environment variables (OPENAI_API_KEY, etc.)"
    echo "  4. Run enrichment processing:"
    echo "     python scripts/process_documents.py --auto --enrich-only"
fi

#
# 6. Validate GCS Mount Access
#
section "Validating GCS mount access"
if mountpoint -q /mnt/gcs 2>/dev/null; then
    success "GCS mount exists at /mnt/gcs"

    # Check if we can list buckets
    if ls /mnt/gcs/ > /dev/null 2>&1; then
        success "GCS mount is accessible"
        echo "  Mounted buckets:"
        ls /mnt/gcs/ | sed 's/^/    - /'
    else
        warning "GCS mount exists but is not accessible"
        echo "  You may need to configure gcsfuse"
    fi
else
    warning "No GCS mount found at /mnt/gcs"
    echo ""
    echo "To mount GCS buckets manually:"
    echo "  sudo mkdir -p /mnt/gcs/your-bucket-name"
    echo "  gcsfuse your-bucket-name /mnt/gcs/your-bucket-name"
fi

#
# 7. Create activation helper
#
section "Creating activation helper"
cat > "$HOME/activate_rag.sh" << EOF
#!/bin/bash
# Quick activation helper for $CONDA_ENV_NAME environment
source ~/miniconda/etc/profile.d/conda.sh
conda activate $CONDA_ENV_NAME
echo "Activated environment: $CONDA_ENV_NAME (role: $ROLE)"
EOF
chmod +x "$HOME/activate_rag.sh"
success "Created activation helper: ~/activate_rag.sh"

#
# 8. Summary
#
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Environment: $CONDA_ENV_NAME"
echo "Role: $ROLE"
echo ""
echo "To activate environment:"
echo "  source ~/activate_rag.sh"
echo "  # OR"
echo "  conda activate $CONDA_ENV_NAME"
echo ""
echo "Configuration file: ~/.condarc"
echo "Environment location: $HOME/miniconda/envs/$CONDA_ENV_NAME"
echo ""

# Add to .bashrc for auto-activation (optional)
if ! grep -q "conda activate $CONDA_ENV_NAME" "$HOME/.bashrc"; then
    echo ""
    read -p "Add conda environment to .bashrc for auto-activation? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "" >> "$HOME/.bashrc"
        echo "# Auto-activate $CONDA_ENV_NAME environment" >> "$HOME/.bashrc"
        echo "source ~/miniconda/etc/profile.d/conda.sh" >> "$HOME/.bashrc"
        echo "conda activate $CONDA_ENV_NAME" >> "$HOME/.bashrc"
        success "Added to .bashrc - will auto-activate on next login"
    fi
fi

echo ""
echo -e "${BLUE}Machine is ready for $ROLE workload!${NC}"
