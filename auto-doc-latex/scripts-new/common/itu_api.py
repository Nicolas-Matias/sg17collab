"""ITU website data fetching functions.

Fetches organizational data from ITU web pages:
- Meeting documents (contributions, TDs)
- Question details and leadership
- Study group structure
- Working party management
"""

import pycurl
import sys
from io import BytesIO
from bs4 import BeautifulSoup

from common.models import (
    ValueAndLink, TableRow, AElement, Column, Row, Table,
    Role, Question, WorkingParty, WorkItem,
    QuestionStructure, WorkingPartyStructure, StudyGroupStructure,
)

debug = False


# ---------------------------------------------------------------------------
# Meeting documents
# ---------------------------------------------------------------------------

def get_documents(document_type=None, group=None, working_party=None,
                  questions=None, start=None):
    """Fetch temporary documents from ITU meeting document system.

    Args:
        document_type: 'C' (Contributions), 'GEN', 'PLEN', or 'WP'
        group: Study group number (e.g. 17)
        working_party: Working party number
        questions: Single question number, list of numbers, or 'QALL'
        start: Start date string (YYYYMMDD)

    Returns:
        List of TableRow objects.
    """
    year = int(start[2:4])
    period = str(int(year / 4) * 4 + 1)
    url_base = (f"https://www.itu.int/md/meetingdoc.asp?lang=en"
                f"&parent=T{period}-SG{group}-{start[2:]}-")

    type_map = {'C': 'C', 'GEN': 'TD-GEN', 'PLEN': 'TD-PLEN',
                'WP': f'TD-WP{working_party}'}
    if document_type not in type_map:
        return None
    url_base += type_map[document_type]

    question_names = []
    all_questions_name = f'QALL/{group}'

    if questions is not None:
        if isinstance(questions, list):
            for q in questions:
                question_names.append(f'Q{q}/{group}')
        elif isinstance(questions, int):
            url_base += f'&question=Q{questions}/{group}'
        else:
            url_base += f'&question=QALL/{group}'

    first = 0
    table_rows = []

    while True:
        url = f"{url_base}&PageLB={first}"
        response = _fetch_url(url, encoding='iso8859-2')
        tables = _parse_html_tables(response)

        nrows = 0
        for table in tables:
            if not _is_document_table(table):
                continue

            nrows = len(table.rows) - 3
            if nrows <= 0:
                break
            first += nrows

            for i in range(2, len(table.rows) - 1):
                row = table.rows[i]
                number = None
                rev = None
                title = None
                source = None
                related_questions = None

                for col_idx, column in enumerate(row.columns):
                    if col_idx == 1:  # Number
                        if column.aElements:
                            value = None
                            if column.aElements[0].strongElements:
                                value = column.aElements[0].strongElements[0]
                            elif column.aElements[0].contents:
                                value = _clean(column.aElements[0].contents[0])
                            href = column.aElements[0].href
                            number = ValueAndLink(value, href)
                        if column.fontElements:
                            rev = column.fontElements[0][0]

                    elif col_idx == 2:  # Title
                        if column.contents:
                            idx = column.contents[0].find("\r")
                            title = column.contents[0][:idx] if idx >= 0 else column.contents[0]
                            idx = title.find("[from ")
                            if idx >= 0:
                                title = title[:idx]

                    elif col_idx == 3:  # Source
                        if column.aElements:
                            source = ValueAndLink(
                                column.aElements[0].contents[0],
                                column.aElements[0].href
                            )

                    elif col_idx == 4:  # Related questions
                        related_questions = [
                            ValueAndLink(a.contents[0], a.href)
                            for a in column.aElements
                        ]

                # Filter by question if a list was provided
                selected = True
                if isinstance(questions, list):
                    selected = False
                    for q in (related_questions or []):
                        if q.name == all_questions_name:
                            selected = True
                            break
                        for qn in question_names:
                            if qn == q.name:
                                selected = True
                        if selected:
                            break

                if selected:
                    table_rows.append(TableRow(
                        number=number, rev=rev, title=title,
                        source=source, questions=related_questions
                    ))

        if nrows <= 0:
            break

    return table_rows


