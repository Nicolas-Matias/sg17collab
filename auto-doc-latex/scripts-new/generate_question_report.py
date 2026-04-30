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
import datetime

# Add script directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.config import load_question_config
from common.itu_api import get_documents, get_question, get_study_group, get_work_programme, get_work_item_editors
from common.utils import (
    comma_separated_list, find_td_by_name, find_td_by_number,
    find_question_name_td_and_a5, compare_stripped, stripped_starts_with,
    is_new_work_item, get_rapporteurs, get_associate_rapporteurs,
    get_document_title, get_liaison_destination, get_meeting_reports,
    extract_alt_name, auto_detect_from_work_programme,
    extract_new_work_item_info, detect_outgoing_liaisons,
    print_work_programme_summary,
)
from common.latex import (
    URL, escape_latex, make_href, td_href, write_result, table_row_str,
)
from common.models import split_title

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(PROJECT_DIR, 'question_doc_template', 'chapters', 'results')


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
    doc_type = config['documentType']
    group = config['group']
    question = config['question']
    place = config['place']
    start = config['start']
    end = config['end']
    start_string = config['startString']
    start_date = config['startDate']

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
    wp_rows = get_documents(document_type="WP", group=group, working_party=wp_number,
                            questions=question, start=start_date)

    # Display fetched TDs
    _print_td_summary("Contributions (C)", c_rows)
    _print_td_summary("TD/PLEN (Q-specific)", plen_rows)
    _print_td_summary("TD/PLEN (all Q)", all_plen_rows)
    _print_td_summary("TD/GEN", gen_rows)
    _print_td_summary(f"TD/WP{wp_number}", wp_rows)

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
    deleted_work_items = []
    candidate_next = []
    outgoing_ls = []
    rapporteur_meetings = []

    # Auto-detect approval/consent/determination/agreement from work programme
    # status. Items with "Under study" are ignored.
    td_to_work_item = auto_detect_from_work_programme(
        work_item_details, wp_rows,
        approval, determination, consent, non_normative)

    # Auto-detect outgoing liaisons from WP TDs
    outgoing_ls = detect_outgoing_liaisons(wp_rows)

    # Find time plan, agenda, and report TDs
    time_plan = ""
    for row in all_plen_rows:
        if row.title.startswith("Time plan"):
            time_plan = make_href(URL + row.number.link,
                                  f"TD{row.number.value}{row.lastRev}")
            break

    agenda = ""
    agenda_number = ''
    for row in wp_rows:
        agenda_title = f"Draft agenda of Question {question}/{group}"
        if stripped_starts_with(agenda_title, row.title):
            agenda_number = row.number.value.replace(' ', '')
            agenda = make_href(URL + row.number.link,
                               f"TD{row.number.value}{row.lastRev}")
            break

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
    doc_number = agenda_number if doc_type == "agenda" else report_number
    _generate_variables(group, question, wp_number, place, start, end,
                        start_date, period, rapporteurs, agenda,
                        question_details, doc_type, doc_number)

    # --- Introduction variables (shared by agenda and report) ---
    _gen_introduction(question_details, rapporteurs, agenda)

    if doc_type == "agenda":
        _generate_agenda(group, question, wp_number, start, end, start_date,
                         period, time_plan, c_rows, gen_rows, interim_reports,
                         report_title_prefix)
    elif doc_type == "report":
        _generate_report(
            group, question, wp_number, start_date, period,
            c_rows, plen_rows, gen_rows, wp_rows,
            approval, determination, consent, non_normative,
            work_items, work_item_details, new_work_items, deleted_work_items,
            candidate_next, outgoing_ls, rapporteur_meetings,
            td_to_work_item,
            editors,
        )

    print("\nDone.")


# ===================================================================
# Variables file (used by LaTeX templates as macros)
# ===================================================================

