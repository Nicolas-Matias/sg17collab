import json
import os
import sys
import datetime
from getDocuments import *
from getQuestion import *
from getStudyGroup import *
from getWorkProgramme import *
from commonFunctions import *
URL = "https://www.itu.int"

verbose = 1
if len(sys.argv) < 2:
    print("usage " + sys.argv[0] + " meeting")
    sys.exit()
meeting = sys.argv[1]
try:
    fid = open(meeting,"r",encoding = "utf-8")
except Exception as e:
    print("Error while opening " + meeting + " (" + str(e) + ")")
    sys.exit()
try:
    jsonContent = fid.read()
except Exception as e:
    print("Error while reading " + meeting + " (" + str(e) + ")")
    sys.exit()
fid.close()
try:
    content = json.loads(jsonContent)
except Exception as e:
    print("Error while decoding " + meeting + " (" + str(e) + ")")
    sys.exit()
documentType = None
if 'documentType' in content:
    documentType = content['documentType']
if documentType != "agenda" and documentType != "report":
    print("Unknown document type " + documentType)
    sys.exit()
group = None
if 'group' in content:
    groupString = content['group']
    try:
        group = int(groupString)
    except Exception as e:
        print("Invalid group " + groupString)
        sys.exit()
question = None
if 'question' in content:
    questionString = content['question']
    try:
        question = int(questionString)
    except Exception as e:
        print("Invalid question " + questionString)
        sys.exit()
place = None
if 'place' in content:
    place = content['place']
startString = None
start = None
if 'start' in content:
    startString = content['start']
    try:
        start = datetime.datetime.strptime(startString,"%Y/%m/%d")
    except Exception as e:
        print("Invalid start date " + startString)
        sys.exit()
startDate = "{:04}".format(start.year) + "{:02}".format(start.month) + "{:02}".format(start.day)
end = None
if 'end' in content:
    endString = content['end']
    try:
        end = datetime.datetime.strptime(endString,"%Y/%m/%d")
    except Exception as e:
        print("Invalid end data " + endString)
        sys.exit()
studyGroupDetails = getStudyGroup(group,start = startString)
workingPartyNumber = ''
for currentWorkingParty in studyGroupDetails.workingParties:
    for currentQuestion in currentWorkingParty.questions:
        if currentQuestion.number == question:
            workingPartyNumber = currentWorkingParty.number
            break
if workingPartyNumber is None:
    print("Question " + str(question) + " not found in study group " + str(group))
    sys.exit()
approval = []
if 'approval' in content:
    if not content['approval'] is None:
        approval = content['approval']
determination = []
if 'determination' in content:
    if not content['determination'] is None:
        determination = content['determination']
consent = []
if 'consent' in content:
    if not content['consent'] is None:
        consent = content['consent']
nonNormative = []
if 'agreement' in content:
    if not content['agreement'] is None:
        nonNormative = content['agreement']
workItems = []
workItemDetails = []
if 'workItems' in content:
    if not content['workItems'] is None:
        workItems = content['workItems']
else:
    if 'workProgramme' in content:
        workProgramme = content['workProgramme']
        workItemDetails = getWorkProgramme(workProgramme)
        if not workItemDetails is None:
            questionName = "Q" + str(question) + "/" + str(group)
            for workItemDetail in workItemDetails:
                if workItemDetail.question == questionName:
                    workItems.append(workItemDetail.workItem)
newWorkItems = []
if 'newWorkItems' in content:
    if not content['newWorkItems'] is None:
        newWorkItems = content['newWorkItems']
deletedWorkItems = []
if 'deletedWorkItems' in content:
    if not content['deletedWorkItems'] is None:
        deletedWorkItems = content['DeletedWorkItems']
candidateForNextMeeting = []
if 'nextMeeting' in content:
    if not content['nextMeeting'] is None:
        candidateForNextMeeting = content['nextMeeting']
outgoingLiaisonStatements = []
if 'outgoingLiaisons' in content:
    if not content['outgoingLiaisons'] is None:
        for number in content['outgoingLiaisons']:
            outgoingLiaisonStatements.append(str(number))
rapporteurMeetings = []
if 'rapporteurMeetings' in content:
    if not content['rapporteurMeetings'] is None:
        for number in content['rapporteurMeetings']:
            rapporteurMeetings.append(str(number))
questionDetails = getQuestion(group = group,question = question,start = startDate)
cTableRows = getDocuments(documentType = "C",group = group,workingParty = workingPartyNumber,questions = question,start = startDate)
plenTableRows = getDocuments(documentType = "PLEN",group = group,workingParty = workingPartyNumber,questions = question,start = startDate)
allPlenTableRows = getDocuments(documentType = "PLEN",group = group,workingParty = workingPartyNumber,questions = "QALL",start = startDate)
genTableRows = getDocuments(documentType = "GEN",group = group,workingParty = workingPartyNumber,questions = question,start = startDate)
wPTableRows = getDocuments(documentType = "WP",group = group,workingParty = workingPartyNumber,questions = question,start = startDate)
agendaTitle = "Draft agenda of Question " + str(question) + "/" + str(group)
reportTitle = "Report of Q" + str(question) + "/" + str(group)
interimReportTitle = "Report of ITU-T Q" + str(question) + "/" + str(group)
interimReports = []
agendaNumber = ''
agenda = ""
reportNumber = ''
report = ""
timePlanNumber = ''
timePlan = ""
if not 'approval' in content:
    for tableRow in wPTableRows:
        if tableRow.documentType == 'Approval':
            approval.append(tableRow.number.value)
