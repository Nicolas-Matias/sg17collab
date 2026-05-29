#!/usr/bin/env python3
"""Generate LaTeX content files for an ITU-T Question report.

Usage:
    python generate_question_report.py <config.json>

Reads a JSON configuration file, fetches data from the ITU website,
and generates LaTeX snippet files in ../question_doc_template/chapters/results/.
These snippets are included by the .tex templates in ../question_doc_template/chapters/.
"""

import sys
import os

# Add script directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.config import load_question_config
from common.itu_api import get_documents, get_question, get_study_group, get_work_programme, get_work_item_editors
from common.utils import (
    comma_separated_list, find_td_by_name, find_td_by_number,
    find_question_name_td_and_a5, stripped_starts_with,
    is_new_work_item, get_rapporteurs, get_associate_rapporteurs,
    get_meeting_reports, extract_alt_name, extract_new_work_item_info,
    detect_outgoing_liaisons, detect_processed_work_items, print_work_programme_summary,
    parse_timing,
)
from common.latex import (
    URL, escape_latex, make_href, td_href, write_result, table_row_str, seqsplit_text,
)
from common.models import split_title

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(PROJECT_DIR, 'question_doc_template', 'chapters', 'variables')


def _format_date_range(start_dt, end_dt):
    """Format date range as 'D - D Month YYYY' or 'D Month - D Month YYYY'."""
    if end_dt is None:
        return f"{start_dt.day} {start_dt.strftime('%B')} {start_dt.year}"
    if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
        return (f"{start_dt.day} - {end_dt.day} "
                f"{end_dt.strftime('%B')} {end_dt.year}")
    return (f"{start_dt.day} {start_dt.strftime('%B')} - "
            f"{end_dt.day} {end_dt.strftime('%B')} {end_dt.year}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.json>")
        sys.exit(1)

    config = load_question_config(sys.argv[1])
    group = config['group']
    question = config['question']
    place = config['place']
    start = config['start']
    end = config['end']
    start_string = config['startString']
    start_date = config['startDate']
    next_meeting = config.get('next_meeting')

    # ---------------------------------------------------------------
    # Fetch data from ITU website
    # ---------------------------------------------------------------
    print("Fetching study group structure...")
    sg_details = get_study_group(group=group, start=start_string)

    # Find which WP this question belongs to
    wp_number = ''
    for wp in sg_details.workingParties:
        for q in wp.questions:
            if q.number == question:
                wp_number = wp.number
                break
    if not wp_number:
        print(f"Question {question} not found in study group {group}")
        sys.exit(1)

    print("Fetching question details...")
    question_details = get_question(group=group, question=question, start=start_date)
    rapporteurs = get_rapporteurs(question_details)
    associate_rapporteurs = get_associate_rapporteurs(question_details)

    print("Fetching documents...")
    c_rows = get_documents(document_type="C", group=group, working_party=wp_number,
                           questions=question, start=start_date)
    plen_rows = get_documents(document_type="PLEN", group=group, working_party=wp_number,
                              questions=question, start=start_date)
    all_plen_rows = get_documents(document_type="PLEN", group=group, working_party=wp_number,
                                  questions="QALL", start=start_date)
    gen_rows = get_documents(document_type="GEN", group=group, working_party=wp_number,
                             questions=question, start=start_date)
    all_gen_rows = get_documents(document_type="GEN", group=group, working_party=wp_number,
                                 questions="QALL", start=start_date)
    wp_rows = get_documents(document_type="WP", group=group, working_party=wp_number,
                            questions=question, start=start_date)
    all_wp_rows = get_documents(document_type="WP", group=group, working_party=wp_number,
                                questions="QALL", start=start_date)

    # Display fetched TDs
    _print_td_summary("Contributions (C)", c_rows)
    _print_td_summary("TD/PLEN (Q-specific)", plen_rows)
    _print_td_summary("TD/PLEN (QALL)", all_plen_rows)
    _print_td_summary("TD/GEN (Q-specific)", gen_rows)
    _print_td_summary("TD/GEN (QALL)", all_gen_rows)
    _print_td_summary(f"TD/WP{wp_number} (Q-specific)", wp_rows)
    _print_td_summary(f"TD/WP{wp_number} (QALL)", all_wp_rows)

    # ---------------------------------------------------------------
    # Process work programme (scraped from ITU website)
    # ---------------------------------------------------------------
    print("Fetching work programme...")
    work_item_details = get_work_programme(
        group=group, question=question,
        working_party=wp_number, start=start_string)

    work_items = [wi.workItem for wi in work_item_details]

    # Display work programme summary
    print_work_programme_summary(work_item_details)

    print("Fetching work item editors...")
    editors = get_work_item_editors(work_item_details)

    approval = []
    determination = []
    consent = []
    non_normative = []
    new_work_items = []
    outgoing_ls = []

    # Auto-detect approval/consent/determination/agreement from TD titles only
    # (e.g., "Approval - X.1234: Title", "Determination - X.5678: Title")
    # Also build td_to_work_item mapping by matching work item name to work programme
    td_to_work_item = {}
    for row in wp_rows:
        val = row.number.value.strip()
        if row.documentType == 'Approval':
            if val not in approval:
                approval.append(val)
        elif row.documentType == 'Determination':
            if val not in determination:
                determination.append(val)
        elif row.documentType == 'Consent':
            if val not in consent:
                consent.append(val)
        elif row.documentType == 'Agreement':
            if val not in non_normative:
                non_normative.append(val)

        # Match work item name from TD to work programme data
        work_item_name = row.recommendation or row.acronym
        if work_item_name:
            for wi in work_item_details:
                # Match by work item name (e.g., "X.1234" or "X.abc")
                wi_name = wi.workItem or ""
                # Normalize for comparison (remove spaces, handle "ex" aliases)
                if wi_name and (work_item_name in wi_name or wi_name in work_item_name or
                               work_item_name.split()[0] == wi_name.split()[0] if ' ' in work_item_name else False):
                    td_to_work_item[val] = wi
                    print(f"  Matched TD {val} ({work_item_name}) -> WP: {wi_name}, version={wi.version}")
                    break

    # Detect processed work items (under study items with TDs)
    processed_work_items = detect_processed_work_items(work_item_details, wp_rows)

    # Auto-detect candidate work items for next SG meeting
    # Criteria: "Under study" items with timing between end of current meeting and next_meeting
    from datetime import timedelta
    candidate_next = []
    if next_meeting:
        next_meeting_date = next_meeting
    else:
        # Default to 6 months after start if next_meeting not specified
        next_meeting_date = start + timedelta(days=180)

    for wi in work_item_details:
        status = (wi.status or '').strip()
        if not status.startswith('Under study'):
            continue
        timing = (wi.timing or '').strip()
        if not timing:
            continue
        timing_date = parse_timing(timing)
        # Candidate if timing is between end of current meeting and next meeting
        if timing_date and end and timing_date > end and timing_date <= next_meeting_date:
            name = wi.workItem or ""
            if name and name not in candidate_next:
                candidate_next.append(name)

    if candidate_next:
        print(f"  Found {len(candidate_next)} candidate work items for next meeting")

    # Auto-detect outgoing liaisons from GEN TDs
    outgoing_ls = detect_outgoing_liaisons(gen_rows)

    # Find agenda and report TDs
    agenda_number = ""
    agenda_url = ""
    # Match patterns like "agenda of Q10/17" or "agenda of Question 10/17"
    agenda_patterns = [
        f"agenda of q{question}/{group}",
        f"agenda of question {question}/{group}",
    ]
    for row in wp_rows:
        title_lower = row.title.lower()
        for pattern in agenda_patterns:
            if pattern in title_lower:
                agenda_number = row.number.value.replace(' ', '')
                agenda_url = URL + row.number.link
                print(f"  Found agenda TD: {agenda_number} - {row.title}")
                break
        if agenda_number:
            break
    if not agenda_number:
        print(f"  WARNING: No agenda TD found for Question {question}/{group}")

    report_number = ''
    report_title_prefix = f"Report of Question {question}/{group}"
    interim_report_prefix = f"Report of ITU-T Q{question}/{group}"
    interim_reports = []
    for row in wp_rows:
        if stripped_starts_with(report_title_prefix, row.title):
            report_number = row.number.value.replace(' ', '')
        elif stripped_starts_with(interim_report_prefix, row.title):
            interim_reports.append(
                make_href(URL + row.number.link,
                          f"TD{row.number.value}/{wp_number}{row.lastRev}")
            )

    year = int(start_date[2:4])
    period = str(int(year / 4) * 4 + 1)

    # ---------------------------------------------------------------
    # Generate LaTeX snippets
    # ---------------------------------------------------------------
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"\nGenerating LaTeX snippets to {RESULTS_DIR}/")

    # --- Variables (includes \contact macro) ---
    _generate_variables(group, question, wp_number, place, start, end,
                        start_date, period, question_details, report_number)

    # --- Introduction variables ---
    _gen_introduction(question_details, rapporteurs, associate_rapporteurs, agenda_url, agenda_number, wp_number)

    _generate_report(
            group, question, wp_number, start_date, period,
            c_rows, plen_rows, gen_rows, wp_rows,
            all_plen_rows, all_gen_rows, all_wp_rows,
            approval, determination, consent, non_normative,
            work_items, work_item_details, new_work_items,
            outgoing_ls,
            td_to_work_item,
            editors,
            processed_work_items,
            candidate_next,
        )

    print("\nDone.")


