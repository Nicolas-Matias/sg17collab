"""Utility functions for searching, filtering, and formatting ITU document data."""

import re
from datetime import datetime

from common.models import split_title


def comma_separated_list(elements):
    """Join elements into a comma-separated string."""
    return ", ".join(str(e) for e in elements)


def find_td_by_name(table_rows, name):
    """Find a TableRow whose title contains the given name.

    Returns (questionName, tableRow) or ("", None).
    """
    for row in table_rows:
        if name in row.title:
            question_name = row.questions[0].value if row.questions else ""
            return (question_name, row)
    return ("", None)


def _normalize_number(value):
    """Normalize a document number by stripping spaces and leading zeros."""
    return str(value).strip().lstrip('0') or '0'


def find_td_by_number(table_rows, number):
    """Find a TableRow by its document number.

    Returns (questionName, tableRow) or ("", None).
    """
    normalized = _normalize_number(number)
    for row in table_rows:
        if _normalize_number(row.number.value) == normalized:
            question_name = row.questions[0].value if row.questions else ""
            return (question_name, row)
    return ("", None)


def find_question_name_td_and_a5(table_rows, number):
    """Find a TableRow by number and its associated A.5 justification document.

    Returns (questionName, tableRow, a5TableRow).
    """
    question_name = ""
    td = None
    a5 = None
    title = None

    normalized_number = _normalize_number(number)
    for row in table_rows:
        if _normalize_number(row.number.value) == normalized_number:
            question_name = row.questions[0].value if row.questions else ""
            td = row
            title = row.title
            break

    if title is not None:
        for row in table_rows:
            if title in row.title and "A.5" in row.title:
                a5 = row
                break

    return (question_name, td, a5)


def compare_stripped(string1, string2):
    """Compare two strings ignoring all spaces."""
    return string1.replace(' ', '') == string2.replace(' ', '')


def stripped_starts_with(string1, string2):
    """Check if string2 starts with string1 (original logic preserved)."""
    return string2.startswith(string1)


def is_new_work_item(string):
    """Check if a title indicates a new work item proposal."""
    lower = string.lower()
    return 'new' in lower and 'work' in lower and 'item' in lower


# --- Role extraction helpers ---

def get_rapporteurs(question_details):
    """Get formatted rapporteur names from a Question object."""
    rapporteurs = []
    for role in question_details.roles:
        if role.roleName in ("Rapporteur", "Co-rapporteur"):
            rapporteurs.append(
                f"{role.firstName} {role.lastName} ({role.company}, {role.address})"
            )
    return rapporteurs


def get_associate_rapporteurs(question_details):
    """Get formatted associate rapporteur names from a Question object."""
    return [
        f"{role.firstName} {role.lastName} ({role.company}, {role.address})"
        for role in question_details.roles
        if role.roleName == "Associate rapporteur"
    ]


def get_chairs(working_party_details):
    """Get formatted chair names from a WorkingParty object."""
    return [
        f"{role.firstName} {role.lastName} ({role.company}, {role.address})"
        for role in working_party_details.roles
        if role.roleName in ("Chair", "Co-Chair")
    ]


def get_vice_chairs(working_party_details):
    """Get formatted vice-chair names from a WorkingParty object."""
    return [
        f"{role.firstName} {role.lastName} ({role.company}, {role.address})"
        for role in working_party_details.roles
        if role.roleName == "Vice-chair"
    ]


# --- Document search helpers ---

def get_document_title(table_rows, number):
    """Find the title of a document by its number."""
    normalized = _normalize_number(number)
    for row in table_rows:
        if _normalize_number(row.number.value) == normalized:
            return row.title
    return ""


def get_liaison_destination(table_rows, number):
    """Extract the liaison destination from a document title (text in [to ...])."""
    normalized = _normalize_number(number)
    for row in table_rows:
        if _normalize_number(row.number.value) == normalized:
            title = row.title
            idx1 = title.find('[to')
            if idx1 >= 0:
                idx2 = title.find(']', idx1)
                if idx2 > idx1:
                    return title[idx1 + 1:idx2]
    return ""


def get_meeting_reports(table_rows, question, group):
    """Find all rapporteur group meeting reports for a given question."""
    reports = []
    for row in table_rows:
        stripped = row.title.replace(' ', '')
        if (stripped.startswith(f"ReportofQ{question}/{group}") and
                "RapporteurGroupMeeting" in stripped):
            reports.append(row)
    return reports


# --- Work programme helpers (shared by WP and Question reports) ---

def extract_alt_name(work_item_name):
    """Extract alternate name from 'X.1096 (ex X.bvm)' -> 'X.bvm'."""
    idx1 = work_item_name.find('(ex ')
    if idx1 < 0:
        return None
    idx2 = work_item_name.find(')', idx1)
    if idx2 < 0:
        return None
    return work_item_name[idx1 + 4:idx2].strip()