def _generate_variables(group, question, wp_number, place, start, end,
                        start_date, period, rapporteurs, agenda,
                        question_details, doc_type, doc_number):
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
    ]
    if doc_type == "report":
        lines.append(f"\\newcommand{{\\abstr}}{{This TD contains the report for Question {question}/{group} meeting.}}")
    else:
        lines.append(f"\\newcommand{{\\abstr}}{{This TD contains the meeting agenda for Question {question}/{group} meeting.}}")

    # Contact command — embeds all contacts in a single \contact macro
    contact_lines = []
    for role in question_details.roles:
        role_label = role.roleName or "Contact"
        name = f"{role.firstName} {role.lastName}".strip()
        country = escape_latex(role.address)
        title_line = f"WP{wp_number} {role_label}"
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

    write_result(RESULTS_DIR, "00.tex", "\n".join(lines) + "\n")


# ===================================================================
# Agenda generation
# ===================================================================

def _generate_agenda(group, question, wp_number, start, end, start_date,
                     period, time_plan, c_rows, gen_rows, interim_reports,
                     report_title):
    """Generate LaTeX snippets for an agenda document."""
    lines = []

    # Meeting plan
    lines.append(f"The SG{group} timetable, including the sessions allocated for this Question, "
                 f"is to be found in the latest revision of {time_plan}\n")
    day = start
    delta = datetime.timedelta(hours=24)
    while day <= end:
        date_str = day.strftime("%a").upper() + " " + day.strftime("%d/%m/%y")
        first = (day == start)
        penultimate = ((day + delta) == end)
        last = (day == end)
        if not date_str.startswith("SAT") and not date_str.startswith("SUN"):
            lines.append(f"\\textbf{{{date_str}}}\n")
            if first:
                lines.append(f"\\begin{{itemize}}")
                lines.append(f"  \\item S1, S2: Opening plenary of SG{group}")
                lines.append(f"  \\item S3:")
                lines.append(f"  \\item S4:")
                lines.append(f"\\end{{itemize}}\n")
            elif penultimate:
                lines.append(f"\\begin{{itemize}}")
                lines.append(f"  \\item S1, S2, S3, S4: Closing Plenary of WP{wp_number}/{group}")
                lines.append(f"\\end{{itemize}}\n")
            elif last:
                lines.append(f"\\begin{{itemize}}")
                lines.append(f"  \\item S1, S2, S3, S4: Closing Plenary of SG{group}")
                lines.append(f"\\end{{itemize}}\n")
            else:
                lines.append(f"\\begin{{itemize}}")
                lines.append(f"  \\item S1:")
                lines.append(f"  \\item S2:")
                lines.append(f"  \\item S3:")
                lines.append(f"  \\item S4:")
                lines.append(f"\\end{{itemize}}\n")
        day += delta
    write_result(RESULTS_DIR, "agenda-meeting-plan.tex", "\n".join(lines))

    # Documentation
    doc_url = f"{URL}/md/T{period}-SG{group}-{start_date[2:]}/sum/en"
    lines = [f"The SG{group} documents can be found at: \\href{{{doc_url}}}{{{doc_url}}}\n"]
    lines.append("The following documents will be considered:\n")

    # Contributions
    c_links = ", ".join(td_href(r, "C") for r in reversed(c_rows))
    lines.append(f"\\subsection*{{Contributions:}}\n{c_links}\n")

    # Interim reports
    ir_links = ", ".join(reversed(interim_reports))
    lines.append(f"\\subsection*{{Report of interim activities}}\n{ir_links}\n")

    # Incoming LS
    ls_links = ", ".join(
        make_href(URL + r.number.link, f"TD{r.number.value}/G{r.lastRev}")
        for r in reversed(gen_rows) if r.title.startswith("LS/i")
    )
    lines.append(f"\\subsection*{{Incoming Liaison Statements}}\n{ls_links}\n")

    write_result(RESULTS_DIR, "agenda-documentation.tex", "\n".join(lines))


# ===================================================================
# Report generation
# ===================================================================