# ===================================================================
# Variables file (used by LaTeX templates as macros)
# ===================================================================

def _generate_variables(group, question, wp_number, place, start, end,
                        start_date, period, question_details, doc_number):
    """Generate results/00-variables.tex with LaTeX macro definitions.

    Produces \\newcommand entries for all document-level variables,
    including a \\contact command with the contact longtable.
    """
    year = int(start_date[0:4])
    first_year = int(year / 4) * 4 + 1
    last_year = first_year + 3

    occurence = _format_date_range(start, end)

    lines = [
        f"\\newcommand{{\\studyGroup}}{{{group}}}",
        f"\\newcommand{{\\workingParty}}{{{wp_number}}}",
        f"\\newcommand{{\\questions}}{{{question}}}",
        f"\\newcommand{{\\place}}{{{place}}}",
        f"\\newcommand{{\\occurence}}{{{occurence}}}",
        f"\\newcommand{{\\startDate}}{{{start_date}}}",
        f"\\newcommand{{\\studyPeriod}}{{{first_year}-{last_year}}}",
        f"\\newcommand{{\\period}}{{{period}}}",
        f"\\newcommand{{\\reportNumber}}{{{doc_number}}}",
        f"\\newcommand{{\\tdNumber}}{{}}",  # TD number assigned by secretariat
        f"\\newcommand{{\\abstr}}{{This TD contains the report for Question {question}/{group} meeting.}}",
    ]

    # Contact command — embeds all contacts in a single \contact macro
    contact_lines = []
    for role in question_details.roles:
        role_label = role.roleName or "Contact"
        name = f"{role.firstName} {role.lastName}".strip()
        country = escape_latex(role.address)
        title_line = f"Q{question}/{group} {role_label}"
        contact_info = []
        if role.tel:
            contact_info.append(f"Tel: {escape_latex(role.tel)}")
        if role.email:
            contact_info.append(f"Email: \\ul{{{escape_latex(role.email)}}}")

        contact_lines.append("\\begin{longtable}{p{0.15\\linewidth} p{0.30\\linewidth} p{0.50\\linewidth}}")
        contact_lines.append("\\midrule")
        contact_lines.append(
            f"\\textbf{{Contact:}} &\n"
            f"{escape_latex(name)}\\newline\n"
            f"{country}\\newline\n"
            f"{escape_latex(title_line)} &\n"
            f"{' \\newline '.join(contact_info)} \\\\")
        contact_lines.append("\\midrule")
        contact_lines.append("\\end{longtable}")

    lines.append("")
    lines.append("\\newcommand{\\contact}{")
    lines.extend(contact_lines)
    lines.append("}")

    write_result(RESULTS_DIR, "00-metadata.tex", "\n".join(lines) + "\n")