# ---------------------------------------------------------------------------
# Question details
# ---------------------------------------------------------------------------

def get_question(group=None, question=None, start=None):
    """Fetch question leadership data from the ITU LOQR page.

    Args:
        group: Study group number
        question: Question number
        start: Start date (YYYYMMDD)

    Returns:
        Question object with roles, or None.
    """
    year = int(start[:4])
    period = str(int((year - 1953) / 4))
    url = (f"https://www.itu.int/net4/ITU-T/lists/loqr.aspx"
           f"?Group={group}&Period={period}")
    question_name = f'Q{question}/{group}'

    response = _fetch_url(url, encoding='utf-8')
    soup = BeautifulSoup(response, "html.parser")

    prefix = 'ContentPlaceHolder1_dtlRappQues_'
    selected_table = None
    first_row = None
    last_row = None

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not isinstance(rows, list):
            continue
        for i in range(len(rows)):
            row = rows[i]
            for td in row.find_all("td"):
                spans = td.find_all("span")
                if not (isinstance(spans, list) and spans):
                    continue
                if 'id' not in spans[0].attrs:
                    continue
                span_id = spans[0].attrs['id']
                if span_id.startswith(prefix + 'lblQWP_') or i == len(rows) - 1:
                    if selected_table is None:
                        contents = spans[0].contents
                        if (isinstance(contents, list) and contents and
                                contents[0].startswith(question_name)):
                            selected_table = table
                            first_row = i
                    else:
                        last_row = i
                        break
            if last_row is not None:
                break
        if last_row is not None:
            break

    if last_row is None:
        return None

    question_details = Question(group=group, question=question)
    rows = selected_table.find_all("tr")

    for i in range(first_row, last_row):
        row = rows[i]
        role = Role()
        for td in row.find_all("td"):
            spans = td.find_all("span")
            a_elements = td.find_all("a")
            for span in spans:
                if 'id' not in span.attrs or not span.contents:
                    continue
                span_id = span.attrs['id']
                content = span.contents[0]

                if span_id.startswith(prefix + 'lblQWP_'):
                    idx1 = content.find('(WP')
                    if idx1 >= 0:
                        idx2 = content.find('/', idx1 + 3)
                        if idx2 > 0:
                            try:
                                question_details.workingParty = int(content[idx1 + 3:idx2])
                            except ValueError:
                                pass
                elif span_id.startswith(prefix + 'lblQuestion69_'):
                    question_details.title = content
                elif span_id.startswith(prefix + 'lblFName_'):
                    role.firstName = content
                elif span_id.startswith(prefix + 'lblLName_'):
                    role.lastName = content
                elif span_id.startswith(prefix + 'lblRole_'):
                    role.roleName = content
                elif span_id.startswith(prefix + 'lblCompany_'):
                    role.company = content
                elif span_id.startswith(prefix + 'lblAddress_'):
                    if len(span.contents) > 1:
                        role.address = span.contents[-2]
                elif span_id.startswith(prefix + 'telLabel_'):
                    role.tel = content
                elif span_id.startswith(prefix + 'lblEmail_'):
                    for a_el in a_elements:
                        if 'id' in a_el.attrs and a_el.attrs['id'].startswith(prefix + 'linkemail_'):
                            if a_el.contents:
                                role.email = a_el.contents[0].replace('[at]', '@')
                    question_details.addRole(role)
                    role = Role()

    return question_details


# ---------------------------------------------------------------------------
# Study group structure
# ---------------------------------------------------------------------------