def _generate_report(group, question, wp_number, start_date,
                     period, c_rows, plen_rows, gen_rows, wp_rows,
                     approval, determination, consent, non_normative,
                     work_items, work_item_details, new_work_items, deleted_work_items,
                     candidate_next, outgoing_ls, rapporteur_meetings,
                     td_to_work_item=None, editors=None):
    """Generate all LaTeX snippet files for a Question report."""

    _gen_executive_summary(group, question, c_rows, approval, determination,
                           consent, non_normative, work_items, new_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           wp_rows)
    _gen_documentation(group, question, wp_number, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows)
    _gen_interim_reports(group, question, wp_number, wp_rows)
    _gen_discussions(group, question, wp_number, work_items, c_rows, gen_rows,
                     plen_rows, wp_rows)
    _gen_draft_recommendations(group, question, wp_number, wp_rows,
                               approval, determination, consent, non_normative,
                               work_items, td_to_work_item)
    _gen_outgoing_liaisons(group, question, wp_number, outgoing_ls, wp_rows)
    _gen_work_programme(group, question, wp_number, work_item_details,
                        new_work_items, deleted_work_items, c_rows, wp_rows,
                        editors)
    _gen_candidate_work_items(group, question, wp_number, candidate_next,
                              wp_rows, work_item_details)
    _gen_planned_meetings(group, question, wp_number, rapporteur_meetings, wp_rows)
    _gen_annex_a(group, question, wp_number, c_rows, gen_rows, plen_rows, wp_rows)


# --- Section generators ---

def _gen_introduction(question_details, rapporteurs, agenda):
    """01.tex — introduction variables (questionTitle, leadership, agendaRef)."""
    leadership = " and ".join(rapporteurs) if rapporteurs else ""
    title = escape_latex(question_details.title or '')

    lines = [
        f"\\newcommand{{\\questionTitle}}{{{title}}}",
        f"\\newcommand{{\\leadership}}{{{leadership}}}",
        f"\\newcommand{{\\agendaRef}}{{{agenda}}}",
    ]
    write_result(RESULTS_DIR, "01.tex", "\n".join(lines) + "\n")