# ===================================================================
# Agenda generation
# ===================================================================

def _generate_report(group, question, wp_number, start_date,
                     period, c_rows, plen_rows, gen_rows, wp_rows,
                     all_plen_rows, all_gen_rows, all_wp_rows,
                     approval, determination, consent, non_normative,
                     work_items, work_item_details, new_work_items,
                     outgoing_ls,
                     td_to_work_item=None, editors=None, processed_work_items=None,
                     candidate_next=None):
    """Generate all LaTeX snippet files for a Question report."""

    _gen_executive_summary(group, question, c_rows, approval, determination,
                           consent, non_normative, work_items, new_work_items,
                           outgoing_ls,
                           wp_rows, gen_rows, processed_work_items)
    _gen_documentation(group, question, wp_number, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows)
    _gen_interim_reports(group, question, wp_number, wp_rows)
    _gen_discussions(group, question, wp_number, work_items, c_rows, gen_rows,
                     wp_rows, processed_work_items)
    _gen_draft_recommendations(group, question, wp_number, wp_rows,
                               approval, determination, consent, non_normative,
                               td_to_work_item)
    _gen_outgoing_liaisons(outgoing_ls, gen_rows)
    _gen_work_programme(group, question, wp_number, work_item_details,
                        new_work_items, wp_rows, editors)
    _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors)
    _gen_annex_a(group, question, wp_number, c_rows, gen_rows, plen_rows, wp_rows,
                 all_gen_rows, all_plen_rows, all_wp_rows)
    _gen_annex_c(wp_number, wp_rows)


# --- Section generators ---

def _gen_introduction(question_details, rapporteurs, associate_rapporteurs, agenda_url, agenda_number, wp_number):
    """01.tex — introduction variables (questionTitle, leadership, assistedBy, agendaRef)."""
    leadership = " and ".join(escape_latex(r) for r in rapporteurs) if rapporteurs else ""
    title = escape_latex(question_details.title or '')

    # Format "assisted by [Associate Rapporteurs]" if any exist
    if associate_rapporteurs:
        assisted_by = ", assisted by " + ", ".join(escape_latex(ar) for ar in associate_rapporteurs)
    else:
        assisted_by = ""

    # Format agenda as hyperlink with TD number (e.g., "TD 123/WP1" as clickable link)
    if agenda_number and agenda_url:
        agenda_ref = make_href(agenda_url, f"TD {agenda_number}/{wp_number}")
    else:
        agenda_ref = ""

    lines = [
        f"\\newcommand{{\\questionTitle}}{{{title}}}",
        f"\\newcommand{{\\leadership}}{{{leadership}}}",
        f"\\newcommand{{\\assistedBy}}{{{assisted_by}}}",
        f"\\newcommand{{\\agendaRef}}{{{agenda_ref}}}",
    ]
    write_result(RESULTS_DIR, "01-introduction.tex", "\n".join(lines) + "\n")


