#!/usr/bin/env python3
"""Generate LaTeX content files for an ITU-T Working Party report.

Usage:
    python generate_wp_report.py <config.json>

Reads a JSON configuration file, fetches data from the ITU website,
and generates LaTeX snippet files in ../wp_doc_template/chapters/results/.
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
    get_chairs, get_vice_chairs,
    get_document_title, get_liaison_destination, get_meeting_reports,
    extract_alt_name, auto_detect_from_work_programme,
    extract_new_work_item_info, detect_outgoing_liaisons,
    parse_timing, print_work_programme_summary,
)
from common.latex import (
    URL, escape_latex, make_href, td_href, write_result, table_row_str,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(PROJECT_DIR, 'wp_doc_template', 'chapters', 'results')


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.json>")
        sys.exit(1)

    config = load_wp_config(sys.argv[1])
    doc_type = config['documentType']
    group = config['group']
    wp_number = config['workingParty']
    place = config['place']
    start = config['start']
    start_string = config['startString']
    start_date = config['startDate']
    end = config['end']
    sessions = config.get('sessions')
    meeting_days = config.get('meetingDays') or []

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
    new_work_items = []
    deleted_work_items = []
    candidate_next = []
    outgoing_ls = []
    rapporteur_meetings = []
    interim_meetings = []

    # Auto-detect approval/consent/determination/agreement from work programme
    # status (e.g. "Consented 2025-04-17" → consent list)
    td_to_work_item = auto_detect_from_work_programme(
        work_item_details, wp_rows,
        approval, determination, consent, non_normative)

    # Auto-detect outgoing liaisons from WP TDs
    outgoing_ls = detect_outgoing_liaisons(wp_rows)

    # Auto-detect from TD document types
    for row in wp_rows:
        if row.documentType == 'Approval':
            val = row.number.value.strip()
            if val not in approval:
                approval.append(val)
    for row in wp_rows:
        if row.documentType == 'Determination':
            val = row.number.value.strip()
            if val not in determination:
                determination.append(val)
    for row in wp_rows:
        if row.documentType == 'Consent':
            val = row.number.value.strip()
            if val not in consent:
                consent.append(val)
    for row in wp_rows:
        if row.documentType == 'Agreement':
            val = row.number.value.strip()
            if val not in non_normative:
                non_normative.append(val)

    # Auto-detect candidate work items for next SG meeting
    # Criteria: "Under study" items with timing ≤ next SG meeting (~6 months out)
    from datetime import datetime, timedelta
    meeting_start = config['start']
    if isinstance(meeting_start, str):
        meeting_start = datetime.strptime(meeting_start, '%Y/%m/%d')
    next_meeting = meeting_start + timedelta(days=180)
    for wi in work_item_details:
        status = (wi.status or '').strip()
        if not status.startswith('Under study'):
            continue
        timing = (wi.timing or '').strip()
        if not timing:
            continue
        timing_date = parse_timing(timing)
        if timing_date and timing_date <= next_meeting:
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
    next_sg_meeting = get_next_sg_meeting(group, after_date=meeting_start)
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

    if doc_type == "agenda":
        # WP agenda not implemented in original script
        print("WP agenda generation not yet implemented.")
        sys.exit(0)

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
                           non_normative, work_items, new_work_items, deleted_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           wp_rows)
    _gen_structure_leadership(group, wp_number, chairs, vice_chairs,
                              question_numbers, questions_details)
    _gen_documentation(group, wp_number, question_numbers, start_date, period,
                       c_rows, plen_rows, gen_rows, wp_rows)
    _gen_opening_plenary(group, wp_number, question_numbers, wp_rows)
    _gen_opening_plenary_issues(group, wp_number, question_numbers,
                                wp_rows, plen_rows, gen_rows)
    _gen_appointments(group, wp_number, question_numbers, questions_details)
    _gen_question_meetings(group, wp_number, question_numbers, wp_rows, c_rows,
                           approval, determination, consent, non_normative,
                           work_items, new_work_items, deleted_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           work_item_details=work_item_details,
                           td_to_work_item=td_to_work_item)
    _gen_draft_recommendations(group, wp_number, wp_rows, approval, determination,
                               consent, non_normative,
                               td_to_work_item=td_to_work_item)
    _gen_outgoing_liaisons(group, wp_number, question_numbers, outgoing_ls, wp_rows)
    _gen_work_programme(group, wp_number, question_numbers, work_items,
                        work_item_details, new_work_items, deleted_work_items,
                        c_rows, wp_rows, editors=editors)
    _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors=editors)
    _gen_planned_meetings(group, wp_number, question_numbers, questions,
                          rapporteur_meetings, wp_rows)
    _gen_scheduled_meetings(group, wp_number, interim_meetings, next_sg_meeting)
    _gen_ipr(group, wp_number, wp_rows)
    _gen_conclusion(group, wp_number, chairs, sg_roles=wp_details.sg_roles)
    _gen_annex_a(group, wp_number, wp_rows, work_item_details)

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
    """01-introduction content."""
    date_range = _format_date_range(start, end)
    chair_str = " and ".join(chairs)
    lines = [
        f"Working Party {wp_number}/{group} met during the SG{group} meeting held in "
        f"{place}, {date_range}, chaired by {chair_str}"
    ]
    if vice_chairs:
        vc_str = ", ".join(vice_chairs)
        lines[0] += f" and assisted by {vc_str}"
    lines[0] += "\n"

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

    lines.append(f"The meeting was addressed in {sessions_str} sessions on {days_str}. "
                 f"The group adopted the agenda in {agenda_ref}.\n")
    write_result(RESULTS_DIR, "01-introduction-content.tex", "\n".join(lines))


def _gen_executive_summary(group, wp_number, approval, determination, consent,
                           non_normative, work_items, new_work_items, deleted_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           wp_rows):
    """02-executive-summary content."""
    lines = [
        f"\\textit{{Include here an executive summary of the executive summaries "
        f"of Questions of this WP meeting.}}\n",
        f"During this SG{group} meeting, WP{wp_number}/{group} achieved the following results:\n",
        "\\begin{itemize}",
    ]

    if approval:
        lines.append(f"  \\item {len(approval)} Recommendations were finalized and "
                     f"proposed for TAP approval: {comma_separated_list(approval)}")
    if determination:
        lines.append(f"  \\item {len(determination)} Recommendations were finalized and "
                     f"proposed for TAP determination: {comma_separated_list(determination)}")
    if consent:
        lines.append(f"  \\item {len(consent)} Recommendations were finalized and "
                     f"proposed for AAP consent: {comma_separated_list(consent)}")
    if non_normative:
        lines.append(f"  \\item {len(non_normative)} non-normative texts (e.g.\\ Supplements, "
                     f"Technical reports, etc.) were finalized and proposed for agreement: "
                     f"{comma_separated_list(non_normative)}")
    if len(new_work_items) == 1:
        lines.append(f"  \\item {len(new_work_items)} new work item was agreed to be started: "
                     f"{comma_separated_list(new_work_items)}")
    elif len(new_work_items) > 1:
        lines.append(f"  \\item {len(new_work_items)} new work items were agreed to be started: "
                     f"{comma_separated_list(new_work_items)}")
    if len(deleted_work_items) == 1:
        lines.append(f"  \\item {len(deleted_work_items)} work item was agreed to be deleted: "
                     f"{comma_separated_list(deleted_work_items)}")
    elif len(deleted_work_items) > 1:
        lines.append(f"  \\item {len(deleted_work_items)} work items were agreed to be deleted: "
                     f"{comma_separated_list(deleted_work_items)}")
    if len(work_items) == 1:
        lines.append(f"  \\item {len(work_items)} work item was progressed: "
                     f"{comma_separated_list(work_items)}")
    elif len(work_items) > 1:
        lines.append(f"  \\item {len(work_items)} work items were progressed: "
                     f"{comma_separated_list(work_items)}")
    if len(candidate_next) == 1:
        lines.append(f"  \\item {len(candidate_next)} work item is planned for action "
                     f"in next SG{group} meeting: {comma_separated_list(candidate_next)}")
    elif len(candidate_next) > 1:
        lines.append(f"  \\item {len(candidate_next)} work items are planned for action "
                     f"in next SG{group} meeting: {comma_separated_list(candidate_next)}")

    if outgoing_ls:
        destinations = [get_liaison_destination(wp_rows, n) for n in outgoing_ls]
        destinations = [d for d in destinations if d]
        if len(outgoing_ls) == 1:
            lines.append(f"  \\item {len(outgoing_ls)} outgoing liaison statement was agreed "
                         f"to be sent: {comma_separated_list(destinations)}")
        else:
            lines.append(f"  \\item {len(outgoing_ls)} outgoing liaison statements were agreed "
                         f"to be sent: {comma_separated_list(destinations)}")

    if rapporteur_meetings:
        titles = [get_document_title(wp_rows, n) for n in rapporteur_meetings]
        titles = [t for t in titles if t]
        if len(rapporteur_meetings) == 1:
            lines.append(f"  \\item {len(rapporteur_meetings)} interim (RGM) meeting was planned "
                         f"before the next SG{group} meeting: {comma_separated_list(titles)}")
        else:
            lines.append(f"  \\item {len(rapporteur_meetings)} interim (RGM) meetings were planned "
                         f"before the next SG{group} meetings: {comma_separated_list(titles)}")

    lines.append("  \\item \\textit{Appointment of associate rapporteur / liaison officers, if any}")
    lines.append("  \\item \\textit{Any other issue of importance (e.g.\\ OID assignment, "
                 "roadmap updates, workshop, joint session, A.5 qualification)}")
    lines.append("\\end{itemize}")

    write_result(RESULTS_DIR, "02-executive-summary-content.tex", "\n".join(lines))


def _gen_structure_leadership(group, wp_number, chairs, vice_chairs,
                              question_numbers, questions_details):
    """03-wp-structure-and-leadership content."""
    lines = [
        f"WP{wp_number}/{group} Management team\n",
        "\\begin{itemize}",
    ]
    if len(chairs) == 1:
        lines.append(f"  \\item Chair: {chairs[0]}")
    else:
        for ch in chairs:
            lines.append(f"  \\item Co-chair: {ch}")
    for vc in vice_chairs:
        lines.append(f"  \\item Vice-chair: {vc}")
    lines.append("\\end{itemize}\n")

    lines.append(f"The following table reproduces the current list of WP{wp_number}/{group} "
                 f"Questions and related Rapporteurs\n")

    # Contact table for frontmatter
    contact_lines = []
    for role in (chairs + vice_chairs):
        # The role string is "Name (Company, Address)"
        # For the contact table, we keep the simple format
        pass  # Contact table is generated separately if needed

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
            rapp = rapps[i] if i < len(rapps) else ""
            assoc = assoc_rapps[i] if i < len(assoc_rapps) else ""
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
                           approval, determination, consent, non_normative,
                           work_items, new_work_items, deleted_work_items,
                           candidate_next, outgoing_ls, rapporteur_meetings,
                           work_item_details=None, td_to_work_item=None):
    """07-questions-meetings content — per-question executive summaries."""
    td_wi = td_to_work_item or {}
    wi_details = work_item_details or []
    lines = []

    def _tds_for_question(td_numbers, q_name):
        """Filter a list of TD numbers to those belonging to a question."""
        result = []
        for num in td_numbers:
            for row in wp_rows:
                if row.number.value.strip() == str(num).strip():
                    if any(rq.value == q_name for rq in row.questions):
                        result.append(num)
                    break
        return result

    def _resolve_names(td_numbers):
        """Convert TD numbers to work item names via td_to_work_item."""
        names = []
        for num in td_numbers:
            wi = td_wi.get(str(num).strip())
            if wi and wi.workItem:
                names.append(wi.workItem)
            else:
                names.append(f"TD{num}")
        return names

    def _wi_names_for_question(wi_name_list, q_number):
        """Filter work item names by question using work_item_details."""
        q_str = str(q_number)
        q_wi_names = set()
        for wi in wi_details:
            if wi.question and str(wi.question) == q_str:
                q_wi_names.add(wi.workItem)
        return [name for name in wi_name_list if name in q_wi_names]

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
        lines.append(f"The report of Q{qn}/{group} can be found in {q_report}. It was approved.\n")

        # Count contributions for this question
        q_contributions = [r for r in c_rows
                           if any(rq.value == q_name for rq in r.questions)]

        # Filter per-question data
        q_approval = _tds_for_question(approval, q_name)
        q_determination = _tds_for_question(determination, q_name)
        q_consent = _tds_for_question(consent, q_name)
        q_agreement = _tds_for_question(non_normative, q_name)
        q_new_wi = _wi_names_for_question(new_work_items, qn)
        q_deleted_wi = _wi_names_for_question(deleted_work_items, qn)
        q_candidate = _wi_names_for_question(candidate_next, qn)
        q_outgoing = _tds_for_question(outgoing_ls, q_name)
        q_rapporteur_meetings = _tds_for_question(rapporteur_meetings, q_name)

        # Work items progressed for this question
        q_work_items = _wi_names_for_question(work_items, qn)

        # Build executive summary items
        items = []
        lines.append(f"During this meeting, {q_name} received "
                     f"{len(q_contributions)} contribution{'s' if len(q_contributions) != 1 else ''} "
                     f"and achieved the following results:\n")

        if q_approval:
            names = _resolve_names(q_approval)
            items.append(f"  \\item {len(q_approval)} Recommendation{'s' if len(q_approval) != 1 else ''} "
                         f"were finalized and proposed for TAP approval: "
                         f"{comma_separated_list(names)}")
        if q_determination:
            names = _resolve_names(q_determination)
            items.append(f"  \\item {len(q_determination)} Recommendation{'s' if len(q_determination) != 1 else ''} "
                         f"were finalized and proposed for TAP determination: "
                         f"{comma_separated_list(names)}")
        if q_consent:
            names = _resolve_names(q_consent)
            items.append(f"  \\item {len(q_consent)} Recommendation{'s' if len(q_consent) != 1 else ''} "
                         f"were finalized and proposed for AAP consent: "
                         f"{comma_separated_list(names)}")
        if q_agreement:
            names = _resolve_names(q_agreement)
            items.append(f"  \\item {len(q_agreement)} non-normative text{'s' if len(q_agreement) != 1 else ''} "
                         f"(e.g.\\ Supplements, Technical reports, etc.) were finalized and "
                         f"proposed for agreement: {comma_separated_list(names)}")
        if q_work_items:
            items.append(f"  \\item {len(q_work_items)} work item{'s' if len(q_work_items) != 1 else ''} "
                         f"were progressed: {comma_separated_list(q_work_items)}")
        if q_new_wi:
            items.append(f"  \\item {len(q_new_wi)} new work item{'s' if len(q_new_wi) != 1 else ''} "
                         f"were agreed to be started: {comma_separated_list(q_new_wi)}")

        # Discontinued (always show, even if 0)
        items.append(f"  \\item {len(q_deleted_wi)} work item{'s' if len(q_deleted_wi) != 1 else ''} "
                     f"were agreed to be discontinued: "
                     f"{comma_separated_list(q_deleted_wi) if q_deleted_wi else 'None.'}")

        if q_candidate:
            items.append(f"  \\item {len(q_candidate)} text{'s' if len(q_candidate) != 1 else ''} "
                         f"were agreed as candidate{'s' if len(q_candidate) != 1 else ''} "
                         f"for decision in next SG{group} meeting: "
                         f"{comma_separated_list(q_candidate)}")

        if q_outgoing:
            destinations = [get_liaison_destination(wp_rows, n) for n in q_outgoing]
            destinations = [d for d in destinations if d]
            items.append(f"  \\item {len(q_outgoing)} outgoing liaison statement{'s' if len(q_outgoing) != 1 else ''} "
                         f"were agreed to be sent"
                         f"{': ' + comma_separated_list(destinations) if destinations else '.'}")

        if q_rapporteur_meetings:
            titles = [get_document_title(wp_rows, n) for n in q_rapporteur_meetings]
            titles = [t for t in titles if t]
            items.append(f"  \\item {len(q_rapporteur_meetings)} RGM meeting{'s' if len(q_rapporteur_meetings) != 1 else ''} "
                         f"were planned"
                         f"{': ' + comma_separated_list(titles) if titles else '.'}")

        if items:
            lines.append("\\begin{itemize}")
            lines.extend(items)
            lines.append("\\end{itemize}\n")
        else:
            lines.append("Work items were progressed.\n")

    write_result(RESULTS_DIR, "07-question-meetings.tex", "\n".join(lines))


def _gen_draft_recommendations(group, wp_number, wp_rows, approval, determination,
                               consent, non_normative,
                               td_to_work_item=None):
    """08-draft-recommendations table rows."""
    td_wi = td_to_work_item or {}

    def _gen_table(items, has_a5=True):
        lines = []
        for num, element in enumerate(items, 1):
            q_name, td, a5 = find_question_name_td_and_a5(wp_rows, element)
            final_text = ""
            if td:
                final_text = make_href(URL + td.number.link,
                                       f"TD {td.number.value}{td.lastRev}/{wp_number}")
            a5_text = ""
            if a5:
                a5_text = make_href(URL + a5.number.link,
                                    f"TD {a5.number.value}{a5.lastRev}/{wp_number}")

            # Get work item name: prefer work programme data, fall back to TD fields
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
            text_title = escape_latex(td.textTitle) if td else ""

            # Fill equiv from work programme if available
            equiv_num = escape_latex(wp_wi.equivNum) if wp_wi and wp_wi.equivNum else ""

            if has_a5:
                lines.append(table_row_str([
                    num, q_name, escape_latex(work_item), "",
                    text_title, final_text, a5_text, equiv_num
                ]))
            else:
                lines.append(table_row_str([
                    num, q_name, escape_latex(work_item), "",
                    text_title, final_text
                ]))
        return "".join(lines)

    rows = _gen_table(approval)
    write_result(RESULTS_DIR, "08-draft-rec-approval.tex",
                 f"\\newcommand{{\\wpApproval}}{{\n{rows}}}\n")
    rows = _gen_table(determination)
    write_result(RESULTS_DIR, "08-draft-rec-determination.tex",
                 f"\\newcommand{{\\wpDetermination}}{{\n{rows}}}\n")
    rows = _gen_table(consent)
    write_result(RESULTS_DIR, "08-draft-rec-consent.tex",
                 f"\\newcommand{{\\wpConsent}}{{\n{rows}}}\n")

    # Non-normative / agreement — reuse _gen_table (no A.5 column)
    rows = _gen_table(non_normative, has_a5=False)
    write_result(RESULTS_DIR, "09-agreement.tex",
                 f"\\newcommand{{\\wpAgreement}}{{\n{rows}}}\n")


def _gen_outgoing_liaisons(group, wp_number, question_numbers, outgoing_ls, wp_rows):
    """10-outgoing-liaison-statements table rows."""
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
        lines.append(table_row_str([
            num, q_name, f"WP{wp_number}",
            f"\\textit{{{escape_latex(action_to)}}}",
            f"\\textit{{{escape_latex(info_to)}}}",
            escape_latex(title), td_name
        ]))
    rows = "".join(lines)
    write_result(RESULTS_DIR, "10-outgoing-liaisons.tex",
                 f"\\newcommand{{\\wpOutgoingLiaisons}}{{\n{rows}}}\n")


def _gen_work_programme(group, wp_number, question_numbers, work_items,
                        work_item_details, new_work_items, deleted_work_items,
                        c_rows, wp_rows, editors=None):
    """11-work-programme table rows (new, deleted, ongoing)."""
    import re
    editors = editors or {}

    # Build a lookup of "New work item" Output TDs by question for fallback matching
    output_new_wi = {}
    for r in wp_rows:
        if r.documentType == 'New work item' or (
                r.title and 'new work item' in r.title.lower() and 'Output' in r.title):
            for rq in r.questions:
                output_new_wi.setdefault(rq.value, []).append(r)

    # Build justification lookup: work_item_name -> TD reference
    justification_lookup = {}
    for row in wp_rows:
        title = row.title or ""
        if re.search(r'A\.(\d+)\s+justification', title, re.IGNORECASE):
            wi_m = re.search(r'(X\.\S+|TR\.\S+|XSTR\.\S+)', title)
            if wi_m:
                wi_key = wi_m.group(1).rstrip(',:').strip().lower()
                td_ref = make_href(URL + row.number.link,
                                   f"TD{row.number.value}{row.lastRev}/{wp_number}")
                justification_lookup[wi_key] = td_ref
        elif 'new work item' in title.lower() and 'Proposal' in title:
            wi_m = re.search(r'(X\.\S+|TR\.\S+|XSTR\.\S+)', title)
            if wi_m:
                wi_key = wi_m.group(1).rstrip(',:').strip().lower()
                if wi_key not in justification_lookup:
                    td_ref = make_href(URL + row.number.link,
                                       f"TD{row.number.value}{row.lastRev}/{wp_number}")
                    justification_lookup[wi_key] = td_ref

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
        # e.g. "X.accsadlt (X.suppl.bdsa)" -> try matching "X.accsadlt" against
        # keys or alt-names like "X.1286 (ex X.accsadlt)"
        base = stripped.split('(')[0].strip().split(',')[0].strip()
        if base and base != stripped:
            editor = editors.get(base, "")
            if editor:
                return editor
            # Check if base appears in any editor key's alt name
            for key in editors:
                key_alt = extract_alt_name(key)
                if key_alt and key_alt.lower() == base.lower():
                    return editors[key]

        return ""

    # New work items from contributions (deduplicated by work item name)
    lines = []
    seen_work_items = set()
    num = 0
    for row in c_rows:
        if is_new_work_item(row.title):
            work_item, text_title = extract_new_work_item_info(row.title, wp_rows)

            # Fallback: match by question against Output TDs
            if not work_item:
                q_val = row.questions[0].value if row.questions else ""
                for out_td in output_new_wi.get(q_val, []):
                    if out_td.acronym:
                        work_item = out_td.acronym
                        if not text_title:
                            text_title = out_td.textTitle
                        break

            # Fallback 2: match by question against work programme items with recent timing
            if not work_item:
                q_val = row.questions[0].value if row.questions else ""
                for wi in work_item_details:
                    if wi.question == q_val and wi.status and 'under study' in wi.status.lower():
                        # Check if work item name appears in contribution title
                        wi_base = (wi.workItem or "").split('(')[0].strip()
                        if wi_base and wi_base.lower() in row.title.lower():
                            work_item = wi.workItem
                            if not text_title:
                                text_title = wi.title or ""
                            break

            # Deduplicate: skip if we already have this work item
            dedup_key = work_item.strip().lower() if work_item else ""
            if dedup_key and dedup_key in seen_work_items:
                continue
            if dedup_key:
                seen_work_items.add(dedup_key)

            # Look up equivalent ISO/IEC from work programme data
            equiv = ""
            if work_item:
                item_lower = work_item.strip().lower()
                for wi in work_item_details:
                    if wi.workItem:
                        wi_lower = wi.workItem.strip().lower()
                        if wi_lower == item_lower or item_lower in wi_lower:
                            equiv = wi.equivNum or ""
                            break

            # Look up A.1/A.13 justification TD
            justification = ""
            if work_item:
                wi_key = work_item.strip().lower()
                justification = justification_lookup.get(wi_key, "")
                if not justification:
                    alt = extract_alt_name(work_item)
                    if alt:
                        justification = justification_lookup.get(alt.lower(), "")

            # Look up editor
            editor = _lookup_editor(work_item)

            num += 1
            q_name = row.questions[0].value if row.questions else ""
            base_text = td_href(row, "C")
            lines.append(table_row_str([
                num, q_name, escape_latex(work_item), "New",
                escape_latex(text_title), escape_latex(editor),
                base_text, escape_latex(equiv)
            ]))
    rows = "".join(lines)
    write_result(RESULTS_DIR, "11-wp-new-work-items.tex",
                 f"\\newcommand{{\\wpNewWorkItems}}{{\n{rows}}}\n")

    # Deleted work items
    lines = []
    for num, element in enumerate(deleted_work_items, 1):
        q_name, td = find_td_by_number(wp_rows, element)
        title = escape_latex(td.textTitle) if td else ""
        acronym = escape_latex(td.acronym) if td else ""
        lines.append(table_row_str([num, q_name, acronym, title]))
    rows = "".join(lines) if lines else "No deleted work items.\n"
    write_result(RESULTS_DIR, "11-wp-deleted-work-items.tex",
                 f"\\newcommand{{\\wpDeletedWorkItems}}{{\n{rows}}}\n")

    # Ongoing work items — use work programme scraping data as primary source
    lines = []
    for num, wi in enumerate(work_item_details, 1):
        name = wi.workItem or ""
        title = wi.title or ""
        status = wi.status or ""
        equiv = wi.equivNum or ""
        timing = wi.timing or ""
        q_name = wi.question or ""

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

        # Look up editor
        editor = _lookup_editor(name)

        lines.append(table_row_str([
            num, q_name, escape_latex(name), escape_latex(status),
            escape_latex(title), escape_latex(editor),
            td_name, escape_latex(equiv), escape_latex(timing), ""
        ]))
    rows = "".join(lines)
    write_result(RESULTS_DIR, "11-wp-ongoing-work-items.tex",
                 f"\\newcommand{{\\wpOngoingWorkItems}}{{\n{rows}}}\n")


def _gen_candidate_work_items(group, wp_number, candidate_next, wp_rows,
                              work_item_details, editors=None):
    """12-candidate-work-items table rows."""
    editors = editors or {}
    lines = []
    for num, element in enumerate(candidate_next, 1):
        # Try to find matching WP TD
        q_name_td, td = find_td_by_name(wp_rows, element)
        if td is None:
            alt = extract_alt_name(element)
            if alt:
                q_name_td, td = find_td_by_name(wp_rows, alt)

        title = ""
        td_name = ""
        status = ""
        equiv = ""
        q_name = q_name_td or ""
        if td:
            title = td.textTitle
            td_name = make_href(URL + td.number.link,
                                f"TD{td.number.value}{td.lastRev}/{wp_number}")

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

        # Look up editor
        editor = editors.get(element, "")
        if not editor:
            alt = extract_alt_name(element)
            if alt:
                editor = editors.get(alt, "")
        if not editor:
            # Try matching element against editor keys' alt names
            for key in editors:
                key_alt = extract_alt_name(key)
                if key_alt and key_alt.lower() == element.lower():
                    editor = editors[key]
                    break

        lines.append(table_row_str([
            num, q_name, escape_latex(str(element)),
            escape_latex(status), escape_latex(title), escape_latex(editor),
            td_name, "", escape_latex(equiv)
        ]))
    rows = "".join(lines)
    write_result(RESULTS_DIR, "12-candidate-work-items.tex",
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


def _gen_annex_a(group, wp_number, wp_rows, work_item_details):
    """annex-a content: A.1/A.13 justification subsections for new work items.

    Finds 'Output - Proposal for new work item' TDs and explicit
    'A.1/A.13/A.25 justification' TDs. Uses the work programme approval
    process to determine A.1 (AAP/TAP) vs A.13 (Agreement).
    """
    import re

    # Build approval process lookup from work programme
    wp_process = {}
    for wi in work_item_details:
        name = wi.workItem or ""
        wp_process[name] = wi.approvalProcess or ""
        alt = extract_alt_name(name)
        if alt:
            wp_process[alt] = wi.approvalProcess or ""

    # First pass: collect explicit A.x justification TDs and track their work items
    explicit_justifications = []
    explicit_wi_names = set()
    for row in wp_rows:
        title = row.title or ""
        m = re.search(r'A\.(\d+)\s+justification', title, re.IGNORECASE)
        if not m:
            continue
        display = title
        idx = title.find(' - ')
        if idx >= 0:
            display = title[idx + 3:]
        td_link = make_href(URL + row.number.link,
                            f"TD{row.number.value}{row.lastRev}/{wp_number}")
        explicit_justifications.append((row.number.value, escape_latex(display), td_link))
        # Track the work item name to avoid duplicates with proposals
        wi_m = re.search(r'(X\.\S+|TR\.\S+|XSTR\.\S+)', title)
        if wi_m:
            explicit_wi_names.add(wi_m.group(1).rstrip(',:').strip())

    # Second pass: collect "Proposal for new work item" TDs
    entries = []
    seen_names = set()

    for row in wp_rows:
        title = row.title or ""

        # Match "Output - Proposal for [a] new work item X.name ..."
        if 'new work item' not in title.lower():
            continue
        if 'Proposal' not in title:
            continue

        # Extract work item name from the title
        # Try X./TR./XSTR. pattern first (most specific)
        m = re.search(
            r'(?:ITU-T\s+)?[<\s]*(X\.\S+|TR\.\S+|XSTR\.\S+)',
            title[title.lower().find('new work item'):], re.IGNORECASE)
        if not m:
            # Fallback: "Supplement to X.xxx"
            m = re.search(r'(Supplement\s+\S+)', title, re.IGNORECASE)
        if not m:
            continue

        wi_name = m.group(1).rstrip(',:>').strip()
        # Fix names with trailing hyphen/dot from space in original (e.g. "XSTR.QKDN- ZTA")
        if wi_name.endswith('-') or wi_name.endswith('.'):
            full_title_idx = title.find(wi_name)
            if full_title_idx >= 0:
                rest_text = title[full_title_idx + len(wi_name):].strip()
                next_word = rest_text.split()[0] if rest_text else ""
                if next_word and not next_word.startswith('"'):
                    wi_name = wi_name + next_word.rstrip(',:')

        # Skip if explicit justification already exists for this item
        if wi_name in explicit_wi_names:
            continue
        # Skip duplicates (same work item proposed in multiple TDs)
        if wi_name in seen_names:
            continue
        seen_names.add(wi_name)

        # Determine A.1 vs A.13 from approval process
        process = wp_process.get(wi_name, "")
        if not process:
            for key, val in wp_process.items():
                if wi_name in key or key in wi_name:
                    process = val
                    break

        if process == "Agreement":
            annex_num = "A.13"
        else:
            annex_num = "A.1"

        # Extract the descriptive part — look for quoted text or text after colon/comma
        after_name = ""
        # Try to find quoted text in the title
        quote_m = re.search(r'"([^"]+)"', title)
        if quote_m:
            after_name = f', "{quote_m.group(1)}"'
        else:
            # Try text after work item name + separator
            desc_idx = title.find(wi_name)
            if desc_idx >= 0:
                rest = title[desc_idx + len(wi_name):].strip().lstrip(',:').strip()
                rest = rest.strip('"').strip()
                if rest:
                    after_name = f', "{rest}"'

        display = f"{annex_num} justification for proposed draft new ITU-T {wi_name}{after_name}"

        td_link = make_href(URL + row.number.link,
                            f"TD{row.number.value}{row.lastRev}/{wp_number}")
        entries.append((row.number.value, escape_latex(display), td_link))

    # Merge: explicit justifications first, then proposals
    entries = explicit_justifications + entries

    lines = []
    for _, display, td_link in entries:
        lines.append(f"\\subsection*{{{display}}}")
        lines.append(f"\\addcontentsline{{toc}}{{subsection}}{{{display}}}")
        lines.append(f"See {td_link}\n")
        lines.append("\\newpage\n")

    write_result(RESULTS_DIR, "annex-a-justifications.tex", "\n".join(lines))


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