def _gen_executive_summary(group, question, c_rows, approval, determination,
                           consent, non_normative, work_items, new_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           wp_rows):
    """02.tex — executive summary variables (nbContributions, listQuestionContributions)."""
    # Build the itemize list
    items = []

    if approval:
        items.append(f"  \\item {len(approval)} Recommendations were finalized and "
                     f"proposed for TAP approval: {comma_separated_list(approval)}")
    if determination:
        items.append(f"  \\item {len(determination)} Recommendations were finalized and "
                     f"proposed for TAP determination: {comma_separated_list(determination)}")
    if consent:
        items.append(f"  \\item {len(consent)} Recommendations were finalized and "
                     f"proposed for AAP consent: {comma_separated_list(consent)}")
    if non_normative:
        items.append(f"  \\item {len(non_normative)} non-normative texts (e.g.\\ Supplements, "
                     f"Technical reports, etc.) were finalized and proposed for agreement: "
                     f"{comma_separated_list(non_normative)}")
    if len(work_items) == 1:
        items.append(f"  \\item {len(work_items)} work item was progressed: "
                     f"{comma_separated_list(work_items)}")
    elif len(work_items) > 1:
        items.append(f"  \\item {len(work_items)} work items were progressed: "
                     f"{comma_separated_list(work_items)}")
    if len(new_work_items) == 1:
        items.append(f"  \\item {len(new_work_items)} new work item was agreed to be started: "
                     f"{comma_separated_list(new_work_items)}")
    elif len(new_work_items) > 1:
        items.append(f"  \\item {len(new_work_items)} new work items were agreed to be started: "
                     f"{comma_separated_list(new_work_items)}")
    if len(candidate_next) == 1:
        items.append(f"  \\item {len(candidate_next)} was agreed as candidate for decision "
                     f"in next SG{group} meeting: {comma_separated_list(candidate_next)}")
    elif len(candidate_next) > 1:
        items.append(f"  \\item {len(candidate_next)} were agreed as candidates for decision "
                     f"in next SG{group} meeting: {comma_separated_list(candidate_next)}")

    if outgoing_ls:
        destinations = [get_liaison_destination(wp_rows, n) for n in outgoing_ls]
        destinations = [d for d in destinations if d]
        if len(outgoing_ls) == 1:
            items.append(f"  \\item {len(outgoing_ls)} outgoing liaison statement was agreed "
                         f"to be sent: {comma_separated_list(destinations)}")
        else:
            items.append(f"  \\item {len(outgoing_ls)} outgoing liaison statements were agreed "
                         f"to be sent: {comma_separated_list(destinations)}")

    if rapporteur_meetings:
        titles = [get_document_title(wp_rows, n) for n in rapporteur_meetings]
        titles = [t for t in titles if t]
        if len(rapporteur_meetings) == 1:
            items.append(f"  \\item {len(rapporteur_meetings)} interim meeting was planned "
                         f"before the next SG{group} meeting: {comma_separated_list(titles)}")
        else:
            items.append(f"  \\item {len(rapporteur_meetings)} interim meetings were planned "
                         f"before the next SG{group} meetings: {comma_separated_list(titles)}")

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

    write_result(RESULTS_DIR, "02.tex", "\n".join(lines) + "\n")


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

    # Email URLs
    reflector = f"t{period}sg{group}Q{question}@lists.itu.int"
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
        f"\\newcommand{{\\reflectorUrl}}{{\\url{{{URL}{reflector}}}}}",
        "",
        f"\\newcommand{{\\subUrl}}{{\\href{{{sub_url}}}{{subscription webpage}}}}",
        "",
        f"\\newcommand{{\\ifaUrl}}{{\\href{{{ifa_url}}}{{webpage}}}}",
    ]
    write_result(RESULTS_DIR, "03.tex", "\n".join(lines) + "\n")


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
            location = ""
            date = ""
            idx1 = report.title.rfind('(')
            if idx1 >= 0:
                idx2 = report.title.find(')', idx1)
                idx3 = report.title.find(',', idx1)
                if idx2 >= 0 and idx3 >= 0:
                    location = report.title[idx1 + 1:idx3]
                    date = report.title[idx3 + 1:idx2]
            content_lines.append(
                f"  \\item {date} ({location}) The report of this Rapporteur meeting, "
                f"which is found in (TD{report.number.value}/{wp_number}) was approved "
                f"at the WP{wp_number}/{group} held on \\textit{{DD MM YYYY}}"
            )
        content_lines.append("\\end{itemize}")
    else:
        content_lines.append("\\textit{No interim rapporteur meetings were held.}")

    lines = [
        "\\newcommand{\\interimReports}{",
        "\n".join(content_lines),
        "}",
    ]
    write_result(RESULTS_DIR, "04.tex", "\n".join(lines) + "\n")