def _gen_executive_summary(group, question, c_rows, approval, determination,
                           consent, non_normative, work_items, new_work_items,
                           outgoing_ls,
                           wp_rows, gen_rows=None, processed_work_items=None):
    """02.tex — executive summary variables (nbContributions, listQuestionContributions)."""
    gen_rows = gen_rows or []
    processed_work_items = processed_work_items or []

    def _make_td_links(td_numbers, rows, suffix=""):
        """Create hyperlinks for TD numbers."""
        links = []
        for n in td_numbers:
            _, td = find_td_by_number(rows, n)
            if td:
                links.append(make_href(URL + td.number.link, f"TD {n}{suffix}"))
            else:
                links.append(f"TD {n}{suffix}")
        return links

    # Build the itemize list
    items = []

    # Approval
    if approval:
        links = _make_td_links(approval, wp_rows)
        items.append(f"  \\item Recommendations finalized and proposed for TAP Approval: "
                     f"{comma_separated_list(links)}")
    else:
        items.append(f"  \\item Recommendations finalized and proposed for TAP Approval: None")

    # Consent
    if consent:
        links = _make_td_links(consent, wp_rows)
        items.append(f"  \\item Recommendations finalized and proposed for TAP Consent: "
                     f"{comma_separated_list(links)}")
    else:
        items.append(f"  \\item Recommendations finalized and proposed for TAP Consent: None")

    # Determination
    if determination:
        links = _make_td_links(determination, wp_rows)
        items.append(f"  \\item Recommendations finalized and proposed for TAP Determination: "
                     f"{comma_separated_list(links)}")
    else:
        items.append(f"  \\item Recommendations finalized and proposed for TAP Determination: None")

    # Agreement
    if non_normative:
        links = _make_td_links(non_normative, wp_rows)
        items.append(f"  \\item Recommendations finalized and proposed for TAP Agreement: "
                     f"{comma_separated_list(links)}")
    else:
        items.append(f"  \\item Recommendations finalized and proposed for TAP Agreement: None")

    # Work items progressed
    if processed_work_items:
        td_links = [make_href(URL + td.number.link, f"TD {td_num}")
                    for name, td_num, td in processed_work_items]
        items.append(f"  \\item Work items progressed: {comma_separated_list(td_links)}")
    elif work_items:
        items.append(f"  \\item Work items progressed: {comma_separated_list(work_items)}")
    else:
        items.append(f"  \\item Work items progressed: None")

    # Outgoing liaison statements (from gen_rows)
    if outgoing_ls:
        links = _make_td_links(outgoing_ls, gen_rows, "/G")
        items.append(f"  \\item Outgoing liaison statements agreed: {comma_separated_list(links)}")
    else:
        items.append(f"  \\item Outgoing liaison statements agreed: None")

    # Build the two macros
    lines = [
        f"\\newcommand{{\\nbContributions}}{{{len(c_rows)}}}",
        "",
        "\\newcommand{\\listQuestionContributions}{",
        "\\begin{itemize}",
    ]
    lines.extend(items)
    lines.append("\\end{itemize}")
    lines.append("}")

    write_result(RESULTS_DIR, "02-executive-summary.tex", "\n".join(lines) + "\n")


def _gen_documentation(group, question, wp_number, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows):
    """03.tex — documentation variables (documentation, reflectorUrl, subUrl, ifaUrl)."""
    # \documentation — itemize list of document links
    doc_lines = []
    doc_lines.append("\\begin{itemize}")
    c_links = ", ".join(td_href(r, "C") for r in reversed(c_rows))
    doc_lines.append(f"  \\item Contributions: {c_links}")

    p_links = ", ".join(
        make_href(URL + r.number.link, f"{r.number.value}{r.lastRev}")
        for r in reversed(plen_rows)
    )
    doc_lines.append(f"  \\item TD/P: {p_links}")

    g_links = ", ".join(
        make_href(URL + r.number.link, f"{r.number.value}{r.lastRev}")
        for r in reversed(gen_rows)
    )
    doc_lines.append(f"  \\item TD/G: {g_links}")

    w_links = ", ".join(
        make_href(URL + r.number.link, f"{r.number.value}{r.lastRev}")
        for r in reversed(wp_rows)
    )
    doc_lines.append(f"  \\item TD/{wp_number}: {w_links}")
    doc_lines.append("\\end{itemize}")

    # Email URLs - format: t25sg17qXX@lists.itu.int (lowercase q, two-digit question)
    reflector = f"t{period}sg{group}q{int(question):02d}@lists.itu.int"
    year = int(start_date[0:4])
    first_year = int(year / 4) * 4 + 1
    last_year = first_year + 3
    sub_url = f"{URL}/net4/iwm?p0=0&p11=ITU&p12=ITU-SEP-ITU-T-SEP-SP\\%2017-SEP-Study\\%20Group\\%2017&p21=ITU&p22=ITU"
    ifa_url = f"{URL}/en/ITU-T/studygroups/{first_year}-{last_year}/{group}/Pages/ifa-structure.aspx"

    lines = [
        "\\newcommand{\\documentation}{",
        "\n".join(doc_lines),
        "}",
        "",
        f"\\newcommand{{\\reflectorUrl}}{{\\ul{{{reflector}}}}}",
        "",
        f"\\newcommand{{\\subUrl}}{{\\href{{{sub_url}}}{{subscription webpage}}}}",
        "",
        f"\\newcommand{{\\ifaUrl}}{{\\href{{{ifa_url}}}{{webpage}}}}",
    ]
    write_result(RESULTS_DIR, "03-documentation.tex", "\n".join(lines) + "\n")


