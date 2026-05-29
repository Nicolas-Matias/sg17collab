#!/usr/bin/env python3
"""Generate LaTeX content files for an ITU-T Working Party report.

Usage:
    python generate_wp_report.py <config.json>

Reads a JSON configuration file, fetches data from the ITU website,
and generates LaTeX snippet files in ../wp_doc_template/chapters/variables/.
These snippets are included by the .tex templates in ../wp_doc_template/chapters/.
"""

import sys
import os

# Add script directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.config import load_wp_config
from common.itu_api import get_documents, get_question, get_study_group, get_working_party, get_work_programme, get_work_item_editors, get_next_sg_meeting
from common.utils import (
    comma_separated_list, find_td_by_name, find_td_by_number,
    find_question_name_td_and_a5, compare_stripped,
    is_new_work_item, get_rapporteurs, get_associate_rapporteurs,
    get_chairs, get_vice_chairs, get_meeting_reports,
    extract_alt_name, extract_new_work_item_info, detect_outgoing_liaisons,
    detect_processed_work_items, parse_timing, print_work_programme_summary,
)
from common.latex import (
    URL, escape_latex, make_href, write_result, table_row_str, seqsplit_text,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(PROJECT_DIR, 'wp_doc_template', 'chapters', 'variables')


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.json>")
        sys.exit(1)

    config = load_wp_config(sys.argv[1])
    group = config['group']
    wp_number = config['workingParty']
    place = config['place']
    start = config['start']
    start_string = config['startString']
    start_date = config['startDate']
    end = config['end']
    next_meeting = config['next_meeting']

    # ---------------------------------------------------------------
    # Fetch data from ITU website
    # ---------------------------------------------------------------
    print("Fetching study group structure...")
    sg_details = get_study_group(group=group, start=start_string)

    # Find questions under this WP
    questions = None
    working_party = None
    for wp in sg_details.workingParties:
        if wp.number == wp_number:
            working_party = wp
            questions = wp.questions
            break
    if working_party is None:
        print(f"Working party {wp_number} not found in study group {group}")
        sys.exit(1)

    print("Fetching working party details...")
    wp_details = get_working_party(
        group=group, working_party=wp_number,
        questions=questions, start=start_string
    )

    # Fetch details for each question
    question_numbers = []
    questions_details = []
    for q in questions:
        question_numbers.append(q.number)
        print(f"  Fetching Q{q.number}/{group}...")
        qd = get_question(group=group, question=q.number, start=start_date)
        questions_details.append(qd)

    # ---------------------------------------------------------------
    # Fetch documents
    # ---------------------------------------------------------------
    print("Fetching documents...")
    c_rows = get_documents(document_type="C", group=group, working_party=wp_number,
                           questions=question_numbers, start=start_date)
    plen_rows = get_documents(document_type="PLEN", group=group, working_party=wp_number,
                              questions=question_numbers, start=start_date)
    gen_rows = get_documents(document_type="GEN", group=group, working_party=wp_number,
                             questions=question_numbers, start=start_date)
    wp_rows = get_documents(document_type="WP", group=group, working_party=wp_number,
                            questions=question_numbers, start=start_date)

    # ---------------------------------------------------------------
    # Process work programme (scraped from ITU website)
    # ---------------------------------------------------------------
    print("Fetching work programme...")
    work_item_details = []
    for qn in question_numbers:
        print(f"  Fetching work programme for Q{qn}/{group}...")
        items = get_work_programme(
            group=group, question=qn, working_party=wp_number, start=start_string)
        work_item_details.extend(items)

    work_items = [wi.workItem for wi in work_item_details]

    print_work_programme_summary(work_item_details)

    print("Fetching work item editors...")
    editors = get_work_item_editors(work_item_details)

    approval = []
    determination = []
    consent = []
    non_normative = []
    candidate_next = []
    rapporteur_meetings = []
    new_work_items = []
    interim_meetings = []

    # Auto-detect approval/consent/determination/agreement from TD documentType
    # (parsed from TD title, e.g., "Approval - X.1234: Title")
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

        # Build td_to_work_item mapping
        work_item_name = row.recommendation or row.acronym
        if work_item_name:
            for wi in work_item_details:
                wi_name = wi.workItem or ""
                if wi_name and (work_item_name in wi_name or wi_name in work_item_name):
                    td_to_work_item[val] = wi
                    break

    # Auto-detect work items progressed (under study items with a TD)
    processed_work_items = detect_processed_work_items(work_item_details, wp_rows)

    # Auto-detect outgoing liaisons from GEN TDs (LS/O in title)
    outgoing_ls = detect_outgoing_liaisons(gen_rows)

    # Auto-detect candidate work items for next SG meeting
    # Criteria: "Under study" items with timing between end of current meeting and next_meeting
    from datetime import timedelta
    # Use next_meeting from config if provided, otherwise estimate 6 months out
    if next_meeting:
        next_meeting_date = next_meeting
    else:
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

    # Auto-detect rapporteur meetings from TDs
    for row in wp_rows:
        title_lower = (row.title or '').lower()
        if (('terms of reference' in title_lower or 'proposal' in title_lower
             or 'planned' in title_lower)
            and ('rapporteur' in title_lower or 'interim' in title_lower
                 or 'rgm' in title_lower)):
            val = row.number.value.strip()
            if val and val not in rapporteur_meetings:
                rapporteur_meetings.append(val)

    # Scrape next SG meeting info from ITU website
    print(f"\nFetching next SG{group} meeting info...")
    next_sg_meeting = get_next_sg_meeting(group, after_date=start)
    if next_sg_meeting:
        print(f"  Next SG{group} meeting: {next_sg_meeting['city']}, "
              f"{next_sg_meeting['date_range']}")
    else:
        print(f"  Warning: could not find next SG{group} meeting on ITU website")

    # Find agenda and report TDs
    agenda_title = f"Agenda of WP{wp_number}/{group}"
    report_title = f"Report of WP{wp_number}/{group}"
    agenda = ""
    agenda_td_number = ""
    report = ""
    report_number = ''

    for row in wp_rows:
        title_lower = (row.title or "").lower().strip()
        if compare_stripped(row.title, agenda_title) or \
           (f"agenda" in title_lower and f"wp{wp_number}" in title_lower.replace(' ', '')):
            agenda_td_number = f"TD{row.number.value.replace(' ', '')}"
            agenda = make_href(URL + row.number.link,
                               f"TD{row.number.value}{row.lastRev}")
            break
    for row in wp_rows:
        if compare_stripped(row.title, report_title):
            report_number = row.number.value.replace(' ', '')
            report = make_href(URL + row.number.link,
                               f"TD{row.number.value}{row.lastRev}")
            break

    chairs = get_chairs(wp_details)
    vice_chairs = get_vice_chairs(wp_details)

    year = int(start_date[2:4])
    period = str(int(year / 4) * 4 + 1)

    # ---------------------------------------------------------------
    # Generate LaTeX snippets
    # ---------------------------------------------------------------
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"\nGenerating LaTeX snippets to {RESULTS_DIR}/")

    # Sessions and meeting_days are optional - use None as default for manual entry
    sessions = None
    meeting_days = []

    # --- Variables ---
    _generate_variables(group, wp_number, question_numbers, place, start,
                        end, start_string, start_date, period, chairs, vice_chairs,
                        report_number, working_party, questions_details)

    # --- Frontmatter contacts ---
    _generate_frontmatter_contacts(wp_details, wp_number)

    # --- Report sections ---
    _gen_introduction(group, wp_number, place, start, end, chairs, vice_chairs,
                       agenda, agenda_td_number, sessions, meeting_days)
    _gen_executive_summary(group, wp_number, approval, determination, consent,
                           non_normative, processed_work_items, outgoing_ls)
    _gen_structure_leadership(group, wp_number, chairs, vice_chairs,
                              question_numbers, questions_details)
    _gen_documentation(group, wp_number, question_numbers, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows)
    _gen_opening_plenary(group, wp_number, question_numbers, wp_rows)
    _gen_opening_plenary_issues(group, wp_number, question_numbers,
                                wp_rows, plen_rows, gen_rows)
    _gen_appointments(group, wp_number, question_numbers, questions_details)
    _gen_question_meetings(group, wp_number, question_numbers, wp_rows, c_rows,
                           gen_rows, work_item_details)
    _gen_draft_recommendations(group, wp_number, wp_rows, approval, determination,
                               consent, non_normative,
                               td_to_work_item=td_to_work_item)
    _gen_outgoing_liaisons(group, wp_number, question_numbers, outgoing_ls, gen_rows)
    _gen_work_programme(group, wp_number, question_numbers, work_items,
                        work_item_details, new_work_items,
                        wp_rows, editors=editors)
    _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors=editors)
    _gen_planned_meetings(group, wp_number, question_numbers, questions,
                          rapporteur_meetings, wp_rows)
    _gen_scheduled_meetings(group, wp_number, interim_meetings, next_sg_meeting)
    _gen_ipr(group, wp_number, wp_rows)
    _gen_conclusion(group, wp_number, chairs, sg_roles=wp_details.sg_roles)
    _gen_annex_a_docs(group, wp_number, c_rows, gen_rows, plen_rows, wp_rows)
    _gen_annex_b_reflectors(group, question_numbers)
    _gen_annex_c_new_work_items(wp_number, wp_rows)

    print("\nDone.")