def _gen_discussions(group, question, wp_number, work_items, c_rows, gen_rows,
                     plen_rows, wp_rows):
    """05-discussions subsection content files."""
    selected_rows = []

    # 05-01: Outgoing work items
    lines = []
    for i, wi in enumerate(work_items):
        lines.append(f"\\subsubsection{{Work Item {i + 1}: ({wi}):}}\n")
        idx = wi.find(' ')
        search_term = wi[:idx] if idx > 0 else wi
        for row in c_rows:
            if search_term.lower() in row.title.lower():
                selected_rows.append(row)
                lines.append(f"{td_href(row, 'C')}\n")
        lines.append(f"\\textit{{TODO: write the observation here}}\n")
    write_result(RESULTS_DIR, "05-discussions-work-items.tex", "\n".join(lines))

    # 05-02: New proposed work items
    lines = []
    num = 0
    for row in c_rows:
        if is_new_work_item(row.title):
            selected_rows.append(row)
            num += 1
            lines.append(f"\\subsubsection{{New Work Item {num}: ({escape_latex(row.title)}):}}\n")
            lines.append(f"{td_href(row, 'C')}\n")
            lines.append(f"\\textit{{TODO: write the observation here}}\n")
    write_result(RESULTS_DIR, "05-discussions-new-work-items.tex", "\n".join(lines))

    # 05-03: Other contributions
    lines = []
    for row in c_rows:
        if row not in selected_rows:
            lines.append(f"{td_href(row, 'C')}: {escape_latex(row.title)}\n")
    write_result(RESULTS_DIR, "05-discussions-other-contributions.tex", "\n".join(lines))

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
    write_result(RESULTS_DIR, "05-discussions-incoming-liaisons.tex", "\n".join(lines))

    # 05-05: Other TDs
    lines = []
    for row in plen_rows:
        if row not in selected_gen:
            lines.append(
                f"{make_href(URL + row.number.link, f'TD{row.number.value}{row.lastRev}/P')}: "
                f"{escape_latex(row.title)}\n"
            )
    for row in gen_rows:
        if row not in selected_gen:
            lines.append(
                f"{make_href(URL + row.number.link, f'TD{row.number.value}{row.lastRev}/G')}: "
                f"{escape_latex(row.title)}\n"
            )
    for row in wp_rows:
        if row not in selected_gen:
            lines.append(
                f"{make_href(URL + row.number.link, f'TD{row.number.value}{row.lastRev}/{wp_number}')}: "
                f"{escape_latex(row.title)}\n"
            )
    write_result(RESULTS_DIR, "05-discussions-other-tds.tex", "\n".join(lines))


def _gen_recommendation_table_rows(wp_rows, items, group, question, wp_number, has_a5=True, td_wi=None):
    """Generate table rows for recommendation tables (approval/determination/consent)."""
    td_wi = td_wi or {}
    lines = []
    for num, element in enumerate(items, 1):
        q_name, td, a5 = find_question_name_td_and_a5(wp_rows, element)
        if td is None:
            continue

        final_text = make_href(URL + td.number.link,
                               f"TD {td.number.value}{td.lastRev}/{wp_number}")
        a5_text = ""
        if a5 is not None:
            a5_text = make_href(URL + a5.number.link,
                                f"TD {a5.number.value}{a5.lastRev}/{wp_number}")

        if td.acronym:
            work_item = f"{td.recommendation}({td.acronym})"
        elif td.recommendation:
            work_item = td.recommendation
        else:
            work_item = td.acronym

        text_title = escape_latex(td.textTitle)

        # Fill version and equiv. num. from work programme data
        wp_wi = td_wi.get(element)
        version = escape_latex(wp_wi.version) if wp_wi and wp_wi.version else ""
        equiv_num = escape_latex(wp_wi.equivNum) if wp_wi and wp_wi.equivNum else ""

        # Removed # and Question columns
        if has_a5:
            lines.append(table_row_str([
                escape_latex(work_item), version, text_title,
                final_text, a5_text, equiv_num
            ]))
        else:
            lines.append(table_row_str([
                escape_latex(work_item), version, text_title, final_text
            ]))
    return "".join(lines)


