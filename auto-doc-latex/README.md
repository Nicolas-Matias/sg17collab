# ITU Report Generator

Automated generation of ITU-T meeting reports (Working Party reports and Question reports) from JSON configuration files. The system fetches data from the ITU website, generates LaTeX snippets, and produces ready-to-compile documents.

## Features

- Automatic data fetching from ITU website (documents, leadership, work programme)
- LaTeX report generation for Working Party and Question reports
- Web interface for easy report generation
- Text wrapping in tables with automatic word breaking for long identifiers
- Downloadable ZIP files with descriptive naming (`report-SG17-WP1-DD-MM-YYYY.zip`)

## Prerequisites

- **Python 3.8+**
- **Python packages**: install with:
  ```bash
  pip install bs4 pycurl flask
  ```
- **LaTeX distribution** (for PDF compilation): MiKTeX (Windows) or TeX Live (Linux/macOS)

## Project Structure

```
auto-doc-latex/
├── scripts-new/                    # Report generation scripts
│   ├── generate_wp_report.py       # Working Party report generator
│   ├── generate_question_report.py # Question report generator
│   ├── WPReport.json               # Example WP config
│   ├── questionReport.json         # Example Question config
│   └── common/                     # Shared modules
│       ├── config.py               # Configuration loading
│       ├── itu_api.py              # ITU website data fetching
│       ├── latex.py                # LaTeX formatting helpers
│       ├── models.py               # Data models
│       └── utils.py                # Utility functions
│
├── web-app/                        # Flask web application
│   ├── app.py                      # Main Flask application
│   ├── config.py                   # Web app configuration
│   ├── requirements.txt            # Python dependencies
│   ├── templates/                  # HTML templates
│   ├── static/                     # CSS and JavaScript
│   └── utils/                      # Web app utilities
│
├── wp_doc_template/                # WP report LaTeX template
│   ├── main.tex                    # Main document entry point
│   ├── chapters/                   # Chapter .tex files
│   │   └── variables/              # Auto-generated LaTeX snippets
│   └── styles/                     # LaTeX style files
│
└── question_doc_template/          # Question report LaTeX template
    ├── main.tex
    ├── chapters/
    │   ├── 00-frontcover.tex
    │   ├── 01-introduction.tex
    │   ├── 02-executive-summary.tex
    │   ├── 03-report-of-interim.tex
    │   ├── 04-intellectual-property.tex
    │   ├── 05-discussions.tex
    │   ├── 06-draft-recommendations.tex
    │   ├── 07-non-normative-text.tex
    │   ├── 08-outgoing-liaison-statements.tex
    │   ├── 09-work-programme.tex
    │   ├── 10-candidate-work-items.tex
    │   ├── 11-planned-interim-meetings.tex
    │   ├── 12-scheduled-meetings.tex
    │   ├── annex-a.tex, annex-b.tex, annex-c.tex
    │   └── variables/              # Auto-generated LaTeX snippets
    └── styles/
```

## Usage

### Option 1: Web Interface (Recommended)

1. Start the web application:
   ```bash
   cd web-app
   pip install -r requirements.txt
   python app.py
   ```

2. Open your browser to `http://localhost:5000`

3. Fill in the form:
   - Select report type (Working Party or Question)
   - Enter Study Group number, Working Party/Question number
   - Set meeting dates and location

4. Click "Generate Report" to download a ZIP file containing the LaTeX template with generated content

### Option 2: Command Line

#### Step 1: Create a JSON configuration file

**For a Working Party report**:
```json
{
  "group": 17,
  "workingParty": 1,
  "place": "Geneva",
  "start": "2025/12/03",
  "end": "2025/12/11",
  "next_meeting": "2026/07/01"
}
```

**For a Question report**:
```json
{
  "group": 17,
  "question": 10,
  "place": "Geneva",
  "start": "2025/12/03",
  "end": "2025/12/09",
  "next_meeting": "2026/07/01"
}
```

#### Step 2: Run the generation script

```bash
cd scripts-new

# For a Working Party report
python generate_wp_report.py WPReport.json

# For a Question report
python generate_question_report.py questionReport.json
```

The script will:
1. Read the JSON configuration
2. Fetch meeting data from the ITU website
3. Generate LaTeX snippet files in the template's `chapters/variables/` directory

### Step 3: Fill in manual sections

Some sections require manual input. Look for:
- `\textit{For manual entry.}` - sections to write by hand
- `\textit{TODO: write the observation here}` - placeholders for observations
- `(manual entry)` - editor fields to complete

### Step 4: Compile the PDF

**Using Overleaf: (Recommended)**
1. Compress the template directory into a `.zip` file
2. Upload to [Overleaf](https://www.overleaf.com) → New Project → Upload Project
3. Set `main.tex` as the main document
4. Click Recompile → Download PDF

**Using local LaTeX:**
```bash
cd wp_doc_template  # or question_doc_template
latexmk -pdf main.tex
```

## Configuration Reference

### Working Party Report

| Field | Required | Description |
|-------|----------|-------------|
| `group` | Yes | Study Group number (e.g., 17) |
| `workingParty` | Yes | Working Party number (e.g., 1) |
| `start` | Yes | Meeting start date (`YYYY/MM/DD`) |
| `place` | yes | Meeting location |
| `end` | yes | Meeting end date (`YYYY/MM/DD`) |
| `next_meeting` | No | Next meeting date (for filtering candidate work items) |

### Question Report

| Field | Required | Description |
|-------|----------|-------------|
| `group` | Yes | Study Group number |
| `question` | Yes | Question number (e.g., 10) |
| `start` | Yes | Meeting start date (`YYYY/MM/DD`) |
| `place` | yes | Meeting location |
| `end` | yes | Meeting end date (`YYYY/MM/DD`) |
| `next_meeting` | no | Next meeting date (for filtering candidate work items) |

## Template Variables

Each chapter `.tex` file includes variables from the `chapters/variables/` directory. Comments in the template files indicate:
- Variable source: `% Variable: \variableName -> chapters/variables/filename.tex`
- Table row format: `% Row template: Col1 & Col2 & Col3 \\ \hline`

## Troubleshooting

- **Network errors**: Ensure internet access and ITU website (`www.itu.int`) is reachable
- **Missing `pycurl`**: On Windows, install a precompiled wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl
- **LaTeX errors**: Run `latexmk -pdf -interaction=nonstopmode main.tex` for detailed error messages
- **Long text overflow**: Work item names use `\seqsplit{}` to break anywhere in columns
