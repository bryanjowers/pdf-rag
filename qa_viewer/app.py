"""
QA Viewer - Flask web application for QA'ing processed PDF documents

Provides a side-by-side view of original PDFs and extracted Markdown
to facilitate quality assurance of the PDF-RAG pipeline outputs.
"""

from flask import Flask, jsonify, render_template, send_file, abort
from pathlib import Path
import pandas as pd
import markdown
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCS mount paths
MANIFEST_DIR = Path("/mnt/gcs/legal-ocr-results/manifests/")
INPUT_DIR = Path("/mnt/gcs/legal-ocr-pdf-input/")
MARKDOWN_DIR = Path("/mnt/gcs/legal-ocr-results/rag_staging/markdown/")

# Global manifest data
manifest_data = None
file_lookup = {}  # hash -> file info mapping


def load_latest_manifest():
    """Load the most recent manifest CSV file."""
    global manifest_data, file_lookup

    try:
        # Find all manifest files and sort by timestamp (newest first)
        manifest_files = sorted(
            MANIFEST_DIR.glob("manifest_*.csv"),
            reverse=True
        )

        if not manifest_files:
            logger.error(f"No manifest files found in {MANIFEST_DIR}")
            return None

        latest_manifest = manifest_files[0]
        logger.info(f"Loading manifest: {latest_manifest.name}")

        # Load manifest CSV
        df = pd.read_csv(latest_manifest)

        # Fill NaN values for better JSON serialization
        df = df.fillna("")

        # Create file lookup by filename (since hash_sha256 is empty)
        # We'll use filename as the key for now
        file_lookup = {}
        for idx, row in df.iterrows():
            file_name = row.get('file_name', '')
            if file_name:
                file_lookup[file_name] = {
                    'file_path': row.get('file_path', ''),
                    'file_name': file_name,
                    'file_type': row.get('file_type', ''),
                    'processor': row.get('processor', ''),
                    'status': row.get('status', ''),
                    'page_count': row.get('page_count', 0),
                    'chunks_created': row.get('chunks_created', 0),
                    'processing_duration_ms': row.get('processing_duration_ms', 0),
                    'char_count': row.get('char_count', 0),
                    'estimated_tokens': row.get('estimated_tokens', 0),
                    'processed_at': row.get('processed_at', ''),
                    'warnings': row.get('warnings', ''),
                    'error': row.get('error', ''),
                    'confidence_score': row.get('confidence_score', 0.0)
                }

        logger.info(f"Loaded {len(df)} records from manifest")
        manifest_data = df

        return df

    except Exception as e:
        logger.error(f"Error loading manifest: {e}")
        return None


@app.route('/')
def index():
    """Serve the main viewer page."""
    return render_template('viewer.html')


@app.route('/api/files')
def get_files():
    """Get list of all files from manifest."""
    if manifest_data is None:
        load_latest_manifest()

    if manifest_data is None:
        return jsonify({'error': 'Failed to load manifest data'}), 500

    # Convert DataFrame to list of dicts for JSON response
    files = manifest_data.to_dict('records')

    return jsonify({
        'files': files,
        'total': len(files)
    })


@app.route('/api/file/<path:file_name>/meta')
def get_file_meta(file_name):
    """Get detailed metadata for a specific file."""
    if file_name not in file_lookup:
        return jsonify({'error': 'File not found'}), 404

    return jsonify(file_lookup[file_name])


@app.route('/pdf/<path:file_name>')
def serve_pdf(file_name):
    """Serve original PDF file from input directory."""
    try:
        # Look up file path from manifest
        if file_name not in file_lookup:
            abort(404, description=f"File not found in manifest: {file_name}")

        file_path = Path(file_lookup[file_name]['file_path'])

        # Verify file exists
        if not file_path.exists():
            abort(404, description=f"PDF file not found on disk: {file_path}")

        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False
        )

    except Exception as e:
        logger.error(f"Error serving PDF {file_name}: {e}")
        abort(500, description=f"Error loading PDF: {str(e)}")


@app.route('/md/<path:file_name>')
def serve_markdown(file_name):
    """Serve rendered Markdown as HTML."""
    try:
        # Convert PDF filename to markdown filename
        # Example: "110-532_WD_Annie.pdf" -> "110-532_WD_Annie.md"
        md_filename = file_name.rsplit('.', 1)[0] + '.md'
        md_path = MARKDOWN_DIR / md_filename

        # Verify file exists
        if not md_path.exists():
            # Try without extension change (in case it's already .md)
            md_path = MARKDOWN_DIR / file_name
            if not md_path.exists():
                abort(404, description=f"Markdown file not found: {md_filename}")

        # Read and convert markdown to HTML
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert to HTML with extensions for tables, code blocks, etc.
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

        # Wrap in basic HTML structure with styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                    max-width: 100%;
                    margin: 0;
                    font-size: 14px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                }}
                h1 {{ font-size: 1.5em; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }}
                h2 {{ font-size: 1.25em; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3em; }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                    font-size: 13px;
                }}
                th, td {{
                    border: 1px solid #d1d5db;
                    padding: 8px 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f3f4f6;
                    font-weight: 600;
                }}
                tr:nth-child(even) {{
                    background-color: #f9fafb;
                }}
                code {{
                    background-color: #f3f4f6;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                }}
                pre {{
                    background-color: #f3f4f6;
                    padding: 12px;
                    border-radius: 6px;
                    overflow-x: auto;
                }}
                pre code {{
                    background-color: transparent;
                    padding: 0;
                }}
                blockquote {{
                    border-left: 4px solid #e5e7eb;
                    padding-left: 16px;
                    color: #6b7280;
                    margin: 16px 0;
                }}
                a {{
                    color: #3b82f6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        return full_html

    except Exception as e:
        logger.error(f"Error serving markdown {file_name}: {e}")
        abort(500, description=f"Error loading markdown: {str(e)}")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': str(error.description)
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error',
        'message': str(error.description)
    }), 500


if __name__ == '__main__':
    # Load manifest on startup
    logger.info("Starting QA Viewer...")
    load_latest_manifest()

    # Run Flask app
    app.run(
        host='0.0.0.0',  # Listen on all interfaces for SSH tunnel
        port=5000,
        debug=True
    )