def _gen_draft_recommendations(group, question, wp_number, wp_rows,
                               approval, determination, consent, non_normative,
                               work_items, td_to_work_item=None):
    """06-draft-recommendations table rows."""
    td_wi = td_to_work_item or {}

    # TAP approval
    rows = _gen_recommendation_table_rows(wp_rows, approval, group, question, wp_number, td_wi=td_wi)
    rows = rows if rows.strip() else "NONE"
    write_result(RESULTS_DIR, "06-draft-rec-approval.tex",
                 f"\\newcommand{{\\approval}}{{\n{rows}}}\n")

    # TAP determination
    rows = _gen_recommendation_table_rows(wp_rows, determination, group, question, wp_number, td_wi=td_wi)
    rows = rows if rows.strip() else "NONE"
    write_result(RESULTS_DIR, "06-draft-rec-determination.tex",
                 f"\\newcommand{{\\determination}}{{\n{rows}}}\n")

    # AAP consent
    rows = _gen_recommendation_table_rows(wp_rows, consent, group, question, wp_number, td_wi=td_wi)
    rows = rows if rows.strip() else "NONE"
    write_result(RESULTS_DIR, "06-draft-rec-consent.tex",
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
        work_item = ""
        for wi in work_items:
            idx = wi.find(' ')
            current = (wi[:idx] if idx > 0 else wi).replace('_', '.')
            if current.lower() in td.title.replace('_', '.').lower():
                work_item = current
                break

        # Use work programme data for version if available
        wp_wi = td_wi.get(element)
        version = escape_latex(wp_wi.version) if wp_wi and wp_wi.version else ""

        text_title = escape_latex(split_title(td.title)[3])

        # Removed # and Question columns
        lines.append(table_row_str([
            escape_latex(work_item), version, text_title, final_text
        ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "06-draft-rec-agreement.tex",
                 f"\\newcommand{{\\agreement}}{{\n{rows}}}\n")


def _gen_outgoing_liaisons(group, question, wp_number, outgoing_ls, wp_rows):
    """09-outgoing-liaison-statements table rows."""
    lines = []
    for num, element in enumerate(outgoing_ls, 1):
        q_name, td = find_td_by_number(wp_rows, element)
        title = ""
        td_name = ""
        action_to = ""
        info_to = ""
        if td:
            title = td.title
            action_to, info_to = _parse_liaison_destinations(title)
            td_name = make_href(URL + td.number.link,
                                f"TD{element}{td.lastRev}/{wp_number}")

        # Combine action_to and info_to in single column
        combined_dest = []
        if action_to:
            combined_dest.append(f"For action: {action_to}")
        if info_to:
            combined_dest.append(f"For info: {info_to}")
        destination = " / ".join(combined_dest) if combined_dest else ""

        # New columns: Question | Title | For information / For action to | Deadline | TD number
        lines.append(table_row_str([
            f"Q{question}/{group}",
            escape_latex(title),
            f"\\textit{{{escape_latex(destination)}}}",
            "",  # Deadline - manual entry
            td_name
        ]))

    # If no liaisons, output NONE instead of empty table
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "09-outgoing-liaisons.tex",
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
                        new_work_items, deleted_work_items, c_rows, wp_rows,
                        editors=None):
    """10-work-programme table rows (new, deleted, ongoing)."""
    editors = editors or {}

    # New work items
    lines = []
    for row in c_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)
            base_text = td_href(row, "C")
            # Removed # and Question columns: Work Item | Status | Title | Editor | Base Text | Equivalent | AAP
            lines.append(table_row_str([
                escape_latex(work_item), "New",
                escape_latex(text_title), "\\textit{manual}", base_text, "", ""
            ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "10-wp-new-work-items.tex",
                 f"\\newcommand{{\\newWorkItems}}{{\n{rows}}}\n")

    # Deleted work items
    lines = []
    for element in deleted_work_items:
        q_name, td = find_td_by_number(wp_rows, element)
        title = escape_latex(td.textTitle) if td else ""
        acronym = escape_latex(td.acronym) if td else ""
        # Removed # and Question columns: Acronym | Title | AAP
        lines.append(table_row_str([
            acronym, title, ""
        ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "10-wp-deleted-work-items.tex",
                 f"\\newcommand{{\\deletedWorkItems}}{{\n{rows}}}\n")

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
        td_name = ""
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

        # Get editor from editors dict
        editor = escape_latex(editors.get(name, ""))

        # New columns (removed # and Question): Work Item | Status | Title | Editor | Base Text | Equivalent | Target Date | Summary updated | AAP
        lines.append(table_row_str([
            escape_latex(name), escape_latex(status),
            escape_latex(title), editor, td_name, escape_latex(equiv),
            escape_latex(timing), "", escape_latex(aap)
        ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "10-wp-ongoing-work-items.tex",
                 f"\\newcommand{{\\ongoingWorkItems}}{{\n{rows}}}\n")


def _gen_candidate_work_items(group, question, wp_number, candidate_next,
                              wp_rows, work_item_details):
    """11-candidate-work-items table rows."""
    lines = []
    for element in candidate_next:
        # Try to find matching WP TD
        _, td = find_td_by_name(wp_rows, element)
        if td is None:
            alt = extract_alt_name(element)
            if alt:
                _, td = find_td_by_name(wp_rows, alt)

        title = ""
        td_name = ""
        status = ""
        equiv = ""
        if td:
            title = td.textTitle
            td_name = make_href(URL + td.number.link,
                                f"TD{td.number.value}{td.lastRev}/{wp_number}")

        # Fill status/title/equiv from work programme data
        for wi in work_item_details:
            if wi.workItem == element or extract_alt_name(wi.workItem) == element:
                status = wi.status or ""
                if not title:
                    title = wi.title or ""
                equiv = wi.equivNum or ""
                break

        # Removed # and Question columns: Acronym | Status | Title | Editor | Base Text | A.5 justification | Equivalent
        lines.append(table_row_str([
            escape_latex(str(element)), escape_latex(status),
            escape_latex(title), "", td_name, "", escape_latex(equiv)
        ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "11-candidate-work-items.tex",
                 f"\\newcommand{{\\candidateWorkItems}}{{\n{rows}}}\n")


def _gen_planned_meetings(group, question, wp_number, rapporteur_meetings, wp_rows):
    """12-planned-interim-meetings table rows."""
    lines = []
    for element in rapporteur_meetings:
        _, td = find_td_by_number(wp_rows, element)
        title = ""
        td_ref = ""
        if td:
            title = escape_latex(td.title)
            td_ref = make_href(URL + td.number.link,
                               f"TD{element}{td.lastRev}/{wp_number}")
        # Removed Question column: Date (time) | Place/Host | Terms of reference | Contact
        lines.append(table_row_str([
            "", "", title or td_ref, ""
        ]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "12-planned-meetings.tex",
                 f"\\newcommand{{\\plannedMeetings}}{{\n{rows}}}\n")


def _format_source(source_value, group):
    """Format source value, replacing ITU with 'ITU study group X' using non-breaking spaces."""
    # Replace "ITU" with "ITU~study~group~17" (non-breaking spaces)
    if source_value and "ITU" in source_value and "study" not in source_value.lower():
        return f"ITU~study~group~{group}"
    return source_value


def _gen_annex_a(group, question, wp_number, c_rows, gen_rows, plen_rows, wp_rows):
    """annex-a table rows (contributions, GEN, PLEN, WP)."""
    q_str = f"Q{question}/{group}"

    # Contributions
    lines = []
    for row in c_rows:
        name = make_href(URL + row.number.link, f"C{row.number.value}{row.lastRev}")
        source_text = _format_source(row.source.value, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-contributions.tex",
                 f"\\newcommand{{\\annexContributions}}{{\n{rows}}}\n")

    # GEN TDs
    lines = []
    for row in gen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/G")
        source_text = _format_source(row.source.value, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-gen.tex",
                 f"\\newcommand{{\\annexGen}}{{\n{rows}}}\n")

    # PLEN TDs
    lines = []
    for row in plen_rows:
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/P")
        source_text = _format_source(row.source.value, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-plen.tex",
                 f"\\newcommand{{\\annexPlen}}{{\n{rows}}}\n")

    # WP TDs
    lines = []
    for row in wp_rows:
        name = make_href(URL + row.number.link,
                         f"TD{row.number.value}{row.lastRev}/{wp_number}")
        source_text = _format_source(row.source.value, group)
        source = make_href(URL + row.source.link, source_text)
        lines.append(table_row_str([name, source, escape_latex(row.title), q_str]))
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