# ===================================================================
# Variables
# ===================================================================

def _format_date_range(start_dt, end_dt):
    """Format date range as 'D - D Month YYYY' or 'D Month - D Month YYYY'.

    Examples:
      Same month:  3 - 11 December 2025
      Cross-month: 28 November - 5 December 2025
    """
    if end_dt is None:
        return f"{start_dt.day} {start_dt.strftime('%B')} {start_dt.year}"
    if start_dt.month == end_dt.month and start_dt.year == end_dt.year:
        return (f"{start_dt.day} - {end_dt.day} "
                f"{end_dt.strftime('%B')} {end_dt.year}")
    return (f"{start_dt.day} {start_dt.strftime('%B')} - "
            f"{end_dt.day} {end_dt.strftime('%B')} {end_dt.year}")


def _generate_variables(group, wp_number, question_numbers, place, start,
                        end, start_string, start_date, period, chairs, vice_chairs,
                        report_number, working_party, questions_details):
    """Generate results/variables.tex with LaTeX macro definitions."""
    year = int(start_date[0:4])
    first_year = int(year / 4) * 4 + 1
    last_year = first_year + 3

    q_list = ", ".join(f"{qn}/{group}" for qn in question_numbers)
    leadership = " and ".join(chairs) if chairs else ""

    # Date range: "3 - 11 December 2025"
    occurence = _format_date_range(start, end)

    # Abstract: include WP title and question titles
    wp_title = working_party.title if working_party and working_party.title else ""
    q_parts = []
    for idx, qn in enumerate(question_numbers):
        qd = questions_details[idx] if idx < len(questions_details) else None
        q_title = qd.title if qd and qd.title else ""
        q_parts.append(f"Q{qn}/{group} ({q_title})" if q_title else f"Q{qn}/{group}")

    if len(q_parts) > 1:
        q_enum = ", ".join(q_parts[:-1]) + ", and " + q_parts[-1]
    elif q_parts:
        q_enum = q_parts[0]
    else:
        q_enum = ""

    wp_desc = f"WP{wp_number}/{group}"
    if wp_title:
        wp_desc = f"WP{wp_number}/{group} ({escape_latex(wp_title)})"
    abstract = f"This is a report of {wp_desc}. The {wp_desc} consists of {q_enum}."

    lines = [
        f"\\newcommand{{\\studyGroup}}{{{group}}}",
        f"\\newcommand{{\\workingParty}}{{{wp_number}}}",
        f"\\newcommand{{\\questions}}{{{q_list}}}",
        f"\\newcommand{{\\place}}{{{place}}}",
        f"\\newcommand{{\\occurence}}{{{occurence}}}",
        f"\\newcommand{{\\startDate}}{{{start_string}}}",
        f"\\newcommand{{\\studyPeriod}}{{{first_year}-{last_year}}}",
        f"\\newcommand{{\\period}}{{{period}}}",
        f"\\newcommand{{\\leadership}}{{{leadership}}}",
        f"\\newcommand{{\\reportNumber}}{{{report_number}}}",
        f"\\newcommand{{\\tdNumber}}{{}}",  # TD number assigned by secretariat — fill in manually
        f"\\newcommand{{\\abstr}}{{{abstract}}}",
    ]
    write_result(RESULTS_DIR, "00-variables.tex", "\n".join(lines) + "\n")


def _generate_frontmatter_contacts(wp_details, wp_number):
    """Generate results/frontmatter-contacts.tex with contact longtable rows."""
    lines = []
    for role in wp_details.roles:
        if role.roleName not in ("Chair", "Co-Chair", "Vice-chair"):
            continue
        name = f"{role.firstName} {role.lastName}".strip()
        country = escape_latex(role.address)
        title_line = f"WP{wp_number} {role.roleName}"
        contact_info = []
        if role.tel:
            contact_info.append(f"Tel: {escape_latex(role.tel)}")
        if role.email:
            contact_info.append(f"Email: \\ul{{{escape_latex(role.email)}}}")

        lines.append("\\begin{longtable}{p{0.15\\linewidth} p{0.30\\linewidth} p{0.50\\linewidth}}")
        lines.append("\\midrule")
        lines.append(
            f"\\textbf{{Contact:}} &\n"
            f"{escape_latex(name)}\\newline\n"
            f"{country}\\newline\n"
            f"{escape_latex(title_line)} &\n"
            f"{' \\newline '.join(contact_info)} \\\\")
        lines.append("\\midrule")
        lines.append("\\end{longtable}")
        lines.append("")

    write_result(RESULTS_DIR, "00-frontmatter-contacts.tex", "\n".join(lines))