def get_study_group(group=None, start=None):
    """Fetch the SG organizational hierarchy (WPs and Questions).

    Args:
        group: Study group number
        start: Start date string (YYYY/MM/DD)

    Returns:
        StudyGroupStructure object.
    """
    year = int(start[:4])
    period = str(int((year - 1953) / 4))
    url = (f"https://www.itu.int/net4/ITU-T/lists/sgstructure.aspx"
           f"?Group={group}&Period={period}")

    response = _fetch_url(url, encoding='utf-8')
    soup = BeautifulSoup(response, "html.parser")

    sg = StudyGroupStructure(group=group)
    current_wp = None
    current_q = None

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not isinstance(rows, list):
            continue
        for i in range(1, len(rows)):
            row = rows[i]
            for td in row.find_all("td"):
                wp = None
                wp_title = None
                title = None
                question = None

                spans = td.find_all("span")
                if not (isinstance(spans, list) and spans):
                    continue

                for span in spans:
                    if 'id' not in span.attrs:
                        continue
                    span_id = span.attrs['id']

                    if 'lblQWP_' in span_id and question is None:
                        strongs = span.find_all("strong")
                        if strongs and strongs[0].contents:
                            question = str(strongs[0].contents[0])
                            if question.startswith('Q'):
                                pos = question.find('/')
                                number = int(question[1:pos])
                                current_q = QuestionStructure(number=number)
                                if current_wp is not None:
                                    current_wp.questions.append(current_q)
                            else:
                                current_q = None

                    elif 'lblBlk' in span_id and wp is None:
                        strongs = span.find_all("strong")
                        if strongs and strongs[0].contents:
                            wp = str(strongs[0].contents[0])
                            if wp.startswith('WP'):
                                pos = wp.find('/')
                                number = int(wp[2:pos])
                                current_wp = WorkingPartyStructure(number=number)
                                sg.workingParties.append(current_wp)
                            else:
                                current_wp = None

                    elif 'lblQuestion' in span_id:
                        strongs = span.find_all("strong")
                        if not strongs and title is None:
                            title = str(span.contents[0])
                            if current_q is not None:
                                current_q.title = title
                        if strongs and wp_title is None and strongs[0].contents:
                            wp_title = str(strongs[0].contents[0])
                            if current_wp is not None:
                                current_wp.title = wp_title

    return sg


# ---------------------------------------------------------------------------
# Working party management
# ---------------------------------------------------------------------------

def get_working_party(group=None, working_party=None, questions=None, start=None):
    """Fetch working party leadership data from ITU management page.

    Args:
        group: Study group number
        working_party: Working party number
        questions: List of question structures
        start: Start date string (YYYY/MM/DD)

    Returns:
        WorkingParty object with roles.
    """
    wp_details = WorkingParty(
        group=group, workingParty=working_party, questions=questions
    )
    wp_name = f"WP{working_party}/{group}"

    year = int(start[:4])
    period = str(int((year - 1953) / 4))
    url = (f"https://www.itu.int/net4/ITU-T/lists/mgmt.aspx"
           f"?Group={group}&Period={period}")

    response = _fetch_url(url, encoding='utf-8')
    soup = BeautifulSoup(response, "html.parser")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not isinstance(rows, list):
            continue
        for i in range(1, len(rows)):
            row = rows[i]
            first_name = last_name = wp = title = None
            sub_role = company = address = tel = email = None

            for td in row.find_all("td"):
                for span in td.find_all("span"):
                    if 'id' not in span.attrs or not span.contents:
                        continue
                    span_id = span.attrs['id']
                    for content in span.contents:
                        if str(content) == '<br/>':
                            continue
                        s = str(content)
                        if "lblFName" in span_id:
                            first_name = s
                        elif "lblLName" in span_id:
                            last_name = s
                        elif "lblWP" in span_id:
                            wp = s
                        elif "lblTitle" in span_id:
                            title = s
                        elif "lblSubrole" in span_id:
                            sub_role = s
                        elif "lblCompany" in span_id:
                            company = s
                        elif "lblAddress" in span_id:
                            address = s
                        elif "lblTel" in span_id:
                            tel = s

                for a_el in td.find_all("a"):
                    if 'id' in a_el.attrs and "Email" in a_el.attrs['id']:
                        email = str(a_el.contents[0]).replace('[at]', '@')

            if title and first_name and last_name:
                role = Role(
                    roleName=title, firstName=first_name, lastName=last_name,
                    company=company, address=address, email=email, tel=tel
                )
                if wp is not None and wp.lower() == wp_name.lower():
                    wp_details.addRole(role)
                elif wp is None or wp.strip() == '':
                    # SG-level roles (Counsellor, Project officer, etc.)
                    wp_details.sg_roles.append(role)

    return wp_details