def _gen_interim_reports(group, question, wp_number, wp_rows):
    """04.tex — interim reports variable (interimReports)."""
    meeting_reports = get_meeting_reports(wp_rows, question, group)
    content_lines = []

    if meeting_reports:
        suffix = "meeting" if len(meeting_reports) == 1 else "meetings"
        content_lines.append(f"Since the last SG{group} meeting, Question {question}/{group} "
                             f"held the following Rapporteur {suffix}")
        content_lines.append("\\begin{itemize}")
        for report in meeting_reports:
            # Extract place and date from title like "(Paris, 6 December 2024)"
            place = ""
            date = ""
            idx1 = report.title.rfind('(')
            if idx1 >= 0:
                idx2 = report.title.find(')', idx1)
                if idx2 >= 0:
                    content = report.title[idx1 + 1:idx2]
                    # Split by comma: "Paris, 6 December 2024" -> ["Paris", "6 December 2024"]
                    parts = content.split(',', 1)
                    if len(parts) == 2:
                        place = parts[0].strip()
                        date = parts[1].strip()
                    else:
                        # No comma, might be just place or date
                        place = content.strip()

            td_number = report.number.value.replace(' ', '')
            td_link = make_href(URL + report.number.link, f"TD {td_number}/{wp_number}")
            content_lines.append(
                f"  \\item The report of the Rapporteur meeting from {date} ({place}), "
                f"can be found in {td_link}"
            )
        content_lines.append("\\end{itemize}")
    else:
        content_lines.append("\\textit{No interim rapporteur meetings were held.}")

    lines = [
        "\\newcommand{\\interimReports}{",
        "\n".join(content_lines),
        "}",
    ]
    write_result(RESULTS_DIR, "04-interim-reports.tex", "\n".join(lines) + "\n")


def _gen_discussions(group, question, wp_number, work_items, c_rows, gen_rows,
                     wp_rows, processed_work_items=None):
    """05-discussions subsection content files."""
    processed_work_items = processed_work_items or []
    selected_rows = []

    # 05-01: Ongoing work items (from processed_work_items in part 2)
    lines = []
    if processed_work_items:
        for i, (name, td_num, td) in enumerate(processed_work_items):
            td_link = make_href(URL + td.number.link, f"TD {td_num}")
            lines.append(f"\\subsubsection{{Work Item {i + 1}: ({escape_latex(name)}):}}\n")
            lines.append(f"{td_link}\n")
            # Find related contributions
            search_term = name.split(' ')[0] if ' ' in name else name
            for row in c_rows:
                if search_term.lower() in row.title.lower():
                    selected_rows.append(row)
                    lines.append(f"{td_href(row, 'C')}\n")
            lines.append(f"\\textit{{TODO: write the observation here}}\n")
    else:
        # Fallback to old behavior if no processed_work_items
        for i, wi in enumerate(work_items):
            lines.append(f"\\subsubsection{{Work Item {i + 1}: ({wi}):}}\n")
            idx = wi.find(' ')
            search_term = wi[:idx] if idx > 0 else wi
            for row in c_rows:
                if search_term.lower() in row.title.lower():
                    selected_rows.append(row)
                    lines.append(f"{td_href(row, 'C')}\n")
            lines.append(f"\\textit{{TODO: write the observation here}}\n")
    write_result(RESULTS_DIR, "05-01-work-items.tex", "\n".join(lines))

    # 05-02: New proposed work items (search in wp_rows for "Proposal", "NWI", or "new work item")
    lines = []
    num = 0
    for row in wp_rows:
        if is_new_work_item(row.title):
            num += 1
            td_link = make_href(URL + row.number.link, f"TD {row.number.value.replace(' ', '')}/{wp_number}")
            lines.append(f"\\subsubsection{{New Work Item {num}: ({escape_latex(row.title)}):}}\n")
            lines.append(f"{td_link}\n")
            lines.append(f"\\textit{{TODO: write the observation here}}\n")
    write_result(RESULTS_DIR, "05-02-new-work-items.tex", "\n".join(lines))

    # 05-03: Other contributions
    lines = []
    for row in c_rows:
        if row not in selected_rows:
            lines.append(f"{td_href(row, 'C')}: {escape_latex(row.title)}\n")
    write_result(RESULTS_DIR, "05-03-other-contributions.tex", "\n".join(lines))

    # 05-04: Incoming liaison statements
    selected_gen = []
    lines = []
    for row in gen_rows:
        if row.title.startswith("LS/i"):
            selected_gen.append(row)
            source_link = make_href(URL + row.source.link, row.source.name)
            lines.append(
                f"{make_href(URL + row.number.link, f'TD{row.number.value}{row.lastRev}/G')}: "
                f"{escape_latex(row.title)} [from {source_link}]\n"
            )
            lines.append(f"\\textit{{TODO: write the observation here}}\n")
    write_result(RESULTS_DIR, "05-04-incoming-liaisons.tex", "\n".join(lines))


