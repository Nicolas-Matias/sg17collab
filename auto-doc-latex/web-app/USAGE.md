# ITU-T Report Generator - User Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Activate your virtual environment (from project root)
cd ../../..  # Go to sg17collab/
venv\Scripts\activate  # Windows

# Install dependencies
cd auto-doc-latex/web-app
pip install Flask Werkzeug beautifulsoup4 lxml python-dateutil
```

**Note:** `pycurl` may fail on Windows. It's only needed for the backend scripts (scraping ITU website), not for the web interface itself.

### 2. Run the Application

```bash
cd auto-doc-latex/web-app
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

---

## 📝 Using the Interface

### Working Party Report

1. Select **"Working Party Report"**
2. Fill in:
   - Study Group (default: 17)
   - Working Party number
   - Meeting place (e.g., Geneva)
   - Start and end dates
   - Number of sessions
   - Meeting days (comma-separated, format: YYYY/MM/DD)
3. Click **"Generate Report"**
4. Wait 2-5 minutes (fetches data from ITU website)
5. Click **"Download LaTeX Files (ZIP)"**

### Question Report

1. Select **"Question Report"**
2. Fill in:
   - Study Group (default: 17)
   - Question number
   - Meeting place
   - Start and end dates
3. Click **"Generate Report"**
4. Wait 2-5 minutes
5. Download the ZIP file

---

## 📦 What You Get

The downloaded ZIP file contains a complete LaTeX project:

```
wp_doc_template/  (or question_doc_template/)
├── main.tex                  # Main document
├── chapters/
│   ├── *.tex                 # Chapter files
│   └── results/              # Auto-generated content
│       ├── 00-variables.tex
│       ├── 01-introduction-content.tex
│       ├── 02-executive-summary-content.tex
│       └── ...
├── styles/                   # LaTeX style files
└── images/                   # Images
```

---

## 📤 Next Steps: Compile on Overleaf

1. Go to [Overleaf.com](https://www.overleaf.com)
2. Click **New Project** → **Upload Project**
3. Upload the downloaded ZIP file
4. Overleaf will automatically compile
5. Click **Download PDF**

---

## ✏️ Manual Sections

Some sections require manual input. Look for:

- `\textit{For manual entry.}` - Fill these sections manually
- `\textit{TODO: ...}` - Placeholders for observations
- `\tdNumber` - TD number (assigned by ITU secretariat)

Typical manual sections:
- Executive summary details
- Observations on liaison statements
- Deleted work items justification

---

## ⚙️ Configuration

### Timeout Settings

Edit `config.py` to adjust:

```python
GENERATION_TIMEOUT = 300        # 5 minutes (in seconds)
TEMP_FILE_MAX_AGE = 1 hour     # Auto-cleanup age
MAX_CONTENT_LENGTH = 16 MB     # Max file upload size
```

### Debug Mode

To disable debug mode (production):

```python
# In app.py
app.run(
    host='127.0.0.1',
    port=5000,
    debug=False  # Change to False
)
```

---

## 🐛 Troubleshooting

### "Download not found or expired"
- Files are auto-deleted after 1 hour
- Generate the report again

### "Network error"
- Check internet connection
- ITU website must be accessible
- Try again in a few minutes

### "Validation error"
- Check that start date < end date
- All required fields must be filled
- Dates must be in YYYY/MM/DD format

### Flask won't start
- Check that port 5000 is not in use
- Kill existing Python processes: `taskkill /F /IM python.exe`
- Reinstall dependencies: `pip install -r requirements.txt`

---

## 🔒 Security Notes

- The app runs on `localhost` only (127.0.0.1)
- Not exposed to the internet
- Session-only (no data persistence)
- Files auto-delete after 1 hour

---

## 📊 File Structure

```
web-app/
├── app.py                    # Flask application
├── config.py                 # Configuration
├── requirements.txt          # Python dependencies
├── utils/                    # Backend modules
│   ├── file_handler.py       # File operations
│   ├── report_generator.py   # Report generation
│   └── validators.py         # Input validation
├── templates/                # HTML templates
│   └── index.html            # Main form
├── static/                   # Frontend assets
│   ├── css/style.css         # Styles
│   └── js/app.js             # JavaScript logic
└── temp/                     # Generated files (auto-cleanup)
```

---

## 💡 Tips

- **Dates:** Use YYYY/MM/DD format (e.g., 2025/12/03)
- **Meeting Days:** Comma-separated (e.g., 2025/12/10, 2025/12/11)
- **Patience:** Report generation takes 2-5 minutes
- **Overleaf:** Best for PDF compilation (no local LaTeX needed)
- **Manual Review:** Always review generated content before submission

---

## 📞 Support

For issues with:
- **Web interface:** Check this guide
- **Generated LaTeX:** See main `README.md` in `auto-doc-latex/`
- **ITU scripts:** Check `scripts-new/` documentation
