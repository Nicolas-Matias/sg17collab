import pycurl
import os
from io import BytesIO
from bs4 import BeautifulSoup
from commonFunctions import *

debug = False

class ValueAndLink(object):
    def __init__(self,value = None,link = None):
        if debug:
            print("ValueAndLink " + str(value) + " " + str(link))
        if value is None:
            self.value = ""
        else:
            name = ""
            lastCharacter = 0
            for character in value:
                if character == ' ':
                    if lastCharacter != ' ':
                        name = name + character
                        lastCharacter = character
                elif character != '[' and character != ']':
                    name = name + character
                    lastCharacter = character
            self.name = name
            index = name.find('-')
            if index > 0:
                self.value = name[:index]
            else:
                self.value = name
        if link is None:
            self.link = ""
        else:
            self.link = link
    def dump(self):
        print("value " + str(self.value))
        print("link " + str(self.link))

class TableRow(object):
    def __init__(self,number = None,rev = "",title = None,source = None,questions = None):
        self.number = number
        if rev is None:
            self.rev = ""
            self.lastRev = ""
        else:
            self.rev = rev
            index = rev.find("-")
            if index > 0:
                self.lastRev = "R" + rev[index + 1:-1]
            else:
                index = rev.find(".")
                if index > 0:
                    self.lastRev = "R" + rev[index + 1:-1]
                else:
                    self.lastRev = ""
        self.title = title
        (documentType,recommendation,acronym,textTitle) = splitTitle(self.title)
        self.documentType = documentType
        self.recommendation = recommendation
        self.acronym = acronym
        self.textTitle = textTitle
        self.source = source
        if questions is None:
            self.questions = []
        else:
            self.questions = questions
    def dump(self):
        if not self.number is None:
            print("number " + str(self.number.value) + " " + str(self.number.link))
        print("rev " + str(self.rev))
        print("lastRev " + str(self.lastRev))
        print("title " + str(self.title))
        print("documentType " + str(self.documentType))
        print("recommendation " + str(self.recommendation))
        print("acronym " + str(self.acronym))
        print("textTitle " + str(self.textTitle))
        if not self.source is None:
            print("source " + str(self.source.value) + " " + str(self.source.link))
        print("questions ")
        for question in self.questions:
            print("\t " + str(question.value) + " " + str(question.link))

class AElement(object):
    def __init__(self,href = None,strongElements = None,contents = None):
        self.href = href
        if strongElements is None:
            self.strongElements = []
        else:
            self.strongElements = strongElements
        if contents is None:
            self.contents = []
        else:
            self.contents = contents
    def dump(self):
        if not self.href is None:
            print("href of AElement " + str(self.href))
        if not self.strongElements is None:
            print("strong elements of a element")
            for strongElement in self.strongElements:
                print("\t" + str(strongElement))
        if not self.contents is None:
            print("contents of a element")
            for content in self.contents:
                print("\t" + str(content))

class Column(object):
    def __init__(self,aElements = None,fontElements = None,strongElements = None,contents = None):
        if aElements is None:
            self.aElements = []
        else:
            self.aElements = aElements
        if fontElements is None:
            self.fontElements = []
        else:
            self.fongElements = fontElements
        if strongElements is None:
            self.strongElements = []
        else:
            self.strongElements = strongElements
        self.contents = contents
    def dump(self):
        print("aElements")
        for aElement in self.aElements:
            aElement.dump()
        print("fontElements")
        for fontElement in self.fontElements:
            print("\t" + str(fontElement))
        print("strongElements")
        for strongElement in self.strongElements:
            for content in strongElement:
                print(content)
        print("contents ")
        for content in self.contents:
            print(content)

class Row(object):
    def __init__(self):
        self.columns = []
    def dump(self):
        print("-- Row -- " + str(len(self.columns)) + " columns")
        num = 0
        for column in self.columns:
            print("--- Column " + str(num) + " ---")
            column.dump()
            num = num + 1

class Table(object):
    def __init__(self):
        self.rows = []
    def dump(self):
        print("-- Table " + str(len(self.rows)) + " rows")
        for row in self.rows:
            row.dump()