def _gen_recommendation_table_rows(wp_rows, items, group, question, wp_number, has_a5=True, td_wi=None):
    """Generate table rows for recommendation tables (approval/determination/consent)."""
    td_wi = td_wi or {}
    lines = []
    for num, element in enumerate(items, 1):
        q_name, td, a5 = find_question_name_td_and_a5(wp_rows, element)

        if td is not None:
            final_text = make_href(URL + td.number.link,
                                   f"TD {td.number.value}{td.lastRev}/{wp_number}")
        else:
            final_text = "no update"

        a5_text = ""
        if a5 is not None:
            a5_text = make_href(URL + a5.number.link,
                                f"TD {a5.number.value}{a5.lastRev}/{wp_number}")

        # Extract work item name: find part starting with X., stop at first space
        work_item = ""
        text_title = ""
        if td is not None:
            source = td.recommendation or td.acronym or ""
            for part in source.split():
                if part.startswith('X.') or part.startswith('XSTR.'):
                    work_item = part
                    break
            text_title = escape_latex(td.textTitle)

        # Fill version and equiv. num. from work programme data
        wp_wi = td_wi.get(element)
        version = escape_latex(wp_wi.version) if wp_wi and wp_wi.version else ""
        equiv_num = escape_latex(wp_wi.equivNum) if wp_wi and wp_wi.equivNum else ""
        # If no work_item found from TD, try to get it from work programme
        if not work_item and wp_wi:
            work_item = wp_wi.workItem or ""
        if not text_title and wp_wi:
            text_title = escape_latex(wp_wi.title or "")

        # Removed # and Question columns
        if has_a5:
            lines.append(table_row_str([
                seqsplit_text(work_item), version, text_title,
                final_text, a5_text, equiv_num
            ]))
        else:
            lines.append(table_row_str([
                seqsplit_text(work_item), version, text_title, final_text
            ]))
    return "".join(lines)


def _gen_draft_recommendations(group, question, wp_number, wp_rows,
                               approval, determination, consent, non_normative,
                               td_to_work_item=None):
    """06-draft-recommendations table rows."""
    td_wi = td_to_work_item or {}

    # TAP approval
    rows = _gen_recommendation_table_rows(wp_rows, approval, group, question, wp_number, td_wi=td_wi)
    has_approval = "true" if approval else "false"
    write_result(RESULTS_DIR, "06-approval.tex",
                 f"\\newcommand{{\\hasApproval}}{{{has_approval}}}\n"
                 f"\\newcommand{{\\approval}}{{\n{rows}}}\n")

    # TAP determination
    rows = _gen_recommendation_table_rows(wp_rows, determination, group, question, wp_number, td_wi=td_wi)
    has_determination = "true" if determination else "false"
    write_result(RESULTS_DIR, "06-determination.tex",
                 f"\\newcommand{{\\hasDetermination}}{{{has_determination}}}\n"
                 f"\\newcommand{{\\determination}}{{\n{rows}}}\n")

    # AAP consent
    rows = _gen_recommendation_table_rows(wp_rows, consent, group, question, wp_number, td_wi=td_wi)
    has_consent = "true" if consent else "false"
    write_result(RESULTS_DIR, "06-consent.tex",
                 f"\\newcommand{{\\hasConsent}}{{{has_consent}}}\n"
                 f"\\newcommand{{\\consent}}{{\n{rows}}}\n")

    # Non-normative / agreement
    lines = []
    for num, element in enumerate(non_normative, 1):
        q_name, td, a5 = find_question_name_td_and_a5(wp_rows, element)
        if td is None:
            print(f"WARNING: Could not find TD for agreement number '{element}', skipping row")
            continue

        final_text = make_href(URL + td.number.link,
                               f"TD {td.number.value}{td.lastRev}/{wp_number}")
        # Extract work item name: find part starting with X./XSTR., stop at first space
        work_item = ""
        source = td.acronym or td.recommendation or ""
        for part in source.split():
            if part.startswith('X.') or part.startswith('XSTR.'):
                work_item = part
                break

        # Use work programme data for version if available
        wp_wi = td_wi.get(element)
        version = escape_latex(wp_wi.version) if wp_wi and wp_wi.version else ""

        text_title = escape_latex(split_title(td.title)[3])

        # Removed # and Question columns
        lines.append(table_row_str([
            seqsplit_text(work_item), version, text_title, final_text
        ]))
    rows = "".join(lines)
    has_agreement = "true" if non_normative else "false"
    write_result(RESULTS_DIR, "07-agreement.tex",
                 f"\\newcommand{{\\hasAgreement}}{{{has_agreement}}}\n"
                 f"\\newcommand{{\\agreement}}{{\n{rows}}}\n")