def auto_detect_from_work_programme(work_item_details, wp_rows,
                                    approval, determination, consent,
                                    non_normative):
    """Auto-detect approval/consent/determination/agreement from work programme status.

    For each work item with a non-'Under study' status, finds the matching WP TD
    and adds its number to the appropriate list.

    Returns a dict mapping TD number -> WorkItem for use in table generation.
    """
    td_to_work_item = {}

    for wi in work_item_details:
        status = (wi.status or '').strip()
        if not status or status.startswith('Under study'):
            continue

        if status.startswith('Approved'):
            target = approval
        elif status.startswith('Determined'):
            target = determination
        elif status.startswith('Consented'):
            target = consent
        elif status.startswith('Agreed'):
            target = non_normative
        else:
            continue

        name = wi.workItem
        _, td = find_td_by_name(wp_rows, name)
        if td is None:
            alt = extract_alt_name(name)
            if alt:
                _, td = find_td_by_name(wp_rows, alt)
        if td is not None:
            td_num = td.number.value.strip()
            if td_num not in target:
                target.append(td_num)
            td_to_work_item[td_num] = wi

    return td_to_work_item


def extract_new_work_item_info(title, wp_rows):
    """Extract work item name and title from a new work item contribution title.

    Returns (work_item_name, text_title).
    """
    # Pattern 1: "X.name [revision]: title" or "X.name, \"title\""
    m = re.search(r'(X\.\S+(?:\s+\S+)*?)\s*[:,]\s*"?(.*?)"?\s*$', title)
    if m:
        name = m.group(1).strip().rstrip(',')
        text = m.group(2).strip().strip('"')
        return name, text

    # Pattern 2: "TR.name [title]"
    m = re.search(r'(TR\.\S+)(?:[\s,]+"?(.*?)"?\s*$)?', title)
    if m:
        name = m.group(1).rstrip(',')
        text = (m.group(2) or "").strip().strip('"')
        return name, text

    # Pattern 3: "XSTR.name [title]"
    m = re.search(r'(XSTR\.\S+)(?:[\s,]+"?(.*?)"?\s*$)?', title)
    if m:
        name = m.group(1).rstrip(',')
        text = (m.group(2) or "").strip().strip('"')
        return name, text

    # Fallback: match against "Output - new work item" WP TD titles
    for row in wp_rows:
        if "new work item" in row.title.lower():
            m2 = re.search(r'new work item\s+(X\.\S+|TR\.\S+|XSTR\.\S+)', row.title, re.IGNORECASE)
            if m2:
                name = m2.group(1).rstrip(':')
                if name.lower() in title.lower() or name.replace('.', '') in title.replace('.', ''):
                    text = split_title(row.title)[3] if hasattr(row, 'textTitle') else ""
                    return name, row.textTitle if hasattr(row, 'textTitle') and row.textTitle else text

    return "", ""


def detect_outgoing_liaisons(wp_rows):
    """Auto-detect outgoing liaison TD numbers from WP TDs.

    Detects titles starting with 'LS/o' (case-insensitive) or
    containing 'liaison statement' with outgoing indicators.

    Returns a list of TD number strings.
    """
    outgoing_ls = []
    for row in wp_rows:
        title = row.title or ''
        title_lower = title.lower().strip()
        if (title_lower.startswith('ls/o')
                or ('liaison statement' in title_lower
                    and ('outgoing' in title_lower or '[to ' in title_lower))):
            val = row.number.value.strip()
            if val and val not in outgoing_ls:
                outgoing_ls.append(val)
    return outgoing_ls


def parse_timing(timing_str):
    """Parse work programme timing string to a datetime for comparison.

    Handles: '2026-06', '2026-12', '2027-Q1', '2027-Q2', etc.
    Returns datetime or None.
    """
    timing_str = timing_str.strip()
    quarter_map = {'Q1': '03', 'Q2': '06', 'Q3': '09', 'Q4': '12'}
    for q, month in quarter_map.items():
        if q in timing_str:
            year = timing_str.split('-')[0]
            try:
                return datetime(int(year), int(month), 28)
            except ValueError:
                return None
    try:
        return datetime.strptime(timing_str, '%Y-%m')
    except ValueError:
        return None


def print_work_programme_summary(work_items):
    """Print a summary of scraped work programme items."""
    print(f"\n  Work Programme: {len(work_items)} item(s)")
    for wi in work_items:
        status = wi.status or "?"
        process = wi.approvalProcess or "?"
        name = wi.workItem or "?"
        if len(name) > 30:
            name = name[:27] + "..."
        print(f"    {name:<30} Status: {status:<25} Process: {process}")
