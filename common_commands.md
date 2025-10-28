Common commands

gcloud compute ssh olmocr-l4 --zone=us-central1-b

conda activate olmocr-optimized


python olmocr_pipeline/process_pdf.py pdf_input/"2023004079 ASSN. Legacy Reserves Operating LP to Silver Hill Haynesville E&P LLC Shelby County TX.pdf" --summary --qa true --workers 6


python olmocr_pipeline/process_pdf.py pdf_input/"871-828_Assn_Marathon Oil to Marathon Oil (East TX).pdf" --summary --qa --workers 6


python olmocr_pipeline/process_pdf.py pdf_input/"simple.pdf" --summary --qa --workers 6




# mac local sync
gsutil -m rsync -r gs://legal-ocr-results ~/pdf-rag/legal-ocr-results
