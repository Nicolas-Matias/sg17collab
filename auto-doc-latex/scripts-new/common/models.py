"""Data classes for ITU document generation."""


class ValueAndLink:
    """A value (document number, question name, etc.) with an optional hyperlink."""

    def __init__(self, value=None, link=None):
        if value is None:
            self.value = ""
            self.name = ""
        else:
            # Clean whitespace: collapse multiple spaces, strip brackets
            name = ""
            last_char = 0
            for ch in value:
                if ch == ' ':
                    if last_char != ' ':
                        name += ch
                        last_char = ch
                elif ch not in ('[]'):
                    name += ch
                    last_char = ch
            self.name = name
            idx = name.find('-')
            self.value = name[:idx] if idx > 0 else name

        self.link = link if link else ""


class TableRow:
    """A row from the ITU meeting documents table."""

    def __init__(self, number=None, rev="", title=None, source=None, questions=None):
        self.number = number

        if rev is None:
            self.rev = ""
            self.lastRev = ""
        else:
            self.rev = rev
            idx = rev.find("-")
            if idx > 0:
                self.lastRev = "R" + rev[idx + 1:-1]
            else:
                idx = rev.find(".")
                if idx > 0:
                    self.lastRev = "R" + rev[idx + 1:-1]
                else:
                    self.lastRev = ""

        self.title = title
        self.documentType, self.recommendation, self.acronym, self.textTitle = split_title(self.title)
        self.source = source
        self.questions = questions if questions else []


class Role:
    """A person's role in an ITU study group (rapporteur, chair, etc.)."""

    def __init__(self, roleName=None, firstName=None, lastName=None,
                 company=None, address=None, email=None, tel=None):
        self.roleName = roleName or ''
        self.firstName = firstName or ''
        self.lastName = lastName or ''
        self.company = company or ''
        self.address = address or ''
        self.email = email or ''
        self.tel = tel or ''


class Question:
    """An ITU-T Question with its leadership roles."""

    def __init__(self, group=None, workingParty=None, question=None, title=None):
        self.group = group
        self.workingParty = workingParty
        self.question = question
        self.title = title
        self.roles = []

    def addRole(self, role):
        self.roles.append(role)


class WorkingParty:
    """An ITU-T Working Party with leadership and questions."""

    def __init__(self, group=None, workingParty=None, title=None, questions=None):
        self.group = group
        self.workingParty = workingParty
        self.title = title
        self.questions = questions if questions else []
        self.roles = []
        self.sg_roles = []

    def addRole(self, role):
        self.roles.append(role)


class QuestionStructure:
    """Question number and title within the SG hierarchy."""

    def __init__(self, number, title=None):
        self.number = number
        self.title = title


class WorkingPartyStructure:
    """WP number, title, and contained questions within the SG hierarchy."""

    def __init__(self, number, title=None):
        self.number = number
        self.title = title
        self.questions = []


class StudyGroupStructure:
    """Full SG hierarchy: study group -> working parties -> questions."""

    def __init__(self, group, title=None):
        self.group = group
        self.title = title
        self.workingParties = []


class WorkItem:
    """A work item from the ITU work programme."""

    def __init__(self, workItem=None, question=None, title=None, timing=None,
                 group=None, period=None, version=None, status=None,
                 approvalProcess=None, equivNum=None, detailLink=None):
        self.workItem = workItem
        self.question = question
        self.title = title
        self.timing = timing
        self.group = group
        self.period = period
        self.version = version
        self.status = status
        self.approvalProcess = approvalProcess
        self.equivNum = equivNum
        self.detailLink = detailLink or ''


# --- Internal HTML parsing classes (used by itu_api) ---

class AElement:
    """An <a> element parsed from HTML."""

    def __init__(self, href=None, strongElements=None, contents=None):
        self.href = href
        self.strongElements = strongElements or []
        self.contents = contents or []


class Column:
    """A <td> element parsed from HTML."""

    def __init__(self, aElements=None, fontElements=None, strongElements=None, contents=None):
        self.aElements = aElements or []
        self.fontElements = fontElements or []
        self.strongElements = strongElements or []
        self.contents = contents or []


class Row:
    """A <tr> element parsed from HTML."""

    def __init__(self):
        self.columns = []


class Table:
    """An HTML table parsed from a web page."""

    def __init__(self):
        self.rows = []


# --- Helper function used during model construction ---

def split_title(title):
    """Parse a document title into (documentType, recommendation, acronym, textTitle).

    Handles title formats:
      'Approval - X.1234: Title text'
      'Determination - X.1234 (acronym): Title text'
      'Consent - acronym: Title text'
      'Agreement - acronym: Title text'
      'Output - new work item X.abc: Title text'
    """
    documentType = ""
    recommendation = ""
    acronym = ""
    textTitle = ""

    index1 = title.find(' - ')
    if index1 >= 0:
        documentType = title[:index1]
        if documentType in ('Approval', 'Determination'):
            index2 = title.find(':')
            if index2 >= 0:
                recommendation = title[index1 + 3:index2]
                textTitle = title[index2 + 2:]
            else:
                index2 = title.find(' (')
                index3 = title.find('):')
                if index2 >= 0:
                    recommendation = title[index1 + 3:index2]
                    if index3 > 0:
                        acronym = title[index2 + 2:index3]
                        textTitle = title[index3 + 3:]
                else:
                    textTitle = title[index1 + 3:]
        elif documentType in ('Consent', 'Agreement'):
            index2 = title.find(':')
            if index2 >= 0:
                acronym = title[index1 + 3:index2]
                textTitle = title[index2 + 2:]
        elif documentType == 'Output':
            string = title[index1 + 3:]
            if string.startswith('new work item'):
                documentType = 'New work item'
                index2 = string.find(':')
                if index2 >= 0:
                    acronym = string[14:index2]
                    textTitle = string[index2 + 2:]
            else:
                index2 = string.find(':')
                if index2 >= 0:
                    acronym = string[9:index2]
                    textTitle = string[index2 + 2:]

    if textTitle.startswith('"') and textTitle.endswith('"'):
        textTitle = textTitle[1:-1]

    return (documentType, recommendation, acronym, textTitle)