# ===================================================================
# Section generators
# ===================================================================

def _gen_introduction(group, wp_number, place, start, end, chairs, vice_chairs,
                      agenda, agenda_td_number, sessions, meeting_days):
    """01-introduction variables."""
    # Chair string
    chair_str = escape_latex(" and ".join(chairs)) if chairs else ""

    # Vice-chairs / assisted by
    if vice_chairs:
        assisted_by = ", assisted by " + escape_latex(", ".join(vice_chairs))
    else:
        assisted_by = ""

    # Sessions count
    if sessions is not None:
        sessions_str = str(sessions)
    else:
        sessions_str = "\\textit{number}"

    # Meeting days
    if meeting_days:
        def _format_day(dt):
            day = dt.day
            if 11 <= day <= 13:
                suffix = "th"
            elif day % 10 == 1:
                suffix = "st"
            elif day % 10 == 2:
                suffix = "nd"
            elif day % 10 == 3:
                suffix = "rd"
            else:
                suffix = "th"
            return f"{dt.strftime('%B')} {day}{suffix} {dt.year}"
        day_strs = [_format_day(d) for d in meeting_days]
        if len(day_strs) == 1:
            days_str = day_strs[0]
        elif len(day_strs) == 2:
            days_str = f"{day_strs[0]} and {day_strs[1]}"
        else:
            days_str = ", ".join(day_strs[:-1]) + f", and {day_strs[-1]}"
    else:
        days_str = "\\textit{days}"

    # Agenda reference
    if agenda:
        agenda_ref = agenda
    elif agenda_td_number:
        agenda_ref = agenda_td_number
    else:
        agenda_ref = "\\textit{agenda TD}"

    lines = [
        f"\\newcommand{{\\wpChairs}}{{{chair_str}}}",
        f"\\newcommand{{\\assistedBy}}{{{assisted_by}}}",
        f"\\newcommand{{\\sessionsCount}}{{{sessions_str}}}",
        f"\\newcommand{{\\meetingDays}}{{{days_str}}}",
        f"\\newcommand{{\\agendaRef}}{{{agenda_ref}}}",
    ]
    write_result(RESULTS_DIR, "01-introduction.tex", "\n".join(lines) + "\n")


def _gen_executive_summary(group, wp_number, approval, determination, consent,
                           non_normative, processed_work_items, outgoing_ls):
    """02-executive-summary content."""
    lines = [
        f"During this SG{group} meeting, WP{wp_number}/{group} achieved the following results:\n",
        "\\begin{itemize}",
        f"  \\item Recommendations finalized and proposed for TAP Approval: {len(approval)}",
        f"  \\item Recommendations finalized and proposed for TAP Consent: {len(consent)}",
        f"  \\item Recommendations finalized and proposed for TAP Determination: {len(determination)}",
        f"  \\item Recommendations finalized and proposed for TAP Agreement: {len(non_normative)}",
        f"  \\item Work items progressed: {len(processed_work_items)}",
        f"  \\item Outgoing liaison statements agreed: {len(outgoing_ls)}",
        "\\end{itemize}",
    ]

    write_result(RESULTS_DIR, "02-executive-summary-content.tex", "\n".join(lines))


def _gen_structure_leadership(group, wp_number, chairs, vice_chairs,
                              question_numbers, questions_details):
    """03-wp-structure-and-leadership content."""
    lines = [
        f"WP{wp_number}/{group} Management team\n",
        "\\begin{itemize}",
    ]
    if len(chairs) == 1:
        lines.append(f"  \\item Chair: {escape_latex(chairs[0])}")
    else:
        for ch in chairs:
            lines.append(f"  \\item Co-chair: {escape_latex(ch)}")
    for vc in vice_chairs:
        lines.append(f"  \\item Vice-chair: {escape_latex(vc)}")
    lines.append("\\end{itemize}\n")

    lines.append(f"The following table reproduces the current list of WP{wp_number}/{group} "
                 f"Questions and related Rapporteurs\n")

    # Question/rapporteur table rows
    table_lines = []
    for idx, qn in enumerate(question_numbers):
        qd = questions_details[idx]
        rapps = get_rapporteurs(qd)
        assoc_rapps = get_associate_rapporteurs(qd)
        n_lines = max(1, len(rapps), len(assoc_rapps))

        for i in range(n_lines):
            q_name = f"Q{qn}/{group}" if i == 0 else ""
            q_title = escape_latex(qd.title or '') if i == 0 else ""
            rapp = escape_latex(rapps[i]) if i < len(rapps) else ""
            assoc = escape_latex(assoc_rapps[i]) if i < len(assoc_rapps) else ""
            table_lines.append(table_row_str([q_name, q_title, rapp, assoc]))

    lines.append("")  # separator
    write_result(RESULTS_DIR, "03-structure-leadership.tex", "\n".join(lines))
    rows = "".join(table_lines)
    write_result(RESULTS_DIR, "03-structure-questions-table.tex",
                 f"\\newcommand{{\\questionsTable}}{{\n{rows}}}\n")