def clean(value):
    string = str(value)
    newString = ""
    for character in string:
        if ord(character) >= 32:
            newString = newString + character
    return newString

def splitTitle(title):
    documentType = ""
    recommendation = ""
    acronym = ""
    textTitle = ""
    index1 = title.find(' - ')
    if index1 >= 0:
        documentType = title[:index1]
        if documentType == 'Approval' or documentType == 'Determination':
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
        elif documentType == 'Consent':
            index2 = title.find(':')
            if index2 >= 0:
                acronym = title[index1 + 3:index2]
                textTitle = title[index2 + 2:]
        elif documentType == 'Agreement':
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
        textTitle = textTitle[1:len(textTitle) - 1]
    return (documentType,recommendation,acronym,textTitle)

def getDocuments(documentType = None,group = None,workingParty = None,questions = None,start = None):
    year = int(start[2:4])
    period = str(int(year / 4) * 4 + 1)
    urlString = 'https://www.itu.int/md/meetingdoc.asp?lang=en&parent=T' + period + '-SG' + str(group) + '-' + start[2:] + '-'
    if documentType == 'C':
        urlString = urlString + 'C'
    elif documentType == 'GEN':
        urlString = urlString + 'TD-GEN'
    elif documentType == 'PLEN':
        urlString = urlString + 'TD-PLEN'
    elif documentType == 'WP':
        urlString = urlString + 'TD-WP' + str(workingParty)
    else:
        return None
    questionNames = []
    allQuestionsName = 'QALL/' + str(group)
    if not questions is None:
        if isinstance(questions,list):
            for question in questions:
                questionName = 'Q' + str(question) + '/' + str(group)
                questionNames.append(questionName)
        else:
            if isinstance(questions,int):
                urlString = urlString + '&question=Q' + str(questions) + '/' + str(group)
            else:
                urlString = urlString + '&question=QALL/' + str(group)
    first = 0
    tableRows = []
    while True:
        request = pycurl.Curl()
        url = urlString + "&PageLB=" + str(first)
        request.setopt(request.URL,url)
        buffer = BytesIO()
        request.setopt(request.WRITEDATA,buffer)
        response = None
        request.perform()
        response = buffer.getvalue().decode('iso8859-2')
        tables = getTables(response)
        nrows = 0
        for table in tables:
            if debug:
                table.dump()
            if checkTable(table):
                nrows = len(table.rows) - 3
                if nrows <= 0:
                    break
                first = first + nrows
                for i in range(2,len(table.rows) - 1):
                    row = table.rows[i]
                    num = 0
                    number = None
                    rev = None
                    title = None
                    source = None
                    relatedQuestions = None
                    for column in row.columns:
                        if debug:
                            print("column " + str(num))
                            column.dump()
                        if num == 1:
                            if debug:
                                print("---number---")
                            if len(column.aElements) > 0:
                                value = None
                                if len(column.aElements[0].strongElements) > 0:
                                    value = column.aElements[0].strongElements[0]
                                elif len(column.aElements[0].contents) > 0:
                                    value = clean(column.aElements[0].contents[0])
                                href = column.aElements[0].href
                                number = ValueAndLink(value,href)
                                if debug:
                                    number.dump()
                            if len(column.fontElements) > 0:
                                rev = column.fontElements[0][0]
                        elif num == 2:
                            if debug:
                                print("title")
                            if len(column.contents) > 0:
                                index = column.contents[0].find("\r")
                                if index < 0:
                                    title = column.contents[0]
                                else:
                                    title = column.contents[0][:index]
                                index = title.find("[from ")
                                if index >= 0:
                                    title = title[:index]
                        elif num == 3:
                            if debug:
                                print("source")
                            if len(column.aElements) > 0:
                                source = ValueAndLink(column.aElements[0].contents[0],column.aElements[0].href)
                        elif num == 4:
                            if debug:
                                print("relatedQuestions")
                            relatedQuestions = []
                            for aElement in column.aElements:
                                question = ValueAndLink(aElement.contents[0],aElement.href)
                                relatedQuestions.append(question)
                        num = num + 1
                    selectedRow = False
                    if isinstance(questions,list):
                        for question in relatedQuestions:
                            if question.name == allQuestionsName:
                                selectedRow = True
                                break
                            else:
                                for questionName in questionNames:
                                    if questionName == question.name:
                                        selectedRow = True
                            if selectedRow:
                                break
                    else:
                        selectedRow = True
                    if selectedRow:
                        tableRow = TableRow(number = number,rev = rev,title = title,source = source,questions = relatedQuestions)
                        tableRows.append(tableRow)
        if nrows <= 0:
            break
    return tableRows