if not 'determination' in content:
    for tableRow in wPTableRows:
        if tableRow.documentType == 'Determination':
            determination.append(tableRow.number.value)
if not 'consent' in content:
    for tableRow in wPTableRows:
        if tableRow.documentType == 'Consent':
            consent.append(tableRow.number.value)
if not 'agreement' in content:
    for tableRow in wPTableRows:
        if tableRow.documentType == 'Agreement':
            nonNormative.append(tableRow.number.value)
for allPlenTableRow in allPlenTableRows:
    if allPlenTableRow.title.startswith("Time plan"):
        timePlanNumber = allPlenTableRow.number.value
        timePlan = "link:" + URL + allPlenTableRow.number.link + "[TD" + str(allPlenTableRow.number.value) + allPlenTableRow.lastRev + "]"
for wPTableRow in wPTableRows:
    if strippedStartsWith(agendaTitle,wPTableRow.title):
        agendaNumber = wPTableRow.number.value.replace(' ','')
        agenda = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
        agendaLink = "TD" + str(agendaNumber) + "/" + str(group)
        break
for wPTableRow in wPTableRows:
    if strippedStartsWith(reportTitle,wPTableRow.title):
        reportNumber = wPTableRow.number.value.replace(' ','')
        report = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
    elif strippedStartsWith(interimReportTitle,wPTableRow.title):
        interimReport = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + "/" + str(workingPartyNumber) + wPTableRow.lastRev + "]"
        interimReports.append(interimReport)
