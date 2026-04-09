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
itu-template/
├── scripts-new/                    # Report generation scripts
│   ├── generate_wp_report.py       # Working Party report generator
│   ├── generate_question_report.py # Question report generator
│   └── common/                     # Shared modules (ITU API, utilities)
├── wp_doc_template/                # WP report LaTeX template
│   ├── main.tex                    # Main document entry point
│   ├── chapters/                   # Chapter .tex files
│   │   └── results/                # Auto-generated LaTeX snippets
│   └── styles/                     # LaTeX style files
├── question_doc_template/          # Question report LaTeX template
│   ├── main.tex
│   ├── chapters/
│   │   └── results/
│   └── styles/
└── examples/                       # Example JSON config files
    ├── WorkingParty/WPReport.json
    └── Question/questionReport.json
```

## Step-by-step usage

### Step 1: Create a JSON configuration file

Create a JSON file describing the meeting. Use the examples as a starting point.

**For a Working Party report** (`examples/WorkingParty/WPReport.json`):

```json
{
  "documentType": "report",
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

| Field | Description |
|-------|-------------|
| `group` | Study Group number (e.g., 17) |
| `workingParty` | Working Party number (e.g., 1) |
| `place` | Meeting location |
| `start` / `end` | Meeting dates in `YYYY/MM/DD` format |
| `sessions` | Number of sessions |
| `meetingDays` | List of meeting days in `YYYY/MM/DD` format |
| `workProgramme` | Path to the work programme CSV file (relative to the JSON file) |

**For a Question report** (`examples/Question/questionReport.json`):

```json
{
  "documentType": "report",
  "group": 17,
  "question": 10,
  "place": "Geneva",
  "start": "2025/04/08",
  "end": "2025/04/17"
}
```

| Field | Description |
|-------|-------------|
| `group` | Study Group number |
| `question` | Question number (e.g., 10) |
| `place` | Meeting location |
| `start` / `end` | Meeting dates in `YYYY/MM/DD` format |

### Step 2: Run the generation script

From the `scripts-new/` directory, run the appropriate script:

```bash
cd scripts-new

# For a Working Party report
python generate_wp_report.py ../examples/WorkingParty/WPReport.json

# For a Question report
python generate_question_report.py ../examples/Question/questionReport.json
```

The script will:
1. Read the JSON configuration
2. Fetch meeting data from the ITU website (documents, leadership, work programme)
3. Generate LaTeX snippet files in the template's `chapters/results/` directory

### Step 3: Fill in manual sections

Some sections require manual input. Open the generated `.tex` files in `chapters/results/` and look for:

- `\textit{For manual entry.}` -- sections that need to be written by hand (e.g., executive summary, deleted work items)
- `\textit{TODO: write the observation here}` -- placeholders after incoming liaison statements that need observations

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