def _gen_documentation(group, wp_number, question_numbers, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows):
    """04-documentation-and-email-lists content."""
    lines = [f"The following documents were discussed by WP{wp_number}/{group} Questions:\n"]

    for qn in question_numbers:
        q_name = f"Q{qn}/{group}"
        lines.append(f"\\textbf{{{q_name}:}}\n")
        lines.append("\\begin{itemize}")

        # Contributions for this question
        c_links = ", ".join(
            make_href(URL + r.number.link, f"C{r.number.value}{r.lastRev}")
            for r in reversed(c_rows)
            if any(rq.value == q_name for rq in r.questions)
        )
        lines.append(f"  \\item C: {c_links}")

        # TDs for this question (GEN + PLEN + WP)
        td_links = []
        for r in reversed(gen_rows):
            if any(rq.value == q_name for rq in r.questions):
                td_links.append(make_href(URL + r.number.link,
                                          f"TD{r.number.value}{r.lastRev}"))
        for r in reversed(plen_rows):
            if any(rq.value == q_name for rq in r.questions):
                td_links.append(make_href(URL + r.number.link,
                                          f"TD{r.number.value}{r.lastRev}"))
        for r in reversed(wp_rows):
            if any(rq.value == q_name for rq in r.questions):
                td_links.append(make_href(URL + r.number.link,
                                          f"TD{r.number.value}{r.lastRev}"))
        lines.append(f"  \\item TD: {', '.join(td_links)}")
        lines.append("\\end{itemize}\n")

    doc_url = f"{URL}/md/T{period}-SG{group}-{start_date[2:]}/sum/en"
    lines.append(f"The complete documentation for this SG{group} meeting is to be found at:\n")
    lines.append(f"\\href{{{doc_url}}}{{{doc_url}}}\n")

    write_result(RESULTS_DIR, "04-documentation-links.tex", "\n".join(lines))

    # Email info
    year = int(start_date[0:4])
    first_year = int(year / 4) * 4 + 1
    last_year = first_year + 3
    ifa_url = f"{URL}/en/ITU-T/studygroups/{first_year}-{last_year}/{group}/Pages/ifa-structure.aspx"
    sub_url = f"{URL}/net4/iwm?p0=0&p11=ITU&p12=ITU-SEP-ITU-T-SEP-SP%2017-SEP-Study%20Group%2017&p21=ITU&p22=ITU"

    email_lines = [
        f"E-mail correspondences pertaining to the activities of this working party and "
        f"Questions under this working party are routinely conducted using the e-mail reflectors. "
        f"For more information on available e-mail reflectors and informal FTP areas, please visit "
        f"the dedicated \\href{{{URL}{ifa_url}}}{{webpage}}.\n",
        f"Those wishing to subscribe or unsubscribe to SG{group} email reflectors, "
        f"please visit \\href{{{sub_url}}}{{subscription webpage}}.\n",
    ]
    write_result(RESULTS_DIR, "04-email-info.tex", "\n".join(email_lines))


def _gen_opening_plenary(group, wp_number, question_numbers, wp_rows):
    """05-opening-plenary-results content (interim meeting reports table)."""
    lines = []
    total_reports = 0
    for qn in question_numbers:
        reports = get_meeting_reports(wp_rows, qn, group)
        total_reports += len(reports)

    if total_reports > 0:
        table_lines = []
        for qn in question_numbers:
            q_name = f"Q{qn}/{group}"
            meeting_name = f"{q_name} Rapporteur meeting"
            reports = get_meeting_reports(wp_rows, qn, group)
            for report in reports:
                location = ""
                date = ""
                idx1 = report.title.rfind('(')
                if idx1 >= 0:
                    idx2 = report.title.find(')', idx1)
                    idx3 = report.title.find(',', idx1)
                    if idx2 >= 0 and idx3 >= 0:
                        location = report.title[idx1 + 1:idx3]
                        date = report.title[idx3 + 1:idx2]
                td_link = make_href(URL + report.number.link,
                                    f"TD{report.number.value}/{wp_number}")
                table_lines.append(table_row_str([
                    q_name, meeting_name, f"{location}, {date}", td_link
                ]))
        rows = "".join(table_lines)
        write_result(RESULTS_DIR, "05-opening-plenary-reports.tex",
                     f"\\newcommand{{\\openingPlenaryReports}}{{\n{rows}}}\n")
    else:
        write_result(RESULTS_DIR, "05-opening-plenary-reports.tex",
                     "\\newcommand{\\openingPlenaryReports}{}\n")


def _gen_opening_plenary_issues(group, wp_number, question_numbers,
                                wp_rows, plen_rows, gen_rows):
    """05-opening-plenary — Section 5.2: other issues discussed at opening plenary."""
    all_rows = list(wp_rows) + list(plen_rows) + list(gen_rows)

    # Categorise TDs by topic
    incoming_ls = []
    workshops = []
    tutorials = []
    joint_sessions = []

    for row in all_rows:
        title_lower = (row.title or "").lower()
        if ("ls from" in title_lower or "liaison statement from" in title_lower
                or "incoming liaison" in title_lower):
            incoming_ls.append(row)
        if "workshop" in title_lower:
            workshops.append(row)
        if "tutorial" in title_lower:
            tutorials.append(row)
        if "joint session" in title_lower or "joint meeting" in title_lower:
            joint_sessions.append(row)

    lines = []

    if incoming_ls:
        lines.append("\\textbf{Review of incoming liaison statements:}\n")
        lines.append("\\begin{itemize}")
        for row in incoming_ls:
            td_link = make_href(URL + row.number.link,
                                f"TD{row.number.value}{row.lastRev}")
            title = escape_latex(row.title or "")
            lines.append(f"  \\item {td_link}: {title}")
        lines.append("\\end{itemize}\n")

    if workshops:
        lines.append("\\textbf{Workshops:}\n")
        lines.append("\\begin{itemize}")
        for row in workshops:
            td_link = make_href(URL + row.number.link,
                                f"TD{row.number.value}{row.lastRev}")
            title = escape_latex(row.title or "")
            lines.append(f"  \\item {td_link}: {title}")
        lines.append("\\end{itemize}\n")

    if tutorials:
        lines.append("\\textbf{Tutorials:}\n")
        lines.append("\\begin{itemize}")
        for row in tutorials:
            td_link = make_href(URL + row.number.link,
                                f"TD{row.number.value}{row.lastRev}")
            title = escape_latex(row.title or "")
            lines.append(f"  \\item {td_link}: {title}")
        lines.append("\\end{itemize}\n")

    if joint_sessions:
        lines.append("\\textbf{Joint sessions:}\n")
        lines.append("\\begin{itemize}")
        for row in joint_sessions:
            td_link = make_href(URL + row.number.link,
                                f"TD{row.number.value}{row.lastRev}")
            title = escape_latex(row.title or "")
            lines.append(f"  \\item {td_link}: {title}")
        lines.append("\\end{itemize}\n")

    content = "\n".join(lines) if lines else ""
    write_result(RESULTS_DIR, "05-opening-plenary-issues.tex",
                 f"\\newcommand{{\\openingPlenaryIssues}}{{\n{content}}}\n")


