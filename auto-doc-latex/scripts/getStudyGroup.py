import pycurl
import os
import sys
from io import BytesIO
from bs4 import BeautifulSoup
from getQuestion import Role
debug = True
sys.stdout.reconfigure(encoding = 'utf-8')

class QuestionStructure(object):
    def __init__(self,number,title):
        self.number = number
        self.title = title
    def dump(self):
        print("question " + str(self.number) + ": " + str(self.title))

class WorkingPartyStructure(object):
    def __init__(self,number,title):
        self.number = number
        self.title = title
        self.questions = []
    def dump(self):
        print("workingParty " + str(self.number) + ": " + str(self.title))
        for question in self.questions:
            question.dump()

class StudyGroupStructure(object):
    def __init__(self,group,title = None):
        self.group = group
        self.title = title
        self.workingParties = []
    def dump(self):
        print("group " + str(self.group) + ": " + str(self.title))
        for workingParty in self.workingParties:
            workingParty.dump()

def getStudyGroup(group = None,start = None):
    studyGroupDetails = StudyGroupStructure(group = group,title = None)
    year = int(start[:4])
    period = str(int((int(year) - 1953) / 4))
    urlString = 'https://www.itu.int/net4/ITU-T/lists/sgstructure.aspx'
    url = urlString + '?Group=' + str(group) + '&Period=' + period
    request = pycurl.Curl()
    request.setopt(request.URL,url)
    buffer = BytesIO()
    request.setopt(request.WRITEDATA,buffer)
    response = None
    request.perform()
    response = buffer.getvalue().decode('utf-8')
    soup = BeautifulSoup(response,"html.parser")
    tables = soup.find_all("table")
    selectedTable = None
    firstRow = None
    lastRow = None
    workingPartyDetails = None
    questionDetails = None
    for table in tables:
        rows = table.find_all("tr")
        if isinstance(rows,list):
            for i in range(1,len(rows)):
                row = rows[i]
                tds = row.find_all("td")
                if isinstance(tds,list):
                    for td in tds:
                        wp = None
                        wpTitle = None
                        title = None
                        question = None
                        aElements = td.find_all("a")
                        spans = td.find_all("span")
                        if isinstance(spans,list) and len(spans) > 0:
                            for span in spans:
                                if 'id' in span.attrs:
                                    id = span.attrs['id']
                                    if 'lblQWP_' in id and question is None:
                                        strongs = span.find_all("strong")
                                        if len(strongs) > 0:
                                            contents = strongs[0].contents
                                            if len(contents) > 0:
                                                question = str(contents[0])
                                                if question.startswith('Q'):
                                                    position = question.find('/')
                                                    number = int(question[1:position])
                                                    questionDetails = QuestionStructure(number = number,title = None)
                                                    if not workingPartyDetails is None:
                                                        workingPartyDetails.questions.append(questionDetails)
                                                else:
                                                    questionDetails = None
                                    elif 'lblBlk' in id and wp is None:
                                        strongs = span.find_all("strong")
                                        if len(strongs) > 0:
                                            contents = strongs[0].contents
                                            if len(contents) > 0:
                                                wp = str(contents[0])
                                                if wp.startswith('WP'):
                                                    position = wp.find('/')
                                                    number = int(wp[2:position])
                                                    workingPartyDetails = WorkingPartyStructure(number = number,title = None)
                                                    studyGroupDetails.workingParties.append(workingPartyDetails)
                                                else:
                                                    workingPartyDetails = None
                                    elif 'lblQuestion' in id:
                                        strongs = span.find_all("strong")
                                        if len(strongs) == 0 and title is None:
                                            title = str(span.contents[0])
                                            if not questionDetails is None:
                                                questionDetails.title = title
                                        if len(strongs) > 0 and wpTitle is None:
                                            contents = strongs[0].contents
                                            if len(contents) > 0:
                                                wpTitle = str(contents[0])
                                                if not workingPartyDetails is None:
                                                    workingPartyDetails.title = wpTitle
    return studyGroupDetails
