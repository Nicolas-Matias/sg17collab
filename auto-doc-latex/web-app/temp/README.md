# Temporary Files Directory

This directory stores temporarily generated reports during the web application workflow.

## Content

- **Config JSON files**: Temporary configuration files created from form submissions
- **Generated LaTeX templates**: Populated template directories ready for compilation
- **ZIP archives**: Compressed files ready for download

## Automatic Cleanup

Files in this directory are automatically cleaned up after **1 hour** to prevent disk space issues.

## Structure

Each generation creates a unique timestamped directory:

```
temp/
├── 20251226_143025/
│   ├── config.json
│   ├── wp_doc_template/          # Populated template
│   │   ├── main.tex
│   │   ├── chapters/
│   │   │   └── results/          # Auto-generated content
│   │   └── ...
│   └── wp_report_20251226_143025.zip
└── ...
```

## Note

**Do NOT commit generated files to Git!** This directory is ignored by `.gitignore` (except this README and `.gitkeep`).