def _gen_outgoing_liaisons(outgoing_ls, gen_rows):
    """09-outgoing-liaison-statements table rows."""
    lines = []
    for num, element in enumerate(outgoing_ls, 1):
        q_name, td = find_td_by_number(gen_rows, element)
        title = ""
        td_name = "no update"
        action_to = ""
        info_to = ""
        if td:
            title = td.title
            action_to, info_to = _parse_liaison_destinations(title)
            td_name = make_href(URL + td.number.link,
                                f"TD {element}{td.lastRev}/G")

        # Combine action_to and info_to in single column (without prefixes)
        combined_dest = []
        if action_to:
            combined_dest.append(escape_latex(action_to))
        if info_to:
            combined_dest.append(escape_latex(info_to))
        destination = " / ".join(combined_dest) if combined_dest else "\\textit{(manual entry)}"

        # Columns: Title | For information / For action to | TD number
        lines.append(table_row_str([
            escape_latex(title),
            destination,
            td_name
        ]))

    rows = "".join(lines)
    has_outgoing_liaisons = "true" if outgoing_ls else "false"
    write_result(RESULTS_DIR, "08-outgoing-liaisons.tex",
                 f"\\newcommand{{\\hasOutgoingLiaisons}}{{{has_outgoing_liaisons}}}\n"
                 f"\\newcommand{{\\outgoingLiaisons}}{{\n{rows}}}\n")


def _parse_liaison_destinations(title):
    """Parse '[to X]' and '[for info to Y]' from a liaison statement title.

    Returns (action_to, info_to) strings.
    """
    action_to = ""
    info_to = ""
    # Find all bracketed sections
    idx = 0
    while idx < len(title):
        start = title.find('[', idx)
        if start < 0:
            break
        end = title.find(']', start)
        if end < 0:
            break
        bracket = title[start + 1:end].strip()
        if bracket.lower().startswith('for info'):
            # "[for info to X, Y]" → extract after "for info to "
            prefix = 'for info to '
            pos = bracket.lower().find(prefix)
            if pos >= 0:
                info_to = bracket[pos + len(prefix):]
        elif bracket.lower().startswith('to '):
            action_to = bracket[3:]  # skip "to "
        idx = end + 1
    return action_to, info_to


def _gen_work_programme(group, question, wp_number, work_item_details,
                        new_work_items, wp_rows, editors=None):
    """10-work-programme table rows (new, deleted, ongoing)."""
    editors = editors or {}

    # New work items (from wp_rows, same as part 5.2)
    lines = []
    for row in wp_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)
            # Skip entries without a valid work item name (X. or XSTR.)
            if not work_item:
                continue
            td_link = make_href(URL + row.number.link, f"TD {row.number.value.replace(' ', '')}/{wp_number}")
            # Columns: Work Item | Status | Title | Editor | Base Text | Equivalent | Approval process
            lines.append(table_row_str([
                seqsplit_text(work_item), "New",
                escape_latex(text_title), "(manual entry)", td_link, "", ""
            ]))
    rows = "".join(lines)
    has_new_work_items = "true" if lines else "false"
    write_result(RESULTS_DIR, "09-wp-new.tex",
                 f"\\newcommand{{\\hasNewWorkItems}}{{{has_new_work_items}}}\n"
                 f"\\newcommand{{\\newWorkItems}}{{\n{rows}}}\n")

    # Ongoing work items — only "Under study" status
    lines = []
    for wi in work_item_details:
        name = wi.workItem or ""
        title = wi.title or ""
        status = wi.status or ""
        equiv = wi.equivNum or ""
        timing = wi.timing or ""
        aap = wi.approvalProcess or ""

        if "under study" not in status.lower():
            continue

        # Try to find matching WP TD for the base text link
        td_name = "no update"
        _, td = find_td_by_name(wp_rows, name)
        if td is None:
            alt = extract_alt_name(name)
            if alt:
                _, td = find_td_by_name(wp_rows, alt)
        if td:
            td_name = make_href(URL + td.number.link,
                                f"TD{td.number.value}{td.lastRev}/{wp_number}")
            if not title:
                title = td.textTitle

        # New columns (removed # and Question): Work Item | Status | Title | Editor | Base Text | Equivalent | Target Date | Summary updated | AAP
        lines.append(table_row_str([
            seqsplit_text(name), escape_latex(status),
            escape_latex(title), "(manual entry)", td_name, escape_latex(equiv),
            escape_latex(timing), "", escape_latex(aap)
        ]))
    rows = "".join(lines)
    has_ongoing_work_items = "true" if lines else "false"
    write_result(RESULTS_DIR, "09-wp-ongoing.tex",
                 f"\\newcommand{{\\hasOngoingWorkItems}}{{{has_ongoing_work_items}}}\n"
                 f"\\newcommand{{\\ongoingWorkItems}}{{\n{rows}}}\n")


