from olmocr import OlmOCR
from pathlib import Path

# Input and output paths
pdf_path = Path("app/samples/2023004079 ASSN. Legacy Reserves Operating LP to Silver Hill Haynesville E&P LLC Shelby County TX.pdf")
output_path = Path("olmocr_pipeline/data/processed_html/legacy_olmocr.html")

# Initialize model
model = OlmOCR.from_pretrained("allenai/olmOCR-2-7B-1025-FP8", device="cuda")

# Run inference
html_output = model.run(pdf_path, output_format="html")

# Save output
output_path.write_text(html_output, encoding="utf-8")
print(f"✅ Saved HTML to {output_path}")
