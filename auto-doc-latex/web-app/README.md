# ITU-T Report Generator - Web Interface

Web application to generate ITU-T Working Party and Question reports from a user-friendly interface.

## Overview

This web app provides a frontend for the automated report generation system. Users fill a form instead of manually editing JSON configuration files.

## Installation

1. **Activate the virtual environment** (from project root):
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   cd auto-doc-latex/web-app
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open in browser**:
   ```
   http://localhost:5000
   ```

## Usage

1. Select report type (Working Party or Question)
2. Fill in the form fields
3. Click "Generate Report"
4. Download the ZIP file
5. Upload to Overleaf and compile

## Project Structure

```
web-app/
├── app.py                    # Flask application entry point
├── config.py                 # Configuration (paths, timeouts, etc.)
├── requirements.txt          # Python dependencies
│
├── utils/                    # Backend logic
│   ├── file_handler.py       # File operations (ZIP, temp directories)
│   ├── report_generator.py   # Wrapper for existing scripts
│   └── validators.py         # Input validation
│
├── templates/                # HTML templates (Jinja2)
│   ├── base.html             # Base template
│   └── index.html            # Main form page
│
├── static/                   # Static assets
│   ├── css/style.css         # Custom styles
│   └── js/app.js             # Frontend logic
│
└── temp/                     # Generated files (auto-cleaned)
```

## Configuration Values

The following values in `config.py` are **arbitrary choices** and can be adjusted based on real-world usage:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `MAX_CONTENT_LENGTH` | 16 MB | Arbitrary limit for CSV work programme uploads. Adjust if larger files are needed. |
| `TEMP_FILE_MAX_AGE` | 1 hour | Arbitrary cleanup interval. Files older than 1 hour are deleted automatically. |
| `GENERATION_TIMEOUT` | 5 minutes | Arbitrary timeout for report generation. Adjust if generation takes longer. |

**Note**: These values should be monitored in production and adjusted based on:
- Actual CSV file sizes encountered
- Typical report generation times
- Available disk space for temporary files

## Output

The application generates a ZIP file containing:

```
wp_doc_template/              # or question_doc_template/
├── main.tex                  # Main LaTeX document
├── chapters/
│   └── results/              # Auto-generated content from ITU data
├── styles/                   # LaTeX styles
└── images/                   # Images
```

This ZIP can be directly uploaded to [Overleaf](https://www.overleaf.com) for PDF compilation.

## Development

- **Debug mode**: Enabled by default (see `config.py`)
- **Auto-reload**: Templates reload automatically on changes
- **Logging**: Check console output for errors

## Dependencies

- **Flask 3.0.0**: Web framework
- **beautifulsoup4 4.12.2**: HTML parsing (ITU website scraping)
- **pycurl 7.45.2**: HTTP requests
- **python-dateutil 2.8.2**: Date manipulation

See `requirements.txt` for complete list.

## Notes

- Temporary files in `temp/` are automatically cleaned after 1 hour
- The app uses the existing `scripts-new/` Python scripts under the hood
- Generated reports require manual sections to be filled (see main `README.md`)