def _gen_appointments(group, wp_number, question_numbers, questions_details):
    """06-appointments — current rapporteurs and officers."""
    lines = []
    lines.append(f"Current list of Rapporteurs, Associate Rapporteurs and "
                 f"Liaison Officers for WP{wp_number}/{group}:\n")
    lines.append("\\begin{itemize}")

    for idx, qn in enumerate(question_numbers):
        qd = questions_details[idx] if idx < len(questions_details) else None
        if not qd:
            continue
        q_name = f"Q{qn}/{group}"
        rapps = get_rapporteurs(qd)
        assoc_rapps = get_associate_rapporteurs(qd)
        # Extract liaison officers from question roles
        liaison_officers = [
            f"{role.firstName} {role.lastName} ({role.company}, {role.address})"
            for role in qd.roles
            if role.roleName and "liaison" in role.roleName.lower()
        ]

        parts = []
        if rapps:
            rapp_label = "Rapporteur" if len(rapps) == 1 else "Co-rapporteurs"
            parts.append(f"{rapp_label}: {', '.join(rapps)}")
        if assoc_rapps:
            parts.append(f"Associate Rapporteur{'s' if len(assoc_rapps) > 1 else ''}: "
                         f"{', '.join(assoc_rapps)}")
        if liaison_officers:
            parts.append(f"Liaison Officer{'s' if len(liaison_officers) > 1 else ''}: "
                         f"{', '.join(liaison_officers)}")

        if parts:
            detail = "; ".join(parts)
            lines.append(f"  \\item \\textbf{{{q_name}}}: {detail}")
        else:
            lines.append(f"  \\item \\textbf{{{q_name}}}: (no roles found)")

    lines.append("\\end{itemize}\n")

    content = "\n".join(lines)
    write_result(RESULTS_DIR, "06-appointments.tex",
                 f"\\newcommand{{\\openingPlenaryAppointments}}{{\n{content}}}\n")


def _gen_question_meetings(group, wp_number, question_numbers, wp_rows, c_rows,
                           gen_rows, work_item_details):
    """07-questions-meetings content — per-question executive summaries.

    Generates the same format as Question Report Part 2 for each question.
    """
    lines = []

    for qn in question_numbers:
        q_name = f"Q{qn}/{group}"
        lines.append(f"\\subsection{{Question {qn}/{group}}}\n")

        # Find question report TD
        q_report_title = f"Report of Q{qn}/{group}"
        q_report = ""
        for row in wp_rows:
            if compare_stripped(row.title, q_report_title):
                q_report = make_href(URL + row.number.link,
                                     f"TD{row.number.value}{row.lastRev}")
                break
        if q_report:
            lines.append(f"The report of Q{qn}/{group} can be found in {q_report}. It was approved.\n")

        # Count contributions for this question
        q_contributions = [r for r in c_rows
                           if any(rq.value == q_name for rq in r.questions)]

        # Filter WP TDs for this question
        q_wp_rows = [r for r in wp_rows if any(rq.value == q_name for rq in r.questions)]

        # Filter GEN TDs for this question
        q_gen_rows = [r for r in gen_rows if any(rq.value == q_name for rq in r.questions)]

        # Detect approval/consent/determination/agreement from documentType (same as Question Report)
        q_approval = []
        q_determination = []
        q_consent = []
        q_agreement = []
        for row in q_wp_rows:
            val = row.number.value.strip()
            if row.documentType == 'Approval':
                if val not in q_approval:
                    q_approval.append(val)
            elif row.documentType == 'Determination':
                if val not in q_determination:
                    q_determination.append(val)
            elif row.documentType == 'Consent':
                if val not in q_consent:
                    q_consent.append(val)
            elif row.documentType == 'Agreement':
                if val not in q_agreement:
                    q_agreement.append(val)

        # Work items progressed (under study items with a TD)
        q_work_item_details = [wi for wi in work_item_details
                               if wi.question and str(wi.question) == str(qn)]
        q_processed = detect_processed_work_items(q_work_item_details, q_wp_rows)

        # Outgoing liaison statements from GEN TDs (LS/O in title)
        q_outgoing_ls = detect_outgoing_liaisons(q_gen_rows)

        # Build executive summary
        lines.append(f"During this SG{group} meeting, {q_name} received "
                     f"{len(q_contributions)} contribution{'s' if len(q_contributions) != 1 else ''} "
                     f"and achieved the following results:\n")

        # Helper to make TD links
        def _make_td_links(td_numbers, rows, suffix=""):
            links = []
            for n in td_numbers:
                td = None
                for row in rows:
                    if row.number.value.strip() == str(n).strip():
                        td = row
                        break
                if td:
                    links.append(make_href(URL + td.number.link, f"TD {n}{suffix}"))
                else:
                    links.append(f"TD {n}{suffix}")
            return links

        items = []

        # Approval - always show, "None" if empty
        if q_approval:
            links = _make_td_links(q_approval, q_wp_rows)
            items.append(f"  \\item Recommendations finalized and proposed for TAP Approval: "
                         f"{comma_separated_list(links)}")
        else:
            items.append(f"  \\item Recommendations finalized and proposed for TAP Approval: None")

        # Consent - always show, "None" if empty
        if q_consent:
            links = _make_td_links(q_consent, q_wp_rows)
            items.append(f"  \\item Recommendations finalized and proposed for TAP Consent: "
                         f"{comma_separated_list(links)}")
        else:
            items.append(f"  \\item Recommendations finalized and proposed for TAP Consent: None")

        # Determination - always show, "None" if empty
        if q_determination:
            links = _make_td_links(q_determination, q_wp_rows)
            items.append(f"  \\item Recommendations finalized and proposed for TAP Determination: "
                         f"{comma_separated_list(links)}")
        else:
            items.append(f"  \\item Recommendations finalized and proposed for TAP Determination: None")

        # Agreement - always show, "None" if empty
        if q_agreement:
            links = _make_td_links(q_agreement, q_wp_rows)
            items.append(f"  \\item Recommendations finalized and proposed for TAP Agreement: "
                         f"{comma_separated_list(links)}")
        else:
            items.append(f"  \\item Recommendations finalized and proposed for TAP Agreement: None")

        # Work items progressed - always show, "None" if empty
        if q_processed:
            td_links = [make_href(URL + td.number.link, f"TD {td_num}")
                        for _, td_num, td in q_processed]
            items.append(f"  \\item Work items progressed: {comma_separated_list(td_links)}")
        else:
            items.append(f"  \\item Work items progressed: None")

        # Outgoing liaison statements - always show, "None" if empty
        if q_outgoing_ls:
            links = _make_td_links(q_outgoing_ls, q_gen_rows, "/G")
            items.append(f"  \\item Outgoing liaison statements agreed: {comma_separated_list(links)}")
        else:
            items.append(f"  \\item Outgoing liaison statements agreed: None")

        lines.append("\\begin{itemize}")
        lines.extend(items)
        lines.append("\\end{itemize}\n")

    write_result(RESULTS_DIR, "07-question-meetings.tex", "\n".join(lines))


