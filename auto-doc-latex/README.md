# ITU Template

Automated generation of ITU-T meeting reports (Working Party reports and Question reports) from JSON configuration files. The scripts fetch data from the ITU website, generate LaTeX snippets, and produce ready-to-compile documents.

## Prerequisites

- **Python 3.8+**
- **Python packages**: install with:
  ```bash
  pip install bs4 pycurl
  ```
- **LaTeX distribution** (for PDF compilation): MiKTeX (Windows) or TeX Live (Linux/macOS)
- **latexmk** (included with most LaTeX distributions)

## Project structure

```
auto-doc-latex/
├── scripts-new/                    # Report generation scripts
│   ├── generate_wp_report.py       # Working Party report generator
│   ├── generate_question_report.py # Question report generator
│   ├── questionReport.json         # Example Question config
│   └── common/                     # Shared modules (ITU API, utilities)
├── wp_doc_template/                # WP report LaTeX template
│   ├── main.tex                    # Main document entry point
│   ├── chapters/                   # Chapter .tex files
│   │   └── variables/              # Auto-generated LaTeX snippets
│   └── styles/                     # LaTeX style files
└── question_doc_template/          # Question report LaTeX template
    ├── main.tex
    ├── chapters/
    │   ├── 00-frontcover.tex       # Front cover
    │   ├── 01-introduction.tex     # Introduction
    │   ├── 02-executive-summary.tex
    │   ├── 03-report-of-interim.tex
    │   ├── 04-intellectual-property.tex
    │   ├── 05-discussions.tex      # Includes 05-01 to 05-05
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

## Step-by-step usage

### Step 1: Create a JSON configuration file

Create a JSON file describing the meeting.

**For a Working Party report**:

```json
{
  "group": 17,
  "workingParty": 1,
  "place": "Geneva",
  "start": "2025/12/03",
  "end": "2025/12/11",
  "sessions": 1,
  "meetingDays": ["2025/12/10"],
  "workProgramme": "WP.csv"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `group` | Yes | Study Group number (e.g., 17) |
| `workingParty` | Yes | Working Party number (e.g., 1) |
| `start` | Yes | Meeting start date in `YYYY/MM/DD` format |
| `place` | No | Meeting location |
| `end` | No | Meeting end date in `YYYY/MM/DD` format |
| `sessions` | No | Number of sessions |
| `meetingDays` | No | List of meeting days in `YYYY/MM/DD` format |
| `workProgramme` | No | Path to work programme CSV file (relative to JSON file) |

**For a Question report** (`scripts-new/questionReport.json`):

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

| Field | Required | Description |
|-------|----------|-------------|
| `group` | Yes | Study Group number |
| `question` | Yes | Question number (e.g., 10) |
| `start` | Yes | Meeting start date in `YYYY/MM/DD` format |
| `place` | No | Meeting location |
| `end` | No | Meeting end date in `YYYY/MM/DD` format |
| `next_meeting` | No | Next meeting date (for filtering candidate work items) |

### Step 2: Run the generation script

From the `scripts-new/` directory, run the appropriate script:

```bash
cd scripts-new

# For a Working Party report
python generate_wp_report.py path/to/config.json

# For a Question report
python generate_question_report.py questionReport.json
```

The script will:
1. Read the JSON configuration
2. Fetch meeting data from the ITU website (documents, leadership, work programme)
3. Generate LaTeX snippet files in the template's `chapters/variables/` directory

### Step 3: Fill in manual sections

Some sections require manual input. Open the generated `.tex` files in `chapters/variables/` and look for:

- `\textit{For manual entry.}` -- sections that need to be written by hand
- `\textit{TODO: write the observation here}` -- placeholders for observations

The following sections typically require manual input:

| Section | What to fill in |
|---------|----------------|
| Executive summary | Summary of key outcomes |
| Other contributions | Review and observations |
| Incoming liaison statements | Observations after each LS entry |
| Deleted work items | Items discontinued at this meeting |
| TD number (`\tdNumber`) | Assigned by the secretariat after submission |

### Step 4: Compile the PDF with Overleaf

1. Go to [Overleaf](https://www.overleaf.com) and log in (or create a free account)
2. Click **New Project** → **Upload Project**
3. Compress the template directory (`wp_doc_template/` or `question_doc_template/`) into a `.zip` file and upload it
4. Once uploaded, Overleaf will automatically compile the document
5. Click **Recompile** if needed, then **Download PDF** to get the final output

**Tips:**
- Ensure `main.tex` is set as the main document (Menu → Main document)
- If compilation fails, check the error log for missing packages (Overleaf usually auto-installs them)
- You can edit the `.tex` files directly in Overleaf before compiling

## Troubleshooting

- **Network errors**: The scripts fetch data from `www.itu.int`. Ensure you have internet access and the ITU website is reachable.
- **Missing `pycurl`**: On Windows, install a precompiled wheel if `pip install pycurl` fails. Check https://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl for compatible wheels.
- **LaTeX compilation errors**: Run `latexmk -pdf -interaction=nonstopmode main.tex` to see detailed error messages. Ensure all required LaTeX packages are installed (MiKTeX installs them automatically on first use).