if documentType == "agenda":
    filename = str(workingPartyNumber) + "-TD" + str(agendaNumber) + "-Q" + str(question) + " Agenda.adoc"
    fid = open(filename,"w")
    fid.write("= Document\n")
    fid.write(":docNumber: " + str(agendaNumber) + "\n")
    fid.write(":docType: Temporary document\n")
    fid.write(":language: en\n")
    fid.write(":mn-output-extensions: doc,pdf\n")
    fid.write("== Abstract\n")
    fid.write("This TD contains the meeting agenda for Question " + str(question) + "/" + str(group) + " meeting.\n\n")
    fid.write("== Opening the meeting\n\n")
    fid.write("== Approval of the agenda\n")
    fid.write("(this document)\n\n")
    fid.write("== Question " + str(question) + "/" + str(group) + " meeting plan\n")
    fid.write("The SG" + str(group) + " timetable, including the sessions allocated for this Question, is to be found in the latest revision of " + timePlan + "\n\n")
    day = start
    delta = datetime.timedelta(hours = 24)
    while day <= end:
        first = False
        penultimate = False
        last = False
        date = day.strftime("%a").upper() + " " + day.strftime("%d") + "/" + day.strftime("%m") + "/" + day.strftime("%y")
        if (day == start):
            first = True
        if (day + delta) == end:
            penultimate = True
        if day == end:
            last = True
        if not date.startswith("SAT") and not date.startswith("SUN"):
            fid.write("*" + date + "*\n\n")
            if first:
                fid.write("\t- S1, S2: Opening plenary of SG" + str(group)+ "\n\n")
                fid.write("\t- S3:\n\n")
                fid.write("\t- S4:\n\n")
            elif penultimate:
                fid.write("\t- S1, S2, S3, S4: Closing Plenary of WP" + str(workingPartyNumber) + "/" + str(group) + "\n\n")
            elif last:
                fid.write("\t- S1, S2, S3, S4: Closing Plenary of SG" + str(group) + "\n\n")
            else:
                fid.write("\t- S1:\n\n")
                fid.write("\t- S2:\n\n")
                fid.write("\t- S3:\n\n")
                fid.write("\t- S4:\n\n")
        day = day + delta
    fid.write("== Documentation for the meeting\n")
    year = int(startDate[2:4])
    period = str(int(year / 4) * 4 + 1)
    documentation = URL + "/md/T" + period + "-SG" + str(group) + "-" + startDate[2:] + "/sum/en"
    fid.write("The SG" + str(group) + " documents can be found at: ")
    fid.write("link:" + documentation + "[" + documentation + "]\n\n")
    fid.write("The following documents will be considered:\n\n")
    fid.write("=== Contributions:\n\n")
    first = True
    for tableRow in reversed(cTableRows):
        if not first:
            fid.write(", ")
        first = False
        fid.write("link:" + URL + tableRow.number.link + "[C" + str(tableRow.number.value) + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("=== Report of interim activities\n\n")
    first = True
    for interimReport in reversed(interimReports):
        if not first:
            fid.write(", ")
        first = False
        fid.write(interimReport)
        fid.write("\n\n")
    fid.write("=== Incoming Liaison Statements\n\n")
    first = True
    for tableRow in reversed(genTableRows):
        if tableRow.title.startswith("LS/i"):
            if not first:
                fid.write(", ")
            first = False
            fid.write("link:" + URL + tableRow.number.link + "[TD" + str(tableRow.number.value) + "/G" + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("=== Other\n\n")
    fid.write("== Recommendations proposed for APPROVAL (TAP)\n\n")
    fid.write("== Recommendations proposed foe DETERMINATION (TAP)\n\n")
    fid.write("== Recommendations proposed for CONSENT (AAP)\n\n")
    fid.write("== Supplements, Technical Reports; Technical Papers, Implementors' Guides or other documents for AGREEMENT\n\n")
    fid.write("== Proposed new work items\n\n")
    fid.write("== Intellectual property statements\n\n")
    fid.write("== Outgoing Liaison Statements\n\n")
    fid.write("== Review of Question Work Programme\n")
    fid.write("== Future work\n\n")
    fid.write("== Review of Question meeting report " + reportTitle + "\n\n")
    fid.write("== Future meetings\n\n")
    fid.write("== AOB\n\n")
    fid.write("== Closure\n\n")
if documentType == "report":
    filename = str(workingPartyNumber) + "-TD" + str(reportNumber) + "-Q" + str(question) + " Report.adoc"
    fid = open(filename,"w")
    fid.write("= Document\n")
    fid.write(":docNumber: " + str(reportNumber) + "\n")
    fid.write(":docType: Temporary Document\n")
    fid.write(":language: en\n")
    fid.write(":mn-output-extensions: doc,pdf\n")
    fid.write("== Abstract\n\n")
    fid.write("This TD contains the report for Question " + str(question) + "/" + str(group) + " meeting.\n\n")
    fid.write("== Introduction:\n\n")
    for wPTableRow in wPTableRows:
        if wPTableRow.title == "Agenda of Q" + str(question) + "/" + str(group):
            agenda = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
            break
    fid.write("Question " + str(question) + "/" + str(group) + " '" + questionDetails.title + "' " + "was addressed in _number_ sessions during the SG" + str(group) + " meeting held in " + str(place) + ", " + startString + " under the chairmanship of ")
    rapporteurs = getRapporteurs(questionDetails)
    associateRapporteurs = getAssociateRapporteurs(questionDetails)
    first = True
    for rapporteur in rapporteurs:
        if first:
            fid.write(" and ")
        fid.write(rapporteur)
        first = False
    fid.write(". The group adopted the agenda in " + agenda + ".\n\n")
    fid.write("_The list of participants in reproduced in <<Annex_B>>_\n\n")
    fid.write("_Note: <<Annex_B>> list of participants is only requested for interim RGM, not for Q sessions during WP of SG meeting._\n\n")
    fid.write("The objectives for this meeting were:\n\n")
    fid.write("_–	Review input contributions and TDs;_\n\n")
    fid.write("_–	Review input liaison statements and draft reply outgoing liaison statements as appropriate;_\n\n")
    fid.write("_–	Finalize draft ITU-T Recommendations for consent, determination or approval by SG" + str(group) + ";_\n\n")  
    fid.write("_–	Finalize non-normative documents (e.g. draft Supplements, Technical Reports etc) for agreement by SG" + str(group) + ";_\n\n")
    fid.write("_–	Propose new work items to be started by SG" + str(group) + ";_\n\n")
    fid.write("_–   Issue outgoing liaison statements for coordination with other SDOs, Questions, or Study Groups;_\n\n")
    fid.write("_–	etc.…_\n\n")
    fid.write("== Executive summary | Highlights\n\n")
    fid.write("_Include here a detailed executive summary of the results of this Question meeting. This summary will be copied and pasted by the working party chair in the related WP report. So please provide a VERY ACCURATE summary_\n\n")
    fid.write("During this SG" + str(group) + " meeting, Q" + str(question) + "/" + str(group) + " received " + str(len(cTableRows)) + " contributions and achieved the following results:\n\n")
    if len(approval) > 0:
        fid.write("-    " + str(len(approval)) + " Recommendations were finalized znd proposed for TAP approval: " + commaSeparatedList(approval) + "\n\n") 
    if len(determination) > 0:
        fid.write("-    " + str(len(determination)) + " Recommendations were finalized znd proposed for TAP determination: " + commaSeparatedList(determination) + "\n\n") 
    if len(consent) > 0:
        fid.write("-    " + str(len(consent)) + " Recommendation were finalized and proposed for AAP consent: " + commaSeparatedList(consent) + "\n\n") 
    if len(nonNormative) > 0:
        fid.write("-    " + str(len(nonNormative)) + " non-normative texts (e.g. Supplements, Technical reports, etc.) were finalized znd proposed for agreement: " + commaSeparatedList(nonNormative) + "\n\n") 
    if len(workItems) == 1:
        fid.write("-    " + str(len(workItems)) + " work item was progressed: " + commaSeparatedList(workItems) + "\n\n") 
    elif len(workItems) > 1:
        fid.write("-    " + str(len(workItems)) + " work items were progressed: " + commaSeparatedList(workItems) + "\n\n") 
    if len(newWorkItems) == 1:
        fid.write("-    " + str(len(newWorkItems)) + " new work item was agreed to be started: " + commaSeparatedList(newWorkItems) + "\n\n") 
    elif len(newWorkItems) > 1:
        fid.write("-    " + str(len(newWorkItems)) + " new work items were agreed to be started: " + commaSeparatedList(newWorkItems) + "\n\n") 
    if len(candidateForNextMeeting) == 1:
        fid.write("-    " + str(len(candidateForNextMeeting)) + " was agreed as candidate for decision in next SG" + str(group) + " meeting: " + commaSeparatedList(candidateForNextMeeting) + "\n\n") 
    if len(candidateForNextMeeting) > 1:
        fid.write("-    " + str(len(candidateForNextMeeting)) + " were agreed as candidates for decision in next SG" + str(group) + " meeting: " + commaSeparatedList(candidateForNextMeeting) + "\n\n") 
    if len(outgoingLiaisonStatements) > 0:
        destinations = []
        for number in outgoingLiaisonStatements:
            destination = getLiaisonDestination(wPTableRows,number)
            if not destination is None:
                destinations.append(destination)
    if len(outgoingLiaisonStatements) == 1:
        fid.write("-    " + str(len(outgoingLiaisonStatements)) + " outgoing liaison statement was agreed to be sent: " + commaSeparatedList(destinations) + "\n\n") 
    elif len(outgoingLiaisonStatements) > 1:
        fid.write("-    " + str(len(outgoingLiaisonStatements)) + " outgoing liaison statements were agreed to be sent: " + commaSeparatedList(destinations) + "\n\n") 
    if len(rapporteurMeetings) > 0:
        titles = []
        for number in rapporteurMeetings:
            title = getDocumentTitle(wPTableRows,number)
            if not title is None:
                titles.append(title)
    if len(rapporteurMeetings) == 1:
        fid.write("-    " + str(len(rapporteurMeetings)) + " interim meeting was planned before the next SG" + str(group) + " meeting: " + commaSeparatedList(titles) + "\n\n")
    elif len(rapporteurMeetings) > 1:
        fid.write("-    " + str(len(rapporteurMeetings)) + " interim meetings were planned before the next SG" + str(group) + " meetings:" + commaSeparatedList(titles) + "\n\n")
    fid.write("-    _Appointment of associate rapporteur / liaison officers, if any_\n\n")
    fid.write("-    _Any other issue of importance (e.g. OID assignment, roadmap updates, workshop, joint session, A.5 qualification_\n\n")
    fid.write("== Documentation and email lists\n\n")
    fid.write("=== Documentation\n\n")
    fid.write("The list of documents for the meeting with detailed information (document number, title, source) is found in <<Annex_A>>\n\n")
    fid.write("The following documents were examined:\n\n")
    fid.write("-    Contributions: ")
    first = True
    for tableRow in reversed(cTableRows):
        if not first:
            fid.write(", ")
        first = False
        fid.write("link:" + URL + tableRow.number.link + "[C" + tableRow.number.value + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("-    TD/P: ")
    first = True
    for tableRow in reversed(plenTableRows):
        if not first:
            fid.write(", ")
        first = False
        fid.write("link:" + URL + tableRow.number.link + "[" + tableRow.number.value + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("-    TD/G: ")
    first = True
    for tableRow in reversed(genTableRows):
        if not first:
            fid.write(", ")
        first = False
        fid.write("link:" + URL + tableRow.number.link + "[" + tableRow.number.value + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("-    TD/" + str(workingPartyNumber) + ": ")
    first = True
    for tableRow in reversed(wPTableRows):
        if not first:
            fid.write(", ")
        first = False
        fid.write("link:" + URL + tableRow.number.link + "[" + tableRow.number.value + tableRow.lastRev + "]")
    fid.write("\n\n")
    fid.write("The complete documentation for this SG" + str(group) + " meeting is to be found at:\n\n")
    year = int(startDate[2:4])
    period = str(int(year / 4) * 4 + 1)
    documentation = URL + "/md/T" + period + "-SG" + str(group) + "-" + startDate + "/sum/en"
    fid.write("The SG" + str(group) + " documents can be found at: ")
    fid.write("link:" + documentation + "[documentation]\n\n")
    fid.write("=== Emailing list subscription\n\n")
    reflector = "t" + period + "sg" + str(group) + "Q" + str(question) + "@lists.itu.int"
    subscriptionWebpage =  "/net4/iwm?p0=0&p11=ITU&p12=ITU-SEP-ITU-T-SEP-SP%2017-SEP-Study%20Group%2017&p21=ITU&p22=ITU"
    fid.write("E-mail correspondences pertaining to the activities of this Question are routinely conducted using the e-mail reflector " + URL + reflector + ".\n\n")
    fid.write("Those wishing to subscribe or unsubscribe to this, or other SG" + str(group) + " email reflectors should visit the mailing list web page at " + URL + subscriptionWebpage + "[subscription webpage].\n\n")
    year = int(startDate[0:4])
    firstYear = int(year / 4) * 4 + 1
    lastYear = firstYear + 3
    webpage = "/en/ITU-T/studygroups/" + str(firstYear) + "-" + str(lastYear) + "/" + str(group) + "/Pages/ifa-structure.aspx"
    fid.write("Information on SG" + str(group) + "informal FTP areas (IFA) and all SG" + str(group) + " mailing lists is on the related " + URL + webpage + "[webpage].\n\n")
    fid.write("== Report of interim activities\n\n")
    meetingReports = getMeetingReports(tableRows = wPTableRows,question = question,group = group)
    if len(meetingReports) > 0:
        if len(meetingReports) == 1:
            fid.write("Since the last SG" + str(group) + " meeting, Question " + str(question) + "/" + str(group) + " held the following Rapporteur meeting")
        else:
            fid.write("Since the last SG" + str(group) + " meeting, Question " + str(question) + "/" + str(group) + " held the following Rapporteur meetings")
        for meetingReport in meetingReports:
            location = ""
            date = ""
            index1 = meetingReport.title.rfind('(')
            if index1 >= 0:
                index2 = meetingReport.title.find(')',index1)
                index3 = meetingReport.title.find(',',index1)
                if index2 >= 0 and index3 >= 0:
                    location = meetingReport.title[index1 + 1:index3]
                    date = meetingReport.title[index3 + 1:index2]
            fid.write("-    " + date + " (" + location + ") The report of this Rapporteur meeting, which is found in (TD" + str(meetingReport.number.value) + "/" + str(workingPartyNumber) + ") was approved at the WP" + str(workingPartyNumber) + "/" + str(group) + " held on _DD MM YYYY_\n\n")
    fid.write("== Discussions\n\n")
    fid.write("=== Outgoing work items\n\n")
    selectedTableRows = []
    for i in range(0,len(workItems)):
        fid.write("==== Work Item " + str(i + 1) + ": (" + workItems[i] + "):\n\n")
        for tableRow in cTableRows:
            index = workItems[i].find(' ')
            if index > 0:
                workItem = workItems[i][:index]
            else:
                workItem = workItems[i]
            if workItem.lower() in tableRow.title.lower():
                selectedTableRows.append(tableRow)
                fid.write("link:" + URL + tableRow.number.link + "[*C" + tableRow.number.value + tableRow.lastRev + "]*\n\n")
    fid.write("=== New proposed work items\n\n")
    num = 0
    for tableRow in cTableRows:
        if isNewWorkItem(tableRow.title):
            selectedTableRows.append(tableRow)
            num = num + 1
            name = ""
            index1 = tableRow.title.find("X.")
            if index1 >= 0:
                index2 = tableRow.title.find(":",index1)
                if index2 >= 0:
                    name = tableRow.title[index1:index2]
            else:
                index1 = tableRow.title.find("TR.")
                if index1 >= 0:
                    index2 = tableRow.title.find(" ",index1)
                    if index2 >= 0:
                        name = tableRow.title[index1:index2]
            fid.write("==== New Work Item " + str(num) + ": (" + name + "):\n\n")
            fid.write("link:" + URL + tableRow.number.link + "[*C" + tableRow.number.value + tableRow.lastRev + "]*\n\n")
    fid.write("=== Other Contributions (not directly related to a work item)\n\n")
    for tableRow in cTableRows:
        if tableRow not in selectedTableRows:
            fid.write("link:" + URL + tableRow.number.link + "[*C" + tableRow.number.value + "]*\n\n")
    selectedTableRows = []
    fid.write("=== Incoming liaison statements\n\n")
    for tableRow in genTableRows:
        if tableRow.title.startswith("LS/i"):
            selectedTableRows.append(tableRow)
            fid.write("link:" + URL + tableRow.number.link + "[*TD" + tableRow.number.value + tableRow.lastRev + "/G]*: " + tableRow.title + " [from link:" + URL + tableRow.source.link + "[" + tableRow.source.name + "]]\n\n")
    fid.write("=== Other TDs\n\n")
    for tableRow in plenTableRows:
        if tableRow not in selectedTableRows:
            fid.write("link:" + URL + tableRow.number.link + "[*TD" + tableRow.number.value + tableRow.lastRev + "/P]*: " + tableRow.title + "\n\n")
    for tableRow in genTableRows:
        if tableRow not in selectedTableRows:
            fid.write("link:" + URL + tableRow.number.link + "[*TD" + tableRow.number.value + tableRow.lastRev + "/G]*: " + tableRow.title + "\n\n")
    for tableRow in wPTableRows:
        if tableRow not in selectedTableRows:
            fid.write("link:" + URL + tableRow.number.link + "[*TD" + tableRow.number.value + tableRow.lastRev + "/" + str(workingPartyNumber) + "]*: " + tableRow.title + "\n\n")
    fid.write('== Draft new/revised Recommendations proposed for "Approval" (TAP), "determination" (TAP) or "consent" (AAP)\n\n')
    fid.write("Note: The rapporteur checked that the editor applied the link:" + URL + "/en/ITU-T/studygroups/Documents/Doc-ITUT-Recs-Skelet.docx[skeleton template to draft Recommendations]  and that the following Recommendations are compliant with the link:" + URL + "/oth/T0AF000004/en[Author(s guide]\n\n")
    fid.write("=== Recommendations for TAP approval (WTSA Resolution 1, §9)\n\n")
    if len(approval) >= 0:
        fid.write("The Following draft Recommendations are proposed for TAP approval:\n\n")
        fid.write('[cols="1,4,4,4,6,4,4,4"]\n')
        fid.write(".TAP approval\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work item|Status|Title|Final Text|A.5 justification|Equivalent e.g. ISO/IEC\n\n")
        num = 0
        for element in approval:
            (questionName,tD,a5) = findQuestionNameTDandA5(wPTableRows,element)
            num = num + 1
            if tD is None:
                finalText = ""
            else:
                finalText = "link:" + URL + tD.number.link + "[TD " + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            if a5 is None:
                a5Text = ""
            else:
                a5text = "link:" + URL + tD.number.link + "[TD " + a5.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.acronym) > 0:
                workItem = tD.recommendation + "(" + tD.acronym + ")"
            else:
                workItem = tD.recommendation
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|Q" + str(question) + "/" + str(group) + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
        fid.write("\n|===\n\n")
    fid.write("=== Recommendations for TAP determination (WTSA Resolution 1, §9)\n\n")
    if len(determination) >= 0:
        fid.write("The Following draft Recommendations are proposed for TAP determination:\n\n")
        fid.write('[cols="1,4,4,4,6,4,4,4"]\n')
        fid.write(".TAP determination\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work item|Status|Title|Final Text|A.5 justification|Equivalent e.g. ISO/IEC\n\n")
        num = 0
        for element in determination:
            (questionName,tD,a5) = findQuestionNameTDandA5(wPTableRows,element)
            num = num + 1
            if tD is None:
                finalText = ""
            else:
                finalText = "link:" + URL + tD.number.link + "[TD " + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            if a5 is None:
                a5Text = ""
            else:
                a5text = "link:" + URL + tD.number.link + "[TD " + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.acronym) > 0:
                workItem = tD.recommendation + "(" + tD.acronym + ")"
            else:
                workItem = tD.recommendation
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|Q" + str(question) + "/" + str(group) + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
        fid.write("\n|===\n\n")
    fid.write("=== Recommendations for AAP consent (Rec. ITU-T A.8)\n\n")
    if len(consent) >= 0:
        fid.write("The Following draft Recommendations are proposed for consent\n\n")
        fid.write('[cols="1,4,4,4,6,4,4,4"]\n')
        fid.write(".AAP consent\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work item|Status|Title|Final Text|A.5 justification|Equivalent e.g. ISO/IEC\n\n")
        num = 0
        for element in consent:
            (questionName,tD,a5) = findQuestionNameTDandA5(wPTableRows,element)
            num = num + 1
            if tD is None:
                finalText = ""
            else:
                finalText = "link:" + URL + tD.number.link + "[TD " + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            if a5 is None:
                a5Text = ""
            else:
                a5text = "link:" + URL + a5.number.link + "[TD " + a5.number.value + a5.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.recommendation) > 0:
                if len(tD.acronym) > 0:
                    workItem = tD.recommendation + "(" + tD.acronym + ")"
                else:
                    workItem = tD.recommendation
            else:
                workItem = tD.acronym
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|Q" + str(question) + "/" + str(group) + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
        fid.write("\n|===\n\n")
    fid.write("=== Non-normative text (e.g., Supplements, Technical Reports, Technical Papers, Implementors' Guides ot other documents) for agreement\n\n")
    if len(nonNormative) >= 0:
        fid.write("The following documents are proposed for agreement:\n\n")
        fid.write('[cols="1,4,4,4,10,4"]\n')
        fid.write(".Non normative texts\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work item|Status|Title|Final Text\n\n")
        num = 0
        for element in nonNormative:
            (questionName,tD,a5) = findQuestionNameTDandA5(wPTableRows,element)
            num = num + 1
            if tD is None:
                finalText = ""
            else:
                finalText = "link:" + URL + tD.number.link + "[TD " + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            textTitle = ""
            workItem = ""
            for i in range(0,len(workItems)):
                index = workItems[i].find(' ')
                if index > 0:
                    currentWorkItem = workItems[i][:index].replace('_','.')
                else:
                    currentWorkItem = workItems[i].replace('_','.')
                if currentWorkItem.lower() in tD.title.replace('_','.').lower():
                    workItem = currentWorkItem
                    break
            textTitle = splitTitle(tD.title)[3]
            fid.write("|" + str(num) + "|Q" + str(question) + "/" + str(group) + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "\n")
        fid.write("\n|===\n\n")
    fid.write("== Intellectual property statements\n\n")
    fid.write("The Rapporteur reminded the meeting participants of the ITU-T IPR Policy (see link:" + URL + "/en/ITU-T/ipr/Pages/default.aspx[IPR]) and asked those present whether anyone has knowledge of intellectual property rights issues, including patents, copyright for software or text, marks, the use of which may be required to implement or publish the Recommendation being considered.\n\n") 
    fid.write("The Rapporteur reminded the participants that any ITU-T member organization putting forward a standardization proposal should draw the attention of the TSB Director to any known or pending patent and any other applicable IPR issues.\n\n")
    fid.write("_No IPR statements were received at this meeting_\n\n")
    fid.write("_Company xxx submitted / promised to submit to TSB a patent declaration for draft Recommendation X.yyy_\n\n")
    fid.write("== Outgoing liaison statements\n\n")
    if len(outgoingLiaisonStatements) >= 0:
        fid.write("The following outgoing LSs were prepared by the Question\n\n")
        fid.write('[cols="1,4,4,6,6,8,4"]\n')
        fid.write(".Outgoing liaison statements\n")
        fid.write("|===\n")
        fid.write("|#|Question|WP|For action to|For information to|Title|TD\n\n")
        num = 0
        for element in outgoingLiaisonStatements:
            (questionName,tD) = findTDByNumber(wPTableRows,element)
            num = num + 1
            title = ""
            tDName = ""
            destination = ""
            if not tD is None:
                title = tD.title
                index1 = title.find('[to')
                if index1 >= 0:
                    index2 = title.find(']',index1)
                    if index2 > index1:
                        destination = title[index1 + 1: index2]
                tDName = "link:" + URL + tD.number.link + "[TD" + str(element) + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            fid.write("|" + str(num) + "|Q" + str(question) + "/" + str(group) + "|WP" + str(workingPartyNumber) + "|_" + destination + "_|_" + destination + "_|" + insertEscape(title) + "|" + tDName + "\n")
        fid.write("\n|===\n\n")
    fid.write("== Work programme\n\n")
    fid.write("SG" + str(group) + " reports use the place of a superscript next to a work item name to indicate its approval process\n\n")
    fid.write("-    ^*^ for TAP;\n\n")
    fid.write("-    ^**^ for agreement; and\n\n")
    fid.write("-    no superscript is for AAP\n\n")
    fid.write("=== New work items\n\n")
    if len(newWorkItems) >= 0:
        fid.write("The meeting agreed to start work on the following new work items\n\n")
        fid.write('[cols="1,4,4,4,4,6,4,4,4"]\n')
        fid.write(".New work items\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work Item|Status|Title|Editor|Base Text|Equivalent e.g. ISO/IEC|A.1/A.13 Justification Annex\n\n")
        num = 0
        for tableRow in cTableRows:
            if isNewWorkItem(tableRow.title):
                num = num + 1
                workItem = ""
                textTitle = ""
                baseText = ""
                index1 = tableRow.title.find("X.")
                if index1 >= 0:
                    index2 = tableRow.title.find(":",index1)
                    if index2 >= 0:
                        workItem = tableRow.title[index1:index2]
                        textTitle = tableRow.title[index2 + 1:]
                        if textTitle.startswith('"') and textTitle.endswith('"'):
                            textTitle = textTitle[1:len(textTitle) - 1]
                else:
                    index1 = tableRow.title.find("TR.")
                    if index1 >= 0:
                        index2 = tableRow.title.find(" ",index1)
                        if index2 >= 0:
                            workItem = tableRow.title[index1:index2]
                            textTitle = tableRow.title[index2 + 1:]
                            if textTitle.startswith('"') and textTitle.endswith('"'):
                                textTitle = textTitle[1:len(textTitle) - 1]
                baseText = "link:" + URL + tableRow.number.link + "[C" + tableRow.number.value + tableRow.lastRev + "]"
                fid.write("|" + str(num) + "|" + str(question) + "/" + str(group) + "|" + workItem + "|New|" + insertEscape(textTitle) + "| |" + baseText + "| |\n")
        fid.write("\n|===\n\n")
        fid.write("Please create an ANNEX for each new work item, using the A.1 (found in ANNEX C) for normative texts (e.g. ITU-T Recommendations) or A.13 (found in ANNEX D) for non-normative texts (e.g. Supplements, Technical Reports, etc.) justification templates.\n\n")
        fid.write("Note1: A.1 justification template can be downloaded link;" + URL + "/en/ITU-T/studygroups/Documents/Form-A.01-Annex-A-New-Rec-Justif-template.docx[here].\n\n")
        fid.write("Note2: A.13 justification template can be downloaded link:" + URL + "/en/ITU-T/studygroups/Documents/Form-A.13-Annex-A-New_non-normative_Justif-template.docx[here].\n\n")
    fid.write("=== Deleted work items\n\n")
    if len(deletedWorkItems) >= 0:
        fid.write("The meeting agreed to discontinue the following work items:\n\n")
        fid.write('[cols="1,4,6,10"]\n')
        fid.write(".Deleted work items\n")
        fid.write("|===\n")
        fid.write("|#|Question|Acronym kind of publication)|Title\n\n")
        num = 0
        for element in deletedWorkItems:
            num = num + 1
            title = ""
            tDName = ""
            (questionName,tD) = findTDByNumber(wPTableRows,element)
            if not tD is None:
                title = tableRow.title
            fid.write("|" + str(num) + "|" + str(question) + "/" + str(group) + "|" + tD.acronym + "|" + insertEscape(title) + "\n")
        fid.write("|===\n\n")
    fid.write("=== Updated Question work programme\n\n")
    fid.write("The current list of ongoing work items, including eventual new work items agreed at this meeting. (see item [[10.1]] above) as follows:\n\n")
    if len(workItems) >= 0:
        fid.write('[cols="1,4,4,4,10,8,4,4,4,4"]\n')
        fid.write(".Ongoing work items\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work Item|Status|Title|Editor|Base Text|Equivalent e.g.,ISO/IEC|Target Date|Summary updated (Yes/No)\n\n")
        num = 0
        for element in workItems:
            num = num + 1
            title = ""
            tDName = ""
            status = ""
            (questionName,tD) = findTDByName(wPTableRows,element)
            if not tD is None:
                title = tD.textTitle
                tDName = "link:" + URL + tD.number.link + "[TD" + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            else:
                for workItemDetail in workItemDetails:
                    if workItemDetail.workItem == element:
                        title = workItemDetail.title
                        status = workItemDetail.status
                        break
            fid.write("|" + str(num) + "|" + str(question) + "/" + str(group) + "|" + str(element) + "|" + status +  "|" + insertEscape(title) + "| |" + tDName + "| | |\n")
        fid.write("|===\n\n")
    fid.write("Note: The latest SG" + str(group) + " Work programme can be found at link:" + URL + "/ITU-T/workprog/wp_search.aspx?sg=" + str(group) + "[Work programme]\n\n")
    fid.write("== Candidate work items for decision at the next SG" + str(group) + " meeting\n\n")
    if len(candidateForNextMeeting) >= 0:
        fid.write("The following work items are planned for decision at next SG" + str(group) + " meeting\n\n")
        fid.write('[cols="1,4,4,4,10,8,4,4,4"]\n')
        fid.write(".Candidate work items for next SG" + str(group) + " meeting\n")
        fid.write("|===\n")
        fid.write("|#|Question|Acronym (kind of publication)|Status|Title|Editor|Base Text|A.5 justification|Equivalent e.g.,ISO/IEC\n\n")
        num = 0
        for element in candidateForNextMeeting:
            num = num + 1
            title = ""
            tDName = ""
            (questionName,tD) = findTDByName(wPTableRows,element)
            if not tD is None:
                title = tD.textTitle
                tDName = "link:" + URL + tD.number.link + "[TD" + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            fid.write("|" + str(num) + "|" + str(question) + "/" + str(group) + "|" + str(element) + "| |" + insertEscape(title) + "| | " + tDName + "| |\n")
        fid.write("\n|===\n\n")
    fid.write("Note: The latest SG" + str(group) + " Work programme can be found at link:" + URL + "/ITU-T/workprog/wp_search.aspx?sg=" + str(group) + "[Work programme]\n\n")
    fid.write("== Planned interim Rapporteurs meetings\n\n")
    fid.write("The following interim Rapporteurs group meetings for Question " + str(question) + "/" + str(group) + " are proposed for approval\n\n")
    fid.write('[cols="1,4,4,10,8"]\n')
    fid.write(".Interim Rapporteur meeting\n")
    fid.write("|===\n")
    fid.write("|Question|Date (time)|Place/Host|Terms of reference|Contact\n\n")
    if len(rapporteurMeetings) >= 0:
        num = 0
        for element in rapporteurMeetings:
            num = num + 1
            fid.write("|" + str(question) + "/" + str(group) + "| | | |\n")
    fid.write("\n|===\n\n")
    fid.write("Details will be posted on the ITU-T SG" + str(group) + " Rapporteur Group meetings website: link:" + URL + "/net/ITU-T/lists/rgm.aspx?Group=" + str(group) + "&type=interim[Rapporteur Group meetings website]\n\n")
    fid.write("== Scheduled WP or SG" + str(group) + " meetings\n\n")
    fid.write("Q" + str(question) + "/" + str(group) + " is planning to meet again during SG" + str(group) + " or WP" + str(workingPartyNumber) + " of SG" + str(group) + ", to be held from _start_ to _end_. This question will require _number_ of sessions\n\n")
    fid.write("Details will be posted on the ITU-T SG" + str(group) + " website link:" + URL + "/go/tsg" + str(group) + "[SG" + str(group) + " website]\n\n")
    fid.write("[appendix]\n")
    fid.write("[align=center]\n")
    fid.write("== [[Annex_A]]\n\n")
    fid.write("[Documentation addressed by the Question]\n\n")
    fid.write("_Add a table here listing ALL Contributions and TDs (with details like document number, title, and source) addressed by the Question in this meeting_\n\n")
    year = int(startDate[2:4])
    period = str(int(year / 4) * 4 + 1)
    documentation = "link:" + URL + "/md/T" + period + "-SG" + str(group) + "-" + startDate + "/sum/en"
    fid.write("Note: List if all SG" + str(group) + " documents sorted by Questions could be downloaded at " + documentation + "[documents]\n") 
    fid.write('[cols="4,4,12,4"]\n')
    fid.write(".Contributions\n")
    fid.write("|===\n")
    fid.write("|Web|Source|Title|AI/Question\n\n")
    for tableRow in cTableRows:
        name = "link:" + URL + tableRow.number.link + "[C" + tableRow.number.value + tableRow.lastRev + "]"
        source = "link:" + URL + tableRow.source.link + "[" + tableRow.source.value + "]"
        fid.write("|" + name + "|" + source + "|" + insertEscape(tableRow.title) + "|Q" + str(question) + "/" + str(group) + "\n")
    fid.write("\n|===\n\n")
    fid.write('[cols="4,4,12,4"]\n')
    fid.write(".Temporary Documents (GEN)\n")
    fid.write("|===\n")
    fid.write("|Web|Source|Title|AI/Question\n\n")
    for tableRow in genTableRows:
        name = "link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "/G]"
        source = "link:" + URL + tableRow.source.link + "[" + tableRow.source.value + "]"
        fid.write("|" + name + "|" + source + "|" + insertEscape(tableRow.title) + "|Q" + str(question) + "/" + str(group) + "\n")
    fid.write("\n|===\n\n")
    fid.write('[cols="4,4,12,4"]\n')
    fid.write(".Temporary Documents (PLEN)\n")
    fid.write("|===\n")
    fid.write("|Web|Source|Title|AI/Question\n\n")
    for tableRow in plenTableRows:
        name = "link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "/P]"
        source = "link:" + URL + tableRow.source.link + "[" + tableRow.source.value + "]"
        fid.write("|" + name + "|" + source + "|" + insertEscape(tableRow.title) + "|Q" + str(question) + "/" + str(group) + "\n")
    fid.write("\n|===\n\n")
    fid.write('[cols="4,4,12,4"]\n')
    fid.write(".Temporary Documents (WP" + str(workingPartyNumber) + ")\n")
    fid.write("|===\n")
    fid.write("|Web|Source|Title|AI/Question\n\n")
    for tableRow in wPTableRows:
        name = "link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "/" + str(workingPartyNumber) + "]"
        source = "link:" + URL + tableRow.source.link + "[" + tableRow.source.value + "]"
        fid.write("|" + name + "|" + source + "|" + insertEscape(tableRow.title) + "|Q" + str(question) + "/" + str(group) + "\n")
    fid.write("\n|===\n\n")
    fid.write("[appendix]\n")
    fid.write("[align=center]\n")
    fid.write("== [[Annex_B]]\n\n")
    fid.write("[List of participants]\n\n")
    fid.write("Note: Annex B is only required for RGM, not for Q sessions during SG" + str(group) + " meeting\n\n")
    fid.write('[cols="8,10,6"]\n')
    fid.write(".Participants\n")
    fid.write("|===\n")
    fid.write("|Name|Entity|Country\n")
    fid.write("\n|===\n\n")
fid.close()
sys.exit()