def _gen_draft_recommendations(group, wp_number, wp_rows, approval, determination,
                               consent, non_normative,
                               td_to_work_item=None):
    """08-draft-recommendations and 09-agreement table rows."""
    td_wi = td_to_work_item or {}

    def _gen_table(items, has_a5=True):
        lines = []
        for element in items:
            q_name, td, a5 = find_question_name_td_and_a5(wp_rows, element)
            final_text = "no update"
            if td:
                final_text = make_href(URL + td.number.link,
                                       f"TD {td.number.value}{td.lastRev}/{wp_number}")
            a5_text = ""
            if a5:
                a5_text = make_href(URL + a5.number.link,
                                    f"TD {a5.number.value}{a5.lastRev}/{wp_number}")

            # Get work item name and version from work programme
            wp_wi = td_wi.get(element.strip())
            if wp_wi and wp_wi.workItem:
                work_item = wp_wi.workItem
            elif td and td.acronym:
                work_item = f"{td.recommendation}({td.acronym})"
            elif td and td.recommendation:
                work_item = td.recommendation
            elif td:
                work_item = td.acronym
            else:
                work_item = ""

            version = escape_latex(wp_wi.version) if wp_wi and wp_wi.version else ""
            text_title = escape_latex(td.textTitle) if td else ""
            equiv_num = escape_latex(wp_wi.equivNum) if wp_wi and wp_wi.equivNum else ""

            # Columns: Question | Work Item | Version | Title | Final Text | A.5 | Equivalent
            if has_a5:
                lines.append(table_row_str([
                    q_name, seqsplit_text(work_item), version,
                    text_title, final_text, a5_text, equiv_num
                ]))
            else:
                # Agreement: Question | Work Item | Version | Title | Final Text
                lines.append(table_row_str([
                    q_name, seqsplit_text(work_item), version,
                    text_title, final_text
                ]))
        return "".join(lines)

    # Approval
    rows = _gen_table(approval)
    has_approval = "true" if approval else "false"
    write_result(RESULTS_DIR, "08-draft-rec-approval.tex",
                 f"\\newcommand{{\\hasWpApproval}}{{{has_approval}}}\n"
                 f"\\newcommand{{\\wpApproval}}{{\n{rows}}}\n")

    # Determination
    rows = _gen_table(determination)
    has_determination = "true" if determination else "false"
    write_result(RESULTS_DIR, "08-draft-rec-determination.tex",
                 f"\\newcommand{{\\hasWpDetermination}}{{{has_determination}}}\n"
                 f"\\newcommand{{\\wpDetermination}}{{\n{rows}}}\n")

    # Consent
    rows = _gen_table(consent)
    has_consent = "true" if consent else "false"
    write_result(RESULTS_DIR, "08-draft-rec-consent.tex",
                 f"\\newcommand{{\\hasWpConsent}}{{{has_consent}}}\n"
                 f"\\newcommand{{\\wpConsent}}{{\n{rows}}}\n")

    # Agreement (no A.5 column)
    rows = _gen_table(non_normative, has_a5=False)
    has_agreement = "true" if non_normative else "false"
    write_result(RESULTS_DIR, "09-agreement.tex",
                 f"\\newcommand{{\\hasWpAgreement}}{{{has_agreement}}}\n"
                 f"\\newcommand{{\\wpAgreement}}{{\n{rows}}}\n")


def _gen_outgoing_liaisons(group, wp_number, question_numbers, outgoing_ls, gen_rows):
    """10-outgoing-liaison-statements table rows."""
    lines = []
    for element in outgoing_ls:
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
            # Get question from TD
            if td.questions:
                q_name = td.questions[0].value if td.questions else ""

        # Combine action_to and info_to in single column (without prefixes)
        combined_dest = []
        if action_to:
            combined_dest.append(escape_latex(action_to))
        if info_to:
            combined_dest.append(escape_latex(info_to))
        destination = " / ".join(combined_dest) if combined_dest else "\\textit{(manual entry)}"

        # Columns: Question | Title | For info/action to | TD number
        lines.append(table_row_str([
            q_name,
            escape_latex(title),
            destination,
            td_name
        ]))
    rows = "".join(lines)
    has_outgoing = "true" if outgoing_ls else "false"
    write_result(RESULTS_DIR, "10-outgoing-liaisons.tex",
                 f"\\newcommand{{\\hasWpOutgoingLiaisons}}{{{has_outgoing}}}\n"
                 f"\\newcommand{{\\wpOutgoingLiaisons}}{{\n{rows}}}\n")


def _gen_work_programme(group, wp_number, question_numbers, work_items,
                        work_item_details, new_work_items,
                        wp_rows, editors=None):
    """11-work-programme table rows (new, deleted, ongoing)."""
    editors = editors or {}

    def _lookup_editor(name):
        """Look up editor by work item name, trying multiple fallback strategies."""
        if not name:
            return ""
        editor = editors.get(name, "")
        if editor:
            return editor

        # Strategy 1: try alt name from "(ex ...)" pattern
        alt = extract_alt_name(name)
        if alt:
            editor = editors.get(alt, "")
            if editor:
                return editor

        # Strategy 2: strip "for new work item " prefix
        stripped = name
        if stripped.lower().startswith('for new work item '):
            stripped = stripped[len('for new work item '):].strip()
            editor = editors.get(stripped, "")
            if editor:
                return editor

        # Strategy 3: try TR. <-> XSTR. prefix swap
        if stripped.startswith('TR.'):
            editor = editors.get('XSTR.' + stripped[3:], "")
            if editor:
                return editor
        elif stripped.startswith('XSTR.'):
            editor = editors.get('TR.' + stripped[5:], "")
            if editor:
                return editor

        # Strategy 4: extract base name and search editors dict for partial match
        base = stripped.split('(')[0].strip().split(',')[0].strip()
        if base and base != stripped:
            editor = editors.get(base, "")
            if editor:
                return editor
            for key in editors:
                key_alt = extract_alt_name(key)
                if key_alt and key_alt.lower() == base.lower():
                    return editors[key]

        return ""

    # New work items from WP TDs (look for "new work item" or "NWI" in title)
    lines = []
    for row in wp_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)
            if not work_item:
                continue

            q_name = row.questions[0].value if row.questions else ""
            td_link = make_href(URL + row.number.link,
                                f"TD {row.number.value.replace(' ', '')}/{wp_number}")

            # Columns: Question | Work Item | Status | Title | Editor | Base Text | Equivalent | Approval process
            lines.append(table_row_str([
                q_name, seqsplit_text(work_item), "New",
                escape_latex(text_title), "(manual entry)",
                td_link, "", ""
            ]))
    rows = "".join(lines)
    has_new = "true" if lines else "false"
    write_result(RESULTS_DIR, "11-wp-new-work-items.tex",
                 f"\\newcommand{{\\hasWpNewWorkItems}}{{{has_new}}}\n"
                 f"\\newcommand{{\\wpNewWorkItems}}{{\n{rows}}}\n")

    # Ongoing work items — only "Under Study" items
    lines = []
    for wi in work_item_details:
        status = wi.status or ""
        # Filter: only include "Under Study" items
        if not status.lower().startswith('under study'):
            continue

        name = wi.workItem or ""
        title = wi.title or ""
        equiv = wi.equivNum or ""
        timing = wi.timing or ""
        aap = wi.approvalProcess or ""
        q_name = wi.question or ""

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

        # Columns: Question | Work Item | Status | Title | Editor | Base Text | Equivalent | Target Date | Summary updated | Approval process
        lines.append(table_row_str([
            q_name, seqsplit_text(name), escape_latex(status),
            escape_latex(title), "(manual entry)",
            td_name, escape_latex(equiv), escape_latex(timing), "", escape_latex(aap)
        ]))
    rows = "".join(lines)
    has_ongoing = "true" if lines else "false"
    write_result(RESULTS_DIR, "11-wp-ongoing-work-items.tex",
                 f"\\newcommand{{\\hasWpOngoingWorkItems}}{{{has_ongoing}}}\n"
                 f"\\newcommand{{\\wpOngoingWorkItems}}{{\n{rows}}}\n")


