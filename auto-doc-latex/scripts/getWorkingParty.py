import pycurl
import os
import sys
from io import BytesIO
from bs4 import BeautifulSoup
from getQuestion import *
debug = True
sys.stdout.reconfigure(encoding = 'utf-8')

class WorkingParty(object):
    def __init__(self,group = None,workingParty = None,title = None,questions = None):
        self.group = group
        self.workingParty = workingParty
        self.title = title
        if questions is None:
            self.questions = []
        else:
            self.questions = questions
        self.roles = []
    def addRole(self,role):
        self.roles.append(role)
    def dump(self):
        print("-- Group " + str(self.group) + " workingParty " + str(self.workingParty))
        print("title " + str(self.title))
        for question in self.questions:
            question.dump()
        for role in self.roles:
            role.dump()

def getWorkingParty(group = None,workingParty = None,questions = None,start = None):
    workingPartyDetails = WorkingParty(group = group,workingParty = workingParty,questions = questions,title = None)
    workingPartyName = "WP" + str(workingParty) + "/" + str(group)
    year = int(start[:4])
    period = str(int((int(year) - 1953) / 4))
    urlString = 'https://www.itu.int/net4/ITU-T/lists/mgmt.aspx'
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
    for table in tables:
        rows = table.find_all("tr")
        if isinstance(rows,list):
            for i in range(1,len(rows)):
                row = rows[i]
                tds = row.find_all("td")
                if isinstance(tds,list):
                    firstName = None
                    lastName = None
                    wp = None
                    title = None
                    subRole = None
                    company = None
                    address = None
                    tel = None
                    email = None
                    for td in tds:
                        spans = td.find_all("span")
                        if isinstance(spans,list) and len(spans) > 0:
                            for span in spans:
                                if 'id' in span.attrs:
                                    id = span.attrs['id']
                                    if len(span.contents) > 0:
                                        if "lblFName" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    firstName = str(content)
                                        elif "lblLName" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    lastName = str(content)
                                        elif "lblWP" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    wp = str(content)
                                        elif "lblTitle" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    title = str(content)
                                        elif "lblSubrole" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    subRole = str(content)
                                        elif "lblCompany" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    company = str(content)
                                        elif "lblAddress" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    address = str(content)
                                        elif "lblTel" in id:
                                            for content in span.contents:
                                                if str(content) != '<br/>':
                                                    tel = str(content)
                        aElements = td.find_all("a")
                        for aElement in aElements:
                            if 'id' in aElement.attrs:
                                id = aElement.attrs['id']
                                if "Email" in id:
                                    email = str(aElement.contents[0])
                                    email = email.replace('[at]','@')
                if not wp is None:
                    if wp.lower() == workingPartyName.lower():
                        role = Role(roleName = title,firstName = firstName,lastName = lastName,company = company,address = address,email = email,tel = tel)
                        workingPartyDetails.addRole(role)
    return workingPartyDetails

def getViceChairs(workingPartyDetails):
    chairs = []
    for role in workingPartyDetails.roles:
        if role.roleName == "Vice-chair":
            chair = role.firstName + " " + role.lastName + " (" + role.company + ", " + role.address + ")"
            chairs.append(chair)
    return chairs

def getChairs(workingPartyDetails):
    chairs = []
    for role in workingPartyDetails.roles:
        if role.roleName == "Chair" or role.roleName == "Co-Chair":
            chair = role.firstName + " " + role.lastName + " (" + role.company + ", " + role.address + ")"
            chairs.append(chair)
    return chairs
