import pycurl
import os
import sys
from io import BytesIO
from bs4 import BeautifulSoup

debug = True
sys.stdout.reconfigure(encoding = 'utf-8')
class Role(object):
    def __init__(self,roleName = None,firstName = None,lastName = None,company = None,address = None,email = None,tel = None):
        if roleName is None:
            self.roleName = ''
        else:
            self.roleName = roleName
        if firstName is None:
            self.firstName = ''
        else:
            self.firstName = firstName
        if lastName is None:
            self.lastName = ''
        else:
            self.lastName = lastName
        if company is None:
            self.company = ''
        else:
            self.company = company
        if address is None:
            self.address = ''
        else:
            self.address = address
        if email is None:
            self.email = ''
        else:
            self.email = email
        if tel is None:
            self.tel = ''
        else:
            self.tel = tel
    def dump(self):
        print("-- Role " + str(self.roleName))
        print("name " + str(self.firstName) + " " + str(self.lastName))
        print("company " + str(self.company))
        print("address " + str(self.address))
        print("email " + str(self.email))
        print("tel " + str(self.tel))

class Question(object):
    def __init__(self,group = None,workingParty = None,question = None,title = None):
        self.group = group
        self.workingParty = workingParty
        self.question = question
        self.title = title
        self.roles = []
    def addRole(self,role):
        self.roles.append(role)
    def dump(self):
        print("-- Group " + str(self.group) + " workingParty " + str(self.workingParty) + " question " + str(self.question))
        print("title " + str(self.title))
        for role in self.roles:
            role.dump()

def getQuestion(group = None,question = None,start = None):
    questionDetails = None
    year = int(start[:4])
    period = str(int((int(year) - 1953) / 4))
    urlString = 'https://www.itu.int/net4/ITU-T/lists/loqr.aspx'
    url = urlString + '?Group=' + str(group) + '&Period=' + period
    questionName = 'Q' + str(question) + '/' + str(group)
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
    prefix = 'ContentPlaceHolder1_dtlRappQues_'
    for table in tables:
        rows = table.find_all("tr")
        if isinstance(rows,list):
            for i in range(0,len(rows)):
                row = rows[i]
                tds = row.find_all("td")
                if isinstance(tds,list):
                    for td in tds:
                        spans = td.find_all("span")
                        if isinstance(spans,list) and len(spans) > 0:
                            if 'id' in spans[0].attrs:
                                id = spans[0].attrs['id']
                                if id.startswith(prefix + 'lblQWP_') or i == len(rows) - 1:
                                    if selectedTable is None:
                                        contents = spans[0].contents
                                        if isinstance(contents,list) and len(contents) > 0:
                                            if contents[0].startswith(questionName):
                                                selectedTable = table
                                                firstRow = i
                                    else:
                                        lastRow = i
                                        break
                if not lastRow is None:
                    break
        if not lastRow is None:
            break
    if not lastRow is None:
        questionDetails = Question(group = group,question = question)
        rows = selectedTable.find_all("tr")
        for i in range(firstRow,lastRow):
            row = rows[i]
            tds = row.find_all("td")
            role = Role()
            for td in tds:
                spans = td.find_all("span")
                aElements = td.find_all("a")
                for span in spans:
                    if 'id' in span.attrs:
                        id = span.attrs['id']
                        if len(span.contents) > 0:
                            content = span.contents[0]
                            if id.startswith(prefix + 'lblQWP_'):
                                index1 = content.find('(WP')
                                if index1 >= 0:
                                    index2 = content.find('/',index1 + 3)
                                    if index2 > 0:
                                        string = content[index1 + 3:index2]
                                        try:
                                            workingParty = int(string)
                                            questionDetails.workingParty = workingParty
                                        except:
                                            pass
                            elif id.startswith(prefix + 'lblQuestion69_'):
                                questionDetails.title = content
                            elif id.startswith(prefix + 'lblFName_'):
                                role.firstName = content
                            elif id.startswith(prefix + 'lblLName_'):
                                role.lastName = content
                            elif id.startswith(prefix + 'lblRole_'):
                                role.roleName = content
                            elif id.startswith(prefix + 'lblCompany_'):
                                role.company = content
                            elif id.startswith(prefix + 'lblAddress_'):
                                if len(span.contents) > 1:
                                    role.address = span.contents[len(span.contents) - 2]
                            elif id.startswith(prefix + 'telLabel_'):
                                role.tel = content
                            elif id.startswith(prefix + 'lblEmail_'):
                                for aElement in aElements:
                                    if 'id' in aElement.attrs:
                                        id = aElement.attrs['id']
                                        if id.startswith(prefix + 'linkemail_'):
                                            if len(aElement.contents) > 0:
                                                role.email = aElement.contents[0].replace('[at]','@')
                                questionDetails.addRole(role)
                                role = Role()
    return questionDetails

def getRapporteurs(questionDetails):
    rapporteurs = []
    for role in questionDetails.roles:
        if role.roleName == "Rapporteur":
            rapporteur = role.firstName + " " + role.lastName + " (" + role.company + ", " + role.address + ")"
            rapporteurs.append(rapporteur)
        elif role.roleName == "Co-rapporteur":
            first = False
            rapporteur = role.firstName + " " + role.lastName + " (" + role.company + ", " + role.address + ")"
            rapporteurs.append(rapporteur)
    return rapporteurs

def getAssociateRapporteurs(questionDetails):
    associateRapporteurs = []
    for role in questionDetails.roles:
        if role.roleName == "Associate rapporteur":
            rapporteur = role.firstName + " " + role.lastName + " (" + role.company + ", " + role.address + ")"
            associateRapporteurs.append(rapporteur)
    return associateRapporteurs
