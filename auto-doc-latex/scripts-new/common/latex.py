"""LaTeX formatting helpers for ITU document generation.

Provides functions to escape text for LaTeX, generate hyperlinks,
and format table rows matching the existing template structure.
"""

import os

URL = "https://www.itu.int"

# Characters that need escaping in LaTeX text
_LATEX_SPECIAL = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}


def escape_latex(text):
    """Escape special LaTeX characters in plain text.

    Does NOT escape backslash (to allow embedded LaTeX commands when needed).
    """
    if not text:
        return ""
    result = []
    for ch in str(text):
        result.append(_LATEX_SPECIAL.get(ch, ch))
    return ''.join(result)


def make_href(url, text):
    """Generate a LaTeX \\href{url}{text} hyperlink.

    Escapes special LaTeX characters in URLs so they work correctly
    inside \\newcommand definitions (where %, &, # are interpreted
    before \\href can process them).
    """
    safe_url = url.replace('%', '\\%').replace('&', '\\&').replace('#', '\\#')
    return f"\\href{{{safe_url}}}{{{escape_latex(text)}}}"


def td_href(table_row, prefix="TD", suffix=""):
    """Generate a hyperlink for a temporary document reference.

    Args:
        table_row: TableRow object with number.link and number.value
        prefix: 'TD', 'C', etc.
        suffix: Optional suffix like '/1' for WP number

    Returns:
        LaTeX href string, e.g. \\href{url}{TD123R1/1}
    """
    display = f"{prefix}{table_row.number.value}{table_row.lastRev}"
    if suffix:
        display += suffix
    return make_href(URL + table_row.number.link, display)


def write_result(output_dir, filename, content):
    """Write a LaTeX snippet to the results directory.

    Args:
        output_dir: Path to the results/ directory
        filename: Name of the .tex file to write
        content: LaTeX content string
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Generated {filepath}")


def table_row_str(cells):
    """Format a list of cell values as a LaTeX longtable row.

    Returns: 'cell1 & cell2 & ... \\\\\n\\hline\n'
    """
    return " & ".join(str(c) for c in cells) + " \\\\\n\\hline\n"