def _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors=None):
    """12-candidate-work-items table rows."""
    editors = editors or {}
    lines = []
    for element in candidate_next:
        # Try to find matching WP TD for baseline text
        q_name_td, td = find_td_by_name(wp_rows, element)
        if td is None:
            alt = extract_alt_name(element)
            if alt:
                q_name_td, td = find_td_by_name(wp_rows, alt)

        title = ""
        td_name = "no update"
        status = ""
        equiv = ""
        q_name = q_name_td or ""
        editor = ""

        # Look for baseline text TD
        element_lower = element.lower()
        alt = extract_alt_name(element)
        alt_lower = alt.lower() if alt else ""
        for row in wp_rows:
            row_title = (row.title or "").lower()
            if "baseline text" in row_title:
                if element_lower in row_title or (alt_lower and alt_lower in row_title):
                    td = row
                    td_name = make_href(URL + row.number.link,
                                        f"TD{row.number.value}{row.lastRev}/{wp_number}")
                    break

        # Fill status/title/equiv/question from work programme data
        for wi in work_item_details:
            wi_name = wi.workItem or ""
            wi_alt = extract_alt_name(wi_name)
            if (wi_name == element or wi_alt == element
                    or element in wi_name or (wi_alt and element in wi_alt)):
                status = wi.status or ""
                if not title:
                    title = wi.title or ""
                equiv = wi.equivNum or ""
                if not q_name and wi.question:
                    q_name = wi.question
                break

        # Columns: Question | Work Item | Status | Title | Editor | Base Text | A.5 justification | Equivalent
        lines.append(table_row_str([
            q_name, seqsplit_text(str(element)),
            escape_latex(status), escape_latex(title), "(manual entry)",
            td_name, "", escape_latex(equiv)
        ]))
    rows = "".join(lines)
    has_candidate = "true" if candidate_next else "false"
    write_result(RESULTS_DIR, "12-candidate-work-items.tex",
                 f"\\newcommand{{\\hasWpCandidateWorkItems}}{{{has_candidate}}}\n"
                 f"\\newcommand{{\\wpCandidateWorkItems}}{{\n{rows}}}\n")


def _gen_planned_meetings(group, wp_number, question_numbers, questions,
                          rapporteur_meetings, wp_rows):
    """13-planned-interim-meetings table rows."""
    lines = []
    if rapporteur_meetings:
        for element in rapporteur_meetings:
            _, td = find_td_by_number(wp_rows, element)
            q_name = ""
            title = ""
            td_ref = ""
            date_str = ""
            place = ""
            contact = ""
            if td:
                title = escape_latex(td.title)
                td_ref = make_href(URL + td.number.link,
                                   f"TD{element}{td.lastRev}/{wp_number}")
                # Extract question from TD
                if td.questions:
                    q_name = td.questions[0].value

                # Try extract "(Place, Date)" from end of title
                raw_title = td.title or ""
                idx1 = raw_title.rfind('(')
                idx2 = raw_title.rfind(')')
                if idx1 >= 0 and idx2 > idx1:
                    info = raw_title[idx1 + 1:idx2]
                    parts = info.split(',', 1)
                    if len(parts) == 2:
                        place = parts[0].strip()
                        date_str = parts[1].strip()

                # Contact: rapporteur for this question
                if q_name:
                    q_num = q_name.replace(f"/{group}", "")
                    for qd in questions:
                        if str(qd.question) == q_num:
                            for role in qd.roles:
                                if 'rapporteur' in role.roleName.lower():
                                    contact = f"{role.firstName} {role.lastName}"
                                    break
                            break

            lines.append(table_row_str([
                q_name, date_str, place, title or td_ref, contact
            ]))
    else:
        for qn in question_numbers:
            lines.append(table_row_str([f"{qn}/{group}", "", "", "", ""]))
    rows = "".join(lines)
    write_result(RESULTS_DIR, "13-planned-meetings.tex",
                 f"\\newcommand{{\\wpPlannedMeetings}}{{\n{rows}}}\n")


def _gen_scheduled_meetings(group, wp_number, interim_meetings,
                            next_sg_meeting=None):
    """14-scheduled-meetings content."""
    if interim_meetings:
        lines = ["\\begin{itemize}"]
        for element in interim_meetings:
            lines.append(f"  \\item {escape_latex(str(element))}")
        lines.append("\\end{itemize}")
        content = "\n".join(lines)
    else:
        content = (
            f"WP{wp_number}/{group} does not plan to organize a "
            f"WP{wp_number}/{group} interim meeting "
            f"before the next SG{group} meeting.\n"
        )
    write_result(RESULTS_DIR, "14-scheduled-meetings.tex",
                 f"\\newcommand{{\\wpScheduledMeetings}}{{\n{content}}}\n")

    # Next SG meeting info for section 13.2
    if next_sg_meeting:
        city = next_sg_meeting['city']
        country = next_sg_meeting.get('country', '')
        date_range = next_sg_meeting['date_range']
        if country:
            location = f"{city}, {country}"
        else:
            location = city
        next_meeting_text = escape_latex(f"{location}, {date_range}")
    else:
        next_meeting_text = "\\textit{city country, x.ymonth, 20yy}"
    write_result(RESULTS_DIR, "14-next-sg-meeting.tex",
                 f"\\newcommand{{\\wpNextSGMeeting}}{{{next_meeting_text}}}\n")


def _gen_ipr(group, wp_number, wp_rows):
    """04-ipr content: scan TDs for IPR statements, default to none received."""
    ipr_statements = []
    for row in wp_rows:
        title_lower = (row.title or "").lower()
        if ("ipr" in title_lower or "intellectual property" in title_lower
                or "patent" in title_lower):
            td_link = make_href(URL + row.number.link,
                                f"TD{row.number.value}{row.lastRev}/{wp_number}")
            ipr_statements.append(
                f"  \\item {escape_latex(row.title)} ({td_link})")

    if ipr_statements:
        content = ("\\begin{itemize}\n"
                   + "\n".join(ipr_statements)
                   + "\n\\end{itemize}\n")
    else:
        content = "No IPR statements were received at this meeting.\n"
    write_result(RESULTS_DIR, "04-ipr.tex",
                 f"\\newcommand{{\\wpIPRStatements}}{{\n{content}}}\n")