def getTables(string = None):
    newTables = []
    soup = BeautifulSoup(string,"html.parser")
    tables = soup.find_all("table")
    if debug:
        print(str(type(tables)) + " tables")
    for table in tables:
        newTable = Table()
        rows = table.find_all("tr")
        if debug:
            print(str(len(rows)) + " rows")
        for row in rows:
            newRow = Row()
            tds = row.find_all("td")
            if debug:
                print(str(len(tds)) + " columns")
            for td in tds:
                column = Column()
                elements = td.find_all("a")
                if debug:
                    print(str(len(elements)) + " a")
                for element in elements:
                    attrs = element.attrs
                    if 'href' in attrs:
                        href = attrs['href']
                    else:
                        href = None
                    strongElements = element.find_all("strong")
                    if debug:
                        print(str(len(strongElements)) + " strong in a")
                    aStrongElements = []
                    for strongElement in strongElements:
                        if len(strongElement.contents):
                            aStrongElements.append(strongElement.contents[0])
                    aElement = AElement(href = href,strongElements = aStrongElements,contents = element.contents)
                    column.aElements.append(aElement) 
                fontElements = td.find_all("font")
                if debug:
                    print(str(len(fontElements)) + " font")
                for fontElement in fontElements:
                    column.fontElements.append(fontElement.contents)
                strongElements = td.find_all("strong")
                if debug:
                    print(str(len(strongElements)) + " strong")
                for strongElement in strongElements:
                    column.strongElements.append(strongElement.contents)
                column.contents = td.contents
                newRow.columns.append(column)
            newTable.rows.append(newRow)
        newTables.append(newTable)
    return newTables

def checkTable(table):
    if len(table.rows) < 2:
        return False
    row = table.rows[1]
    if len(row.columns) < 6:
        return False
    column = row.columns[1]
    if len(column.strongElements) == 0 or len(column.strongElements[0]) == 0 or column.strongElements[0][0] != 'Number':
        return False
    column = row.columns[2]
    if len(column.strongElements) == 0 or len(column.strongElements[0]) == 0 or column.strongElements[0][0] != 'Title':
        return False
    column = row.columns[3]
    if len(column.strongElements) == 0 or len(column.strongElements[0]) == 0 or column.strongElements[0][0] != 'Source':
        return False
    column = row.columns[4]
    if len(column.strongElements) == 0 or len(column.strongElements[0]) == 0 or column.strongElements[0][0] != 'AI/Question':
        return False
    return True
    
def getDocumentTitle(tableRows = None,number = None):
    for tableRow in tableRows:
        if tableRow.number.value == number:
            return tableRow.title
    return ""

def getLiaisonDestination(tableRows = None,number = None):
    for tableRow in tableRows:
        if tableRow.number.value == number:
            title = tableRow.title
            index1 = title.find('[to')
            if index1 >= 0:
                index2 = title.find(']',index1)
                if index2 > index1:
                    return title[index1 + 1:index2]
    return ""

def getMeetingReports(tableRows = None,question = None,group = None):
    meetingReports = []
    for tableRow in tableRows:
        title = tableRow.title
        strippedTitle = title.replace(' ','')
        if strippedTitle.startswith("ReportofQ" + str(question) + "/" + str(group)) and "RapporteurGroupMeeting" in strippedTitle:
            meetingReports.append(tableRow)
    return meetingReports
