#!/bin/bash
set -e

echo "🔧 Cleaning existing environment..."
pip uninstall -y torch torchvision torchaudio vllm xformers flashinfer || true

echo "📦 Installing PyTorch stack (CUDA 12.8)"
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128

echo "⚙️ Installing compatible vLLM + xformers (no deps to avoid overwriting Torch)"
pip install vllm==0.4.2 --no-deps
pip install xformers==0.0.28.post1 --no-deps

echo "⚡ Optional accelerator (FlashInfer)"
pip install flashinfer==0.2.5 --no-deps || true

echo "🧠 Verifying versions..."
python - <<'EOF'
import torch, sys
print(f"Torch version: {torch.__version__}")
try:
    import vllm; print(f"vLLM version: {vllm.__version__}")
except Exception as e: print(f"vLLM import failed: {e}")
try:
    import olmocr; print(f"OlmOCR version: {olmocr.__version__}")
except Exception as e: print(f"OlmOCR import failed: {e}")
print("\nCUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA device:", torch.cuda.get_device_name(0))
EOF

echo "✅ Environment rebuild complete. Ready to re-run the pipeline."