def _gen_conclusion(group, wp_number, chairs, sg_roles=None):
    """15-conclusion content: dynamic chair and TSB staff names."""
    if chairs:
        chair_text = " and ".join(chairs)
    else:
        chair_text = f"WP{wp_number}/{group}"

    # Extract TSB staff from SG-level roles
    sg_roles = sg_roles or []
    counsellor = ""
    project_officer = ""
    assistant = ""
    for role in sg_roles:
        name = f"{role.firstName} {role.lastName} ({role.company})"
        role_lower = role.roleName.lower()
        if 'counsellor' in role_lower and not counsellor:
            counsellor = name
        elif 'project officer' in role_lower and not project_officer:
            project_officer = name
        elif 'assistant' in role_lower and not assistant:
            assistant = name

    counsellor_text = escape_latex(counsellor) if counsellor else "\\textit{counsellor name (TSB)}"
    officer_text = escape_latex(project_officer) if project_officer else "\\textit{project officer name (TSB)}"
    assistant_text = escape_latex(assistant) if assistant else "\\textit{assistant name (TSB)}"

    content = (
        f"The {chair_text}, Chair of WP{wp_number}/{group}, "
        f"thanked the delegates for their enthusiastic and active participation "
        f"in the relevant activities of Working Party {wp_number}/{group} and each "
        f"Question during the meeting. Special thanks were expressed to the "
        f"SG{group} Counsellor, "
        f"{counsellor_text}, "
        f"SG{group} Project Officer "
        f"{officer_text} "
        f"and SG{group} assistant "
        f"{assistant_text} "
        f"as well as all Associate Rapporteurs, Editors, and contributors "
        f"for their dedicated and sustained efforts during this meeting.\n"
    )
    write_result(RESULTS_DIR, "15-conclusion.tex",
                 f"\\newcommand{{\\wpConclusion}}{{\n{content}}}\n")


def _gen_annex_a_docs(group, wp_number, c_rows, gen_rows, plen_rows, wp_rows):
    """Annex A: documentation tables (contributions, GEN, PLEN, WP) for all questions."""

    def _format_source(name):
        """Format source name: strip study group prefix (escaping done by make_href)."""
        if name and name.startswith(f"SG{group}"):
            name = name[len(f"SG{group}"):].strip()
            if name.startswith("-"):
                name = name[1:].strip()
        return name or ""

    def _get_q_display(row):
        """Get question display string from row, e.g. 'Q10/17' or 'QALL/17'."""
        if not row.questions:
            return ""
        q_val = row.questions[0].value  # e.g. "10/17" or "ALL/17"
        if q_val.startswith("Q"):
            return q_val  # Already has Q prefix
        return f"Q{q_val}"

    # Contributions
    lines = []
    for row in c_rows:
        q_display = _get_q_display(row)
        name = make_href(URL + row.number.link, f"C{row.number.value}{row.lastRev}")
        source = make_href(URL + row.source.link, _format_source(row.source.name))
        lines.append(table_row_str([q_display, name, source, escape_latex(row.title), q_display]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-contributions.tex",
                 f"\\newcommand{{\\wpAnnexContributions}}{{\n{rows}}}\n")

    # GEN TDs
    lines = []
    for row in gen_rows:
        q_display = _get_q_display(row)
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/G")
        source = make_href(URL + row.source.link, _format_source(row.source.name))
        lines.append(table_row_str([q_display, name, source, escape_latex(row.title), q_display]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-gen.tex",
                 f"\\newcommand{{\\wpAnnexGen}}{{\n{rows}}}\n")

    # PLEN TDs
    lines = []
    for row in plen_rows:
        q_display = _get_q_display(row)
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/P")
        source = make_href(URL + row.source.link, _format_source(row.source.name))
        lines.append(table_row_str([q_display, name, source, escape_latex(row.title), q_display]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-plen.tex",
                 f"\\newcommand{{\\wpAnnexPlen}}{{\n{rows}}}\n")

    # WP TDs
    lines = []
    for row in wp_rows:
        q_display = _get_q_display(row)
        name = make_href(URL + row.number.link, f"TD{row.number.value}{row.lastRev}/{wp_number}")
        source = make_href(URL + row.source.link, _format_source(row.source.name))
        lines.append(table_row_str([q_display, name, source, escape_latex(row.title), q_display]))
    rows = "".join(lines) if lines else "NONE"
    write_result(RESULTS_DIR, "annex-a-wp.tex",
                 f"\\newcommand{{\\wpAnnexWp}}{{\n{rows}}}\n")


def _gen_annex_b_reflectors(group, question_numbers):
    """Annex B: email reflector list for all questions in the WP."""
    lines = []
    for q in question_numbers:
        reflector = f"q{q}sg{group}@lists.itu.int"
        lines.append(f"\\item Q{q}/{group}: \\href{{mailto:{reflector}}}{{{reflector}}}")
    content = "\n".join(lines) if lines else "\\item None"
    write_result(RESULTS_DIR, "annex-b-reflectors.tex",
                 f"\\newcommand{{\\wpReflectorList}}{{\\begin{{itemize}}\n{content}\n\\end{{itemize}}}}\n")


def _gen_annex_c_new_work_items(wp_number, wp_rows):
    """Annex C: list of new work items with their justifications."""
    lines = []
    for row in wp_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)
            if not work_item:
                continue
            td_link = make_href(URL + row.number.link,
                                f"TD {row.number.value.replace(' ', '')}/{wp_number}")
            display = f"{escape_latex(work_item)}"
            if text_title:
                display += f" -- {escape_latex(text_title)}"
            lines.append(f"\\item {display} (see {td_link})")

    if lines:
        content = f"\\newcommand{{\\wpAnnexNewWorkItems}}{{\n" + "\n".join(lines) + "\n}\n"
    else:
        content = "% No new work items\n"
    write_result(RESULTS_DIR, "annex-c-new-work-items.tex", content)


# ===================================================================
def _parse_liaison_destinations(title):
    """Parse '[to X]' and '[for info to Y]' from a liaison statement title.

    Returns (action_to, info_to) strings.
    """
    action_to = ""
    info_to = ""
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
            prefix = 'for info to '
            pos = bracket.lower().find(prefix)
            if pos >= 0:
                info_to = bracket[pos + len(prefix):]
        elif bracket.lower().startswith('to '):
            action_to = bracket[3:]
        idx = end + 1
    return action_to, info_to



if __name__ == "__main__":
    main()