# ---------------------------------------------------------------------------
# Work programme
# ---------------------------------------------------------------------------

_WP_SEARCH_URL = "https://www.itu.int/ITU-T/workprog/wp_search.aspx"

_TABULAR_HEADERS = [
    'Work item', 'Question', 'Equiv. Num.', 'Status', 'Timing',
    'Approval process', 'Version', 'Liaison relationship',
    'Subject / Title', 'Priority',
]


def get_work_programme(group=None, question=None, working_party=None, start=None):
    """Fetch work programme items from the public ITU work programme page.

    Discovers ISN parameters dynamically, then scrapes the tabular view.

    Args:
        group: Study group number (e.g. 17)
        question: Question number (e.g. 11), or None for all questions
        working_party: Working party number (e.g. 1)
        start: Start date string (YYYY/MM/DD)

    Returns:
        List of WorkItem objects, or empty list on error.
    """
    year = int(start[:4])

    # Step 1: Discover Study Period and Study Group ISNs
    html = _fetch_url(_WP_SEARCH_URL, encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    isn_sp = _find_dropdown_isn(soup, 'study_period', str(year))
    isn_sg = _find_dropdown_isn(soup, 'study_group', f'SG{group}:')
    if isn_sp is None or isn_sg is None:
        print(f"Could not find ISN for study period {year} or SG{group}")
        return []

    # Step 2: Discover WP and Question ISNs
    url2 = f"{_WP_SEARCH_URL}?isn_sp={isn_sp}&isn_sg={isn_sg}"
    html2 = _fetch_url(url2, encoding='utf-8')
    soup2 = BeautifulSoup(html2, 'html.parser')

    isn_wp = _find_dropdown_isn(soup2, 'working_party', f'WP{working_party}/{group}:')
    if isn_wp is None:
        print(f"Could not find ISN for WP{working_party}/{group}")
        return []

    # Question is optional: use -1 for "any question" (all questions under the WP)
    isn_qu = '-1'
    if question is not None:
        isn_qu = _find_dropdown_isn(soup2, 'question', f'Q{question}/{group}:')
        if isn_qu is None:
            print(f"Could not find ISN for Q{question}/{group}")
            return []

    # Step 3: Fetch with all ISNs and parse the tabular view table
    url3 = (f"{_WP_SEARCH_URL}?isn_sp={isn_sp}&isn_sg={isn_sg}"
            f"&isn_wp={isn_wp}&isn_qu={isn_qu}")
    html3 = _fetch_url(url3, encoding='utf-8')
    soup3 = BeautifulSoup(html3, 'html.parser')

    work_items = _parse_work_programme_table(soup3)

    # Extract detail page links from the entire page (wp_item.aspx?isn=X)
    # and match them to work items by name
    detail_links = {}
    for a_tag in soup3.find_all('a'):
        href = a_tag.get('href', '')
        if 'wp_item.aspx?isn=' in href:
            text = a_tag.get_text().strip()
            if text:
                detail_links[text] = href
    if detail_links:
        print(f"  Found {len(detail_links)} detail page links: {list(detail_links.keys())[:5]}...")
    else:
        print(f"  No detail page links found on search results page")
    matched = 0
    for wi in work_items:
        if not wi.detailLink and wi.workItem:
            wi.detailLink = detail_links.get(wi.workItem, '')
            if wi.detailLink:
                matched += 1
    if detail_links:
        print(f"  Matched {matched}/{len(work_items)} work items to detail links")

    return work_items


def _find_dropdown_isn(soup, dropdown_name, match_prefix):
    """Find an ISN value from a <select> dropdown by matching option text."""
    for select in soup.find_all('select'):
        sel_id = select.get('id', '')
        if dropdown_name not in sel_id:
            continue
        for option in select.find_all('option'):
            text = option.get_text().strip()
            value = option.get('value', '-1')
            if value == '-1':
                continue
            if text.startswith(match_prefix):
                return value
    return None


def _parse_work_programme_table(soup):
    """Parse the tabular view table from the work programme page."""
    work_items = []

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        # Find the header row matching our expected columns
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            texts = [c.get_text().strip() for c in cells]
            if texts == _TABULAR_HEADERS:
                # Parse data rows after the header
                for data_row in rows[row_idx + 1:]:
                    data_cells = data_row.find_all(['td', 'th'])
                    vals = [c.get_text().strip() for c in data_cells]
                    if len(vals) < 10:
                        continue
                    # Extract detail page link from work item name cell
                    link_tag = data_cells[0].find('a') if data_cells else None
                    detail_link = link_tag.get('href', '') if link_tag else ''
                    wi = WorkItem(
                        workItem=vals[0],
                        question=vals[1],
                        title=vals[8],
                        timing=vals[4],
                        group=None,
                        period=None,
                        version=vals[6],
                        status=vals[3],
                        approvalProcess=vals[5],
                        equivNum=vals[2],
                        detailLink=detail_link,
                    )
                    work_items.append(wi)
                return work_items

    return work_items


def get_work_item_editors(work_item_details, max_workers=8):
    """Fetch editor names from individual work item detail pages.

    Scrapes each work item's detail page (wp_item.aspx?isn=X) to extract
    editor names from the Contact(s) section. Uses parallel requests for speed.

    Returns:
        dict: work_item_name -> "Editor1, Editor2"
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    items_with_links = [wi for wi in work_item_details if wi.detailLink]
    if not items_with_links:
        return {}

    editors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_wi = {
            pool.submit(_fetch_one_editor, wi): wi
            for wi in items_with_links
        }
        for future in as_completed(future_to_wi):
            wi = future_to_wi[future]
            try:
                names = future.result()
            except Exception as e:
                print(f"    editors for {wi.workItem} = [fetch failed: {e}]")
                continue
            if names:
                editors[wi.workItem] = ", ".join(names)
                print(f"    editors for {wi.workItem} = {', '.join(names)}")
            else:
                print(f"    editors for {wi.workItem} = [none found]")

    return editors


def _fetch_one_editor(wi):
    """Fetch editor names for a single work item. Returns list of name strings."""
    base_url = "https://www.itu.int/ITU-T/workprog/"
    if wi.detailLink.startswith('http'):
        url = wi.detailLink.replace('http://', 'https://')
    else:
        url = base_url + wi.detailLink

    html = _fetch_url(url, encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    names = []

    # Strategy 1: Find the Contact(s) row
    contact_cell = None
    for td in soup.find_all('td'):
        td_text = td.get_text().strip()
        if td_text.startswith('Contact'):
            tr = td.find_parent('tr')
            if tr:
                siblings = tr.find_all('td')
                for sib in siblings:
                    if sib != td:
                        contact_cell = sib
                        break
            break

    if contact_cell:
        for span in contact_cell.find_all('span'):
            text = span.get_text().strip()
            if ', Editor' in text:
                name = text[:text.rfind(', Editor')].strip()
                if name:
                    names.append(name)

    # Strategy 2: Fallback — search all spans on the page
    if not names:
        for span in soup.find_all('span'):
            text = span.get_text().strip()
            if text.endswith(', Editor'):
                name = text[:-len(', Editor')].strip()
                if name:
                    names.append(name)

    return names


# ---------------------------------------------------------------------------
# Next SG meeting info
# ---------------------------------------------------------------------------

def get_next_sg_meeting(group, after_date=None):
    """Scrape the ITU SG page to find the next full SG meeting.

    Looks for entries titled "SGxx meeting" (not Content Week, Plenary, or WP)
    on the SG's main page and extracts city and date range.

    Args:
        group: Study group number (e.g. 17)
        after_date: datetime — only return meetings after this date (optional)

    Returns:
        dict with 'city', 'country', 'date_range', 'start_date', 'end_date'
        or None if not found.
    """
    import re
    from datetime import datetime

    url = (f"https://www.itu.int/en/ITU-T/studygroups/"
           f"2025-2028/{group}/Pages/default.aspx")
    try:
        html = _fetch_url(url)
    except Exception as e:
        print(f"  Warning: could not fetch SG{group} page: {e}")
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Look for spans/strongs with "SGxx meeting" (exact — not Content Week,
    # Plenary, WP, or photos)
    pattern = re.compile(rf'\bSG\s*{group}\s+meeting\b', re.IGNORECASE)
    exclude = re.compile(r'(content week|plenary|photo|WP\d)', re.IGNORECASE)

    for tag in soup.find_all(['span', 'strong'], string=pattern):
        text = tag.get_text(strip=True)
        if exclude.search(text):
            continue

        # The location/date is typically in the next sibling span or in the
        # parent's text, formatted as: ",City, DD-DD Month YYYY"
        parent = tag.parent
        if parent is None:
            continue
        full_text = parent.get_text(strip=True)
        # Remove zero-width spaces
        full_text = full_text.replace('\u200b', '')

        # Extract "City, DD-DD Month YYYY" or "City, D Month YYYY"
        m = re.search(
            r',\s*([A-Za-z\s]+?),\s*'
            r'(\d{1,2}(?:\s*-\s*\d{1,2})?)\s+'
            r'([A-Za-z]+)\s+'
            r'(\d{4})',
            full_text
        )
        if not m:
            continue

        city = m.group(1).strip()
        day_range = m.group(2).strip()
        month_str = m.group(3).strip()
        year = m.group(4).strip()

        # Parse start date for comparison
        start_day = day_range.split('-')[0].strip()
        try:
            start_date = datetime.strptime(
                f"{start_day} {month_str} {year}", "%d %B %Y")
        except ValueError:
            continue

        if after_date and start_date <= after_date:
            continue

        # Parse end date if present
        end_date = start_date
        if '-' in day_range:
            end_day = day_range.split('-')[1].strip()
            try:
                end_date = datetime.strptime(
                    f"{end_day} {month_str} {year}", "%d %B %Y")
            except ValueError:
                pass

        return {
            'city': city,
            'country': 'Switzerland' if city.lower() == 'geneva' else '',
            'date_range': f"{day_range} {month_str} {year}",
            'start_date': start_date,
            'end_date': end_date,
        }

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_url(url, encoding='utf-8'):
    """Fetch a URL using pycurl and return decoded response."""
    request = pycurl.Curl()
    request.setopt(request.URL, url)
    buf = BytesIO()
    request.setopt(request.WRITEDATA, buf)
    request.perform()
    return buf.getvalue().decode(encoding)


def _clean(value):
    """Remove non-printable characters (< 32) from a string."""
    return ''.join(ch for ch in str(value) if ord(ch) >= 32)


def _parse_html_tables(html):
    """Parse all HTML tables into Table objects."""
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for html_table in soup.find_all("table"):
        table = Table()
        for html_row in html_table.find_all("tr"):
            row = Row()
            for td in html_row.find_all("td"):
                column = Column()

                for a in td.find_all("a"):
                    href = a.attrs.get('href')
                    strong_texts = [
                        s.contents[0] for s in a.find_all("strong") if s.contents
                    ]
                    a_el = AElement(href=href, strongElements=strong_texts, contents=a.contents)
                    column.aElements.append(a_el)

                for font in td.find_all("font"):
                    column.fontElements.append(font.contents)

                for strong in td.find_all("strong"):
                    column.strongElements.append(strong.contents)

                column.contents = td.contents
                row.columns.append(column)
            table.rows.append(row)
        tables.append(table)
    return tables


def _is_document_table(table):
    """Check if a parsed Table is the meeting documents table (has Number/Title/Source/AI headers)."""
    if len(table.rows) < 2:
        return False
    row = table.rows[1]
    if len(row.columns) < 6:
        return False

    expected = {1: 'Number', 2: 'Title', 3: 'Source', 4: 'AI/Question'}
    for col_idx, text in expected.items():
        col = row.columns[col_idx]
        if (not col.strongElements or not col.strongElements[0] or
                col.strongElements[0][0] != text):
            return False
    return True