def _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors=None):
    """10-candidate-work-items.tex — candidate work items for next SG meeting."""
    editors = editors or {}
    candidate_next = candidate_next or []
    lines = []

    for element in candidate_next:
        # Find matching work item in work programme
        wi_match = None
        for wi in work_item_details:
            wi_name = wi.workItem or ""
            wi_alt = extract_alt_name(wi_name)
            if (wi_name == element or wi_alt == element
                    or element in wi_name or (wi_alt and element in wi_alt)):
                wi_match = wi
                break

        name = element
        status = ""
        title = ""
        equiv = ""

        if wi_match:
            status = wi_match.status or ""
            title = wi_match.title or ""
            equiv = wi_match.equivNum or ""

        # Try to find matching WP TD for the base text link
        # Look for TDs containing "baseline text" in the title AND the work item name
        td_name = "no update"
        td = None
        element_lower = element.lower()
        alt = extract_alt_name(element)
        alt_lower = alt.lower() if alt else ""

        for row in wp_rows:
            row_title = (row.title or "").lower()
            # Check if this is a baseline text TD for this work item
            if "baseline text" in row_title:
                # Check if work item name appears in the title
                if element_lower in row_title or (alt_lower and alt_lower in row_title):
                    td = row
                    break

        if td:
            td_name = make_href(URL + td.number.link,
                                f"TD{td.number.value}{td.lastRev}/{wp_number}")
            if not title:
                title = td.textTitle

        # Columns: Work Item | Status | Title | Editor | Base Text | A.5 justification | Equivalent
        lines.append(table_row_str([
            seqsplit_text(name), escape_latex(status),
            escape_latex(title), "(manual entry)", td_name, "", escape_latex(equiv)
        ]))

    rows = "".join(lines)
    has_candidate = "true" if candidate_next else "false"

    write_result(RESULTS_DIR, "10-candidate-work-items.tex",
                 f"\\newcommand{{\\hasCandidateWorkItems}}{{{has_candidate}}}\n"
                 f"\\newcommand{{\\candidateWorkItems}}{{\n{rows}}}\n")


def _format_source(source_value, group):
    """Format source value, preserving full text with normal spaces.

    Allows text to wrap in table cells when the source name is long.
    Note: Do NOT escape here - make_href() already calls escape_latex().
    """
    if not source_value:
        return source_value
    return source_value


def _gen_annex_c(wp_number, wp_rows):
    """annex-c-new-work-items.tex — list of new work items for Annex C."""
    lines = []
    for row in wp_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)
            if not work_item:
                continue
            td_link = make_href(URL + row.number.link,
                                f"TD {row.number.value.replace(' ', '')}/{wp_number}")
            lines.append(f"  \\item {escape_latex(work_item)}: {escape_latex(text_title)} ({td_link})")

    if lines:
        content = f"\\newcommand{{\\annexNewWorkItems}}{{\n" + "\n".join(lines) + "\n}\n"
    else:
        content = "% No new work items\n"
    write_result(RESULTS_DIR, "annex-c-new-work-items.tex", content)


def _gen_annex_a(group, question, wp_number, c_rows, gen_rows, plen_rows, wp_rows,
                 all_gen_rows=None, all_plen_rows=None, all_wp_rows=None):
    """annex-a table rows (contributions, GEN, PLEN, WP) including QALL documents."""
    q_str = f"Q{question}/{group}"
    qall_str = f"QALL/{group}"
    all_gen_rows = all_gen_rows or []
    all_plen_rows = all_plen_rows or []
    all_wp_rows = all_wp_rows or []

    # Contributions
    lines = []
    for row in c_rows:
        name = make_href(URL + row.number.link, f"C{row.number.value}{row.lastRev}")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-contributions.tex",
                 f"\\newcommand{{\\annexContributions}}{{\n{rows}}}\n")

    # GEN TDs (Q-specific + QALL)
    lines = []
    for row in gen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/G")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    for row in all_gen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/G")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), qall_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-gen.tex",
                 f"\\newcommand{{\\annexGen}}{{\n{rows}}}\n")

    # PLEN TDs (Q-specific + QALL)
    lines = []
    for row in plen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/P")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    for row in all_plen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/P")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), qall_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-plen.tex",
                 f"\\newcommand{{\\annexPlen}}{{\n{rows}}}\n")

    # WP TDs (Q-specific + QALL)
    lines = []
    for row in wp_rows:
        name = make_href(URL + row.number.link,
                         f"TD{row.number.value}{row.lastRev}/{wp_number}")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    for row in all_wp_rows:
        name = make_href(URL + row.number.link,
                         f"TD{row.number.value}{row.lastRev}/{wp_number}")
        source_text = _format_source(row.source.name, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), qall_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-wp.tex",
                 f"\\newcommand{{\\annexWp}}{{\n{rows}}}\n")


def _print_td_summary(label, rows):
    """Print a summary of fetched TD rows."""
    print(f"\n  {label}: {len(rows)} document(s)")
    for row in rows:
        td_num = row.number.value.strip() if row.number else "?"
        rev = row.lastRev if row.lastRev else ""
        title = row.title or ""
        if len(title) > 80:
            title = title[:77] + "..."
        print(f"    TD {td_num}{rev} — {title}")


if __name__ == "__main__":
    main()
