import json
import os
import sys
import datetime
from getDocuments import *
from getQuestion import *
from getWorkingParty import *
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
workingPartyNumber = ''
if 'workingParty' in content:
    workingPartyString = content['workingParty']
    try:
        workingPartyNumber = int(workingPartyString)
    except Exception as e:
        print("Invalid workingParty number" + workingPartyString)
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
studyGroupDetails = getStudyGroup(group = group,start = startString)
questions = None
for currentWorkingParty in studyGroupDetails.workingParties:
    if currentWorkingParty.number == workingPartyNumber:
        workingParty = currentWorkingParty
        questions = workingParty.questions
        break
if workingParty is None:
    print("Working party " + str(workingPartyNumber) + " not found in study group " + str(group))
    sys.exit()
workingPartyDetails = getWorkingParty(group = group,workingParty = workingPartyNumber,questions = questions,start = startString)
questionNumbers = []
questionsDetails = []
for question in questions:
    questionNumbers.append(question.number)
    questionDetails = getQuestion(group = group,question = question.number,start = startDate)
    questionsDetails.append(questionDetails)
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
if 'workItems' in content:
    if not content['workItems'] is None:
        workItems = content['workItems']
else:
    if 'workProgramme' in content:
        workProgramme = content['workProgramme']
        workItemDetails = getWorkProgramme(workProgramme)
        if not workItemDetails is None:
            for questionNumber in questionNumbers:
                questionName = "Q" + str(questionNumber) + "/" + str(group)
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
        deletedWorkItems = content['deletedWorkItems']
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
interimMeetings = []
if 'interimMeetings' in content:
    if not content['interimMeetings'] is None:
        for number in content['interimMeetings']:
            interimMeetings.append(str(number))
cTableRows = getDocuments(documentType = "C",group = group,workingParty = workingPartyNumber,questions = questionNumbers,start = startDate)
plenTableRows = getDocuments(documentType = "PLEN",group = group,workingParty = workingPartyNumber,questions = questionNumbers,start = startDate)
genTableRows = getDocuments(documentType = "GEN",group = group,workingParty = workingPartyNumber,questions = questionNumbers,start = startDate)
wPTableRows = getDocuments(documentType = "WP",group = group,workingParty = workingPartyNumber,questions = questionNumbers,start = startDate)
agendaTitle = "Agenda of WP" + str(workingPartyNumber) + "/" + str(group)
reportTitle = "Report of WP" + str(workingPartyNumber) + "/" + str(group)
agendaNumber = ''
agenda = ""
report = ""
reportNumber = ''
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
for wPTableRow in wPTableRows:
    if compareStripped(wPTableRow.title,agendaTitle):
        agendaNumber = wPTableRow.number.value.replace(' ','')
        agenda = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
        agendaLink = "TD" + str(agendaNumber) + "/" + str(group)
        break
for wPTableRow in wPTableRows:
    if compareStripped(wPTableRow.title,reportTitle):
        reportNumber = wPTableRow.number.value.replace(' ','')
        report = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
        reportLink = "TD" + str(reportNumber) + "/" + str(group)
        break
if documentType == "agenda":
    pass
if documentType == "report":
    filename = str(workingPartyNumber) + "-TD" + str(reportNumber) + " Report.adoc"
    fid = open(filename,"w")
    fid.write("= Document\n")
    fid.write(":docNumber: " + str(reportNumber) + "\n")
    fid.write(":docType: Temporary Document\n")
    fid.write(":language: en\n")
    fid.write(":mn-output-extensions: doc,pdf\n")
    fid.write("== Abstract\n\n")
    fid.write("This TD contains the report for Working Party " + str(workingPartyNumber) + "/" + str(group) + " meeting.\n\n")
    fid.write("== Introduction:\n\n")
    chairs = getChairs(workingPartyDetails)
    viceChairs = getViceChairs(workingPartyDetails)
    fid.write("Working Party " + str(workingPartyNumber) + "/" + str(group) + "met during the SG" + str(group) + " meeting held in " + str(place) + ", " + startString + ", chaired by ")
    first = True
    for chair in chairs:
        if not first:
            fid.write(" and ")
        fid.write(chair)
        first = False
    if len(viceChairs) > 0:
        fid.write(" and assisted by ")
        first = True
        for viceChair in viceChairs:
            if not first:
                fid.write(", ")
            fid.write(viceChair)
            first = False
    fid.write("\n\n")
    fid.write("The meeting was addressed in _number_ sessions on _days_. The group adopted the agenda in " + agenda + ".\n\n")
    fid.write("== Executive summary | Highlights\n\n")
    fid.write("_Include here an executive summary of the executive summaries of Questions of this WP meeting._\n\n")
    fid.write("During this SG" + str(group) + " meeting, WP" + str(workingPartyNumber) + "/" + str(group) + " achieved the following results:\n\n")
    if len(approval) >= 0:
        fid.write("-    " + str(len(approval)) + " Recommendations were finalized znd proposed for TAP approval: " + commaSeparatedList(approval) + "\n\n")
    if len(determination) >= 0:
        fid.write("-    " + str(len(determination)) + " Recommendations were finalized znd proposed for TAP determination: " + commaSeparatedList(determination) + "\n\n")
    if len(consent) >= 0:
        fid.write("-    " + str(len(consent)) + " Recommendations were finalized znd proposed for AAP consent: " + commaSeparatedList(consent) + "\n\n")
    if len(nonNormative) >= 0:
        fid.write("-    " + str(len(nonNormative)) + " non-normative texts (e.g. Supplements, Technical reports, etc.) were finalized znd propose for agreement: " + commaSeparatedList(nonNormative) + "\n\n")
    if len(newWorkItems) == 1:
        fid.write("-    " + str(len(newWorkItems)) + " new work item was agreed to be started: " + commaSeparatedList(newWorkItems) + "\n\n")
    elif len(newWorkItems) > 1:
        fid.write("-    " + str(len(newWorkItems)) + " new work items were agreed to be started: " + commaSeparatedList(newWorkItems) + "\n\n")
    if len(deletedWorkItems) == 1:
        fid.write("-    " + str(len(deletedWorkItems)) + " work item was agreed to be deleted: " + commaSeparatedList(deletedWorkItems) + "\n\n")
    elif len(deletedWorkItems) > 1:
        fid.write("-    " + str(len(deletedWorkkItem)) + " new work items were agreed to be deleted: " + commaSeparatedList(deletedWorkItem) + "\n\n")
    if len(workItems) == 1:
        fid.write("-    " + str(len(workItems)) + " work item was progressed: " + commaSeparatedList(workItems) + "\n\n")
    elif len(workItems) > 1:
        fid.write("-    " + str(len(workItems)) + " work items were progressed: " + commaSeparatedList(workItems) + "\n\n")
    if len(candidateForNextMeeting) == 1:
        fid.write("-    " + str(len(candidateForNextMeeting)) + " work item is planed for action in next SG" + str(group) + " meeting: " + commaSeparatedList(candidateForNextMeeting) + "\n\n")
    if len(candidateForNextMeeting) > 1:
        fid.write("-    " + str(len(candidateForNextMeeting)) + " work items are planed for action in next SG" + str(group) + " meeting: " + commaSeparatedList(candidateForNextMeeting) + "\n\n")
    if len(outgoingLiaisonStatements) >= 0:
        destinations = []
        for number in outgoingLiaisonStatements:
            destination = getLiaisonDestination(wPTableRows,number)
            if not destination is None:
                destinations.append(destination)
    if len(outgoingLiaisonStatements) == 1:
        fid.write("-    " + str(len(outgoingLiaisonStatements)) + " outgoing liaison statement was agreed to be sent: " + commaSeparatedList(destinations) + "\n\n")
    elif len(outgoingLiaisonStatements) > 1:
        fid.write("-    " + str(len(outgoingLiaisonStatements)) + " outgoing liaison statements were agreed to be sent: " + commaSeparatedList(destinations) + "\n\n")
    if len(rapporteurMeetings) >= 0:
        titles = []
        for number in rapporteurMeetings:
            title = getDocumentTitle(wPTableRows,number)
            if not title is None:
                titles.append(title)
    if len(rapporteurMeetings) == 1:
        fid.write("-    " + str(len(rapporteurMeetings)) + " interim (RGM) meeting was planned before the next SG" + str(group) + " meeting: " + commaSeparatedList(titles) + "\n\n")
    elif len(rapporteurMeetings) > 1:
        fid.write("-    " + str(len(rapporteurMeetings)) + " interim (RGM) meetings were planned before the next SG" + str(group) + " meetings:" + commaSeparatedList(titles) + "\n\n")
    fid.write("-    _Appointment of associate rapporteur / liaison officers, if any_\n\n")
    fid.write("-    _Any other issue of importance (e.g. OID assignment, roadmap updates, workshop, joint session, A.5 qualification_\n\n")
    fid.write("== WP" + str(workingPartyNumber) + "/" + str(group) + " Structure and leadership\n\n")
    fid.write("WP" + str(workingPartyNumber) + "/" + str(group) + " Management team\n\n")
    if len(chairs) == 1:
        fid.write("-   Chair: " + chairs[0] + "\n\n")
    else:
        for chair in chairs:
            fid.write("-   Vo-chair: " + chair + "\n\n")
    if len(viceChairs) >= 0:
        for viceChair in viceChairs:
            fid.write("-   Vice-chair: " + viceChair + "\n\n")
    fid.write("The following table reproduce the current list of WP" + str(workingPartyNumber) + "/" + str(group) + " Questions and related Rapporteurs\n\n")
    fid.write('[cols="4,12,4,4"]\n')
    fid.write(".Questions and related Rapporteurs\n")
    fid.write("|===\n")
    fid.write("|Question|Title|Rapporteur|Associate Rapporteurs\n\n")
    num = 0
    for questionNumber in questionNumbers:
        rapporteurs = getRapporteurs(questionsDetails[num])
        associateRapporteurs = getAssociateRapporteurs(questionsDetails[num])
        nlines = 1
        if len(rapporteurs) > nlines:
            nlines = len(rapporteurs)
        if len(associateRapporteurs) > nlines:
            nlines = len(associateRapporteurs)
        for i in range(0,nlines):
            if i == 0:
                questionName = 'Q' + str(questionNumber) + '/' + str(group)
                questionTitle = questionsDetails[num].title
            else:
                questionName = ''
                questionTitle = ''          
            if i < len(rapporteurs):
                rapporteur = rapporteurs[i]
            else:
                rapporteur = ''
            if i < len(associateRapporteurs):
                associateRapporteur = associateRapporteurs[i]
            else:
                associateRapporteur = ''
            fid.write("|" + questionName + "|" + questionTitle + "|" + rapporteur + "|" + associateRapporteur + "\n")
        num = num + 1 
    fid.write("\n|===\n\n")
    fid.write("== Documentation and email lists\n\n")
    fid.write("=== Documentation\n\n")
    fid.write("The following documents were discussed by WP" + str(workingPartyNumber) + "/" + str(group) + "Questions:\n\n")
    for questionNumber in questionNumbers:
        questionName = "Q" + str(questionNumber) + "/" + str(group)
        fid.write(questionName + ":\n\n")
        fid.write("- C: ")
        first = True
        for tableRow in reversed(cTableRows):
            selected = False
            for relatedQuestion in tableRow.questions:
                if relatedQuestion.value == questionName:
                    selected = True
                    break
            if selected:
                if not first:
                    fid.write(", ")
                first = False
                fid.write("link:" + URL + tableRow.number.link + "[C" + tableRow.number.value + tableRow.lastRev + "]")
        fid.write("\n")
        fid.write("- TD: ")
        first = True
        for tableRow in reversed(genTableRows):
            selected = False
            for relatedQuestion in tableRow.questions:
                if relatedQuestion.value == questionName:
                    selected = True
                    break
            if selected:
                if not first:
                    fid.write(", ")
                first = False
                fid.write("link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "]")
        first = True
        for tableRow in reversed(plenTableRows):
            selected = False
            for relatedQuestion in tableRow.questions:
                if relatedQuestion.value == questionName:
                    selected = True
                    break
            if selected:
                if not first:
                    fid.write(", ")
                first = False
                fid.write("link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "]")
        first = True
        for tableRow in reversed(wPTableRows):
            selected = False
            for relatedQuestion in tableRow.questions:
                if relatedQuestion.value == questionName:
                    selected = True
                    break
            if selected:
                if not first:
                    fid.write(", ")
                first = False
                fid.write("link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "]")
        fid.write("\n\n")
    fid.write("The complete documentation for this SG" + str(group) + " meeting is to be found at:\n\n")
    year = int(startDate[2:4])
    period = str(int(year / 4) * 4 + 1)
    documentation = "link:" + URL + "/md/T" + period + "-SG" + str(group) + "-" + startDate[2:] + "/sum/en"
    fid.write("link:" + documentation + "[" + documentation + "]\n\n")
    fid.write("=== Emailing list subscription\n\n")
    year = int(startDate[0:4])
    firstYear = int(year / 4) * 4 + 1
    lastYear = firstYear + 3
    webpage = "/en/ITU-T/studygroups/" + str(firstYear) + "-" + str(lastYear) + "/" + str(group) + "/Pages/ifa-structure.aspx"
    fid.write("E-mail correspondences pertaining to the activities of this working party and Questions under this working party are routinely conducted using the e-mail reflectors. For more information on available e-mail reflectors and informal FTP areas, please visit the dedicated " + URL + webpage + "[webpage].\n\n")
    year = int(startDate[0:4])
    firstYear = int(year / 4) * 4 + 1
    lastYear = firstYear + 3
    subscriptionWebpage = "/net4/iwm?p0=0&p11=ITU&p12=ITU-SEP-ITU-T-SEP-SP%2017-SEP-Study%20Group%2017&p21=ITU&p22=ITU"
    fid.write("Those wishing to subscribe or unsubscribe to SG" + str(group) + " email reflectors, please visit " + URL + subscriptionWebpage + "[subcription webpage].\n\n")
    fid.write("== WP" + str(workingPartyNumber) + "/" + str(group) + " opening plenary results\n\n")
    fid.write("=== Reports of interim Rapporteur meetings\n\n")
    fid.write("The following interim meetings of the rapporteur groups under this working party were reviewed and approved: \n\n")
    nmeetingReports = 0
    for questionNumber in questionNumbers:
        meetingReports = getMeetingReports(tableRows = wPTableRows,question = questionNumber,group = group)
        nmeetingReports = nmeetingReports + len(meetingReports)
    if nmeetingReports >= 0:
        fid.write('[cols="4,12,12,4"]\n')
        fid.write(".meeting reports\n")
        fid.write("|===\n")
        fid.write("|Question|Meeting|Date, Place|Report\n\n")
        for questionNumber in questionNumbers:
            questionName = "Q" + str(questionNumber) + "/" + str(group)
            meetingName = questionName + " Rapporteur meeting"
            meetingReports = getMeetingReports(tableRows = wPTableRows,question = questionNumber,group = group)
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
                fid.write("|" + questionName + "|" + meetingName + "|" + location + ", " + date + "|link:" + URL + meetingReport.number.link + "[TD" + meetingReport.number.value + "/" + str(workingPartyNumber) + "]\n\n")
        fid.write("\n|===\n\n")
    fid.write("_Include here summary of interim meeting results, esp. updates to candidate texts planned by last meeting for decision in this meeting._\n\n")
    fid.write("=== Other issues discussed at the opening plenary\n\n")
    fid.write("_Include here a report on additional issues discussed during the opening plenary of this WP, for example,_\n\n")
    fid.write("- _joint session,_\n\n")
    fid.write("- _workshop organized in the past period or during this meeting,_\n\n")
    fid.write("- _tutorial,_\n\n") 
    fid.write("- _appointment of ACTING Rapporteur for this meeting only,_\n\n") 
    fid.write("- _review of incoming liaison statements,_\n\n") 
    fid.write("- _reports from liaison officers, etc._\n\n")
    fid.write("=== Appointment of Rapporteurs, Associate Rapporteurs and Liaison Officers and other issues for SG" + str(group) + "closing plenary decisions\n\n")
    fid.write("_Include here any change in the list of Rapporteurs, Associate Rapporteurs and Liaison officers. For instance:_\n\n")
    fid.write("- _Mr name is no longer the Rapporteur of Qxx/" + str(group) + ". Ms name has been appointed as Rapporteur of Qxx/" + str(group) + "_\n\n")
    fid.write("- _Mr name will act as new liaison officer for organization XXX_\n\n")
    fid.write("- _Ms name has been appointed as Associate Rapporteur for Qyy/" + str(group) + "_\n\n")
    fid.write("_Identify any other important issues for SG" + str(group) + " closing plenary decision, except Question deliberations recorded in the section 5 below._\n\n")
    fid.write("== Questions meetings during SG" + str(group) + " meeting\n\n")
    fid.write("The reports of each Question under WP" + str(workingPartyNumber) + "/" + str(group) + " were reviewed and approved. The executive summary of the Questions meetings results is reported below. Reference to the Questions reports is provided for more details.\n\n")
    for questionNumber in questionNumbers:
        fid.write("=== Question " + str(questionNumber) + "/" + str(group) + "\n\n")
        questionReportTitle = "Report of Q" + str(questionNumber) + "/" + str(group)
        for wPTableRow in wPTableRows:
            if compareStripped(wPTableRow.title,questionReportTitle):
                questionReportNumber = wPTableRow.number.value.replace(' ','')
                questionReport = "link:" + URL + wPTableRow.number.link + "[TD" + str(wPTableRow.number.value) + wPTableRow.lastRev + "]"
                break
        fid.write("The report of Q" + str(questionNumber) + "/" + str(group) + " can be found in " + questionReport + ". It was approved.\n\n")
        fid.write("_Include here the executive summary of the results of this Question meeting, as drafted by the Rapporteur in the Question report under the item 2 “executive summary”._\n\n") 
        fid.write("_If needed, add discussions held during WP closing plenary._\n\n")
    fid.write('== Draft new/revised Recommendations proposed for "approval" (TAP) or "consent" (AAP) or "determination" (TAP)\n\n')
    if len(approval) >= 0:
        fid.write("=== Recommendations for TAP approval (WTSA Resolution 1,§9)\n\n")
        fid.write("The Following draft Recommendations are proposed for TAP approval.\n\n")
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
                a5text = "link:" + URL + a5.number.link + "[TD " + a5.number.value + a5.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.acronym) > 0:
                workItem = tD.recommendation + "(" + tD.acronym + ")"
            else:
                workItem = tD.recommendation
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|" + questionName + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
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
                a5text = "link:" + URL + a5.number.link + "[TD " + a5.number.value + a5.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.acronym) > 0:
                workItem = tD.recommendation + "(" + tD.acronym + ")"
            else:
                workItem = tD.recommendation
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|" + questionName + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
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
                a5Text = "link:" + URL + a5.number.link + "[TD " + a5.number.value + a5.lastRev + "/" + str(workingPartyNumber) + "]"
            if len(tD.recommendation) > 0:
                if len(tD.acronym) > 0:
                    workItem = tD.recommendation + "(" + tD.acronym + ")"
                else:
                    workItem = tD.recommendation
            else:
                workItem = tD.acronym
            textTitle = tD.textTitle
            fid.write("|" + str(num) + "|" + questionName + "|" + workItem + "| |" + insertEscape(textTitle) + "|" + finalText + "|" + a5Text + "|\n")
        fid.write("\n|===\n\n")
    fid.write("=== Non-normative text (e.g., Supplements, Technical Reports, Technical Papers, Implementors' Guides or other documents) for agreement\n\n")
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
            fid.write("|" + str(num) + "|" + questionName + "|" + str(element) + "| |" + insertEscape(tD.title) + "|" + finalText + "\n")
        fid.write("\n|===\n\n")
    fid.write("== Intellectual property statements\n\n")
    fid.write("The Chair of this WP meeting reminded the meeting participants of the ITU-T IPR Policy (see link:" + URL + "/en/ITU-T/ipr/Pages/default.aspx[IPR]) and asked those present whether anyone has knowledge of intellectual property rights issues, including patents, copyright for software or text, marks, the use of which may be required to implement or publish the Recommendation being considered.\n\n") 
    fid.write("The Chair of this WP meeting reminded the participants that any ITU-T member organization putting forward a standardization proposal should draw the attention of the TSB Director to any known or pending patent and any other applicable IPR issues.\n\n")
    fid.write("_No IPR statements were received at this meeting_\n\n")
    fid.write("_Company xxx submitted / promised to submit to TSB a patent declaration for draft Recommendation X.yyy_\n\n")
    fid.write("== Outgoing liaison statements\n\n")
    if len(outgoingLiaisonStatements) >= 0:
        fid.write("The following outgoing LSs were reviewed and prepared by the WP" + str(workingPartyNumber) + "/" + str(group) + "\n\n")
        fid.write('[cols="1,4,4,6,6,8,4"]\n')
        fid.write(".Outgoing liaison statements\n")
        fid.write("|===\n")
        fid.write("|#|Questions|WP|For action to|For information to|Title|TD\n\n")
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
            fid.write("|" + str(num) + "|" + srr(question) + "/" + str(group) + "|WP" + str(workingPartyNumber) + "|_" + destination + "_|_" + destination + "_|" + insertEscape(title) + "|" + tDName + "\n")
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
                baseText = "link:" + URL + tableRow.number.link + "[TD" + tableRow.number.value + tableRow.lastRev + "]"
                fid.write("|" + str(num) + "|" + questionName + "|" + workItem + "|New|" + insertEscape(textTitle) + "| |" + baseText + "| |\n")
        fid.write("\n|===\n\n")
    fid.write("Note: The latest SG" + str(group) + " Work programme can be found at link:" + URL + "/ITU-T/workprog/wp_search.aspx?sg=" + str(group) + "[Work programme]\n\n")
    fid.write("=== Deleted work items\n\n")
    if len(deletedWorkItems) >= 0:
        fid.write("The meeting agreed to discontinue the following work items:\n\n")
        fid.write('[cols="1,4,6,10"]\n')
        fid.write(".Deleted work items\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work Item|Title\n\n")
        num = 0
        for element in deletedWorkItems:
            num = num + 1
            title = ""
            tDName = ""
            questionName = ""
            (questionName,tD) = findTDByNumber(wPTableRows,element)
            if not tD is None:
                title = tD.textTitle
            fid.write("|" + str(num) + "|" + questionName + "|" + tD.acronym + "|" + insertEscape(title) + "\n")
        fid.write("|===\n\n")
    fid.write("=== Updated WP" + str(workingPartyNumber) + " work programme\n\n")
    fid.write("The current list of ongoing work items, including eventual new work items agreed at this meeting. (see item [[9.1]] above) as follows:\n\n")
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
            questionName = ""
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
            fid.write("|" + str(num) + "|" + questionName + "|" + str(element) + "|" + status + "|" + insertEscape(title) + "| |" + tDName + "| | |\n")
        fid.write("|===\n\n")
    fid.write("Note: The latest SG" + str(group) + " Work programme can be found at link:" + URL + "/ITU-T/workprog/wp_search.aspx?sg=" + str(group) + "[Work programme]\n\n")
    fid.write("== Candidate work items for decision at the next SG" + str(group) + " meeting\n\n")
    if len(candidateForNextMeeting) >= 0:
        fid.write("The following work items are planned for decision at next SG" + str(group) + " meeting\n\n")
        fid.write('[cols="1,4,4,4,10,8,4,4,4"]\n')
        fid.write(".Candidate work items for next SG" + str(group) + " meeting\n")
        fid.write("|===\n")
        fid.write("|#|Question|Work item|Status|Title|Editor|Base Text|A.5 justification|Equivalent e.g.,ISO/IEC\n\n")
        num = 0
        for element in candidateForNextMeeting:
            num = num + 1
            title = ""
            tDName = ""
            questionName = ""
            (questionName,tD) = findTDByName(wPTableRows,element)
            if not tD is None:
                title = tD.textTitle
                tDName = "link:" + URL + tD.number.link + "[TD" + tD.number.value + tD.lastRev + "/" + str(workingPartyNumber) + "]"
            fid.write("|" + str(num) + "|" + questionName + "|" + str(element) + "| |" + insertEscape(title) + "| | " + tDName + "| |\n")
        fid.write("\n|===\n\n")
    fid.write("== Planned interim Rapporteurs meetings\n\n")
    fid.write("The following interim Rapporteurs group meetings for Questions unser WP" + str(workingPartyNumber) + "/" + str(group) + " are proposed for approval\n\n")
    if len(rapporteurMeetings) >= 0:
        fid.write('[cols="1,4,4,10,8"]\n')
        fid.write(".Interim Rapporteur meetings\n")
        fid.write("|===\n")
        fid.write("|Question|Date|Place/Host|Terms of reference|Contact\n\n")
        num = 0
        for element in rapporteurMeetings:
            num = num + 1
            fid.write("|" + str(question.number) + "/" + str(group) + "| | | |\n")
        fid.write("\n|===\n\n")
        fid.write("Details will be posted on the ITU-T SG" + str(group) + " Rapporteur Group meetings website: link:" + URL + "/net/ITU-T/lists/rgm.aspx?Group=" + str(group) + "&type=interim[Rapporteur Group meetings website]\n\n")
    fid.write("== Scheduled WP or SG" + str(group) + " meetings\n\n")
    fid.write("=== Interim WP" + str(workingPartyNumber) + "/" + str(group) + " meetings are provided below\n\n")
    if len(interimMeetings) >= 0:
        fid.write('[cols="1,4,4,10,8"]\n')
        fid.write(".Interim WP" + str(workingPartyNumber) + "/" + str(group) + "meetings\n")
        fid.write("|===\n")
        fid.write("|WP|Date|Place/Host|Terms of reference|Contact\n\n")
        num = 0
        for element in interimMeetings:
            num = num + 1
            fid.write("|" + str(workingPartyNumber) + "/" + str(group) + "| | | |\n")
        fid.write("\n|===\n\n")
    else:
        fid.write("WP" + str(workingPartyNumber) + "/" + str(group) + " does not plan to origanize a WP " + str(workingPartyNumber) + "/" + str(group) + " before the next SG" + str(group) + " meeting in Month 20yy\n\n")
    fid.write("=== WP" + str(workingPartyNumber) + "/" + str(group) + " meeting during the next SG" + str(group) + " meeting\n\n")
    fid.write("WP" + str(workingPartyNumber) + "/" + str(group) + " is also planning to meet again during the next SG" + str(group) + " meeting to be held in _city country, x.ymonth, 20yy_\n\n")
    fid.write("Details will be posted on the ITU-T SG" + str(group) + " website:link:" + URL + "/go/tsg" + str(group) + "[SG" + str(group) + "]\n\n")
    fid.write("== Conclusion\n")
    fid.write("_The WPy/17 Chair thanked the delegates for their enthusiastic and active participation in the relevant activities of Working Party y/17 and each Question during the meeting. Special thanks were expressed to the SG17 Counsellor, Ms Xiaoya Yang (TSB), SG17 Project Officer Ms Gillian Makamara (TSB) and SG17 assistant Ms Erika Yoris (TSB) as well as all Associate Rapporteurs, Editors, and contributors for their dedicated and sustained efforts during this meeting._\n\n")
    fid.write("[appendix]\n")
    fid.write("[align=center]\n")
    fid.write("== [[Annex_A]]\n\n")
    fid.write("[align=center]\n")
    fid.write("A1. or A13 justification for new work items\n\n")
    fid.write("_Copy and past here all the A.1 and A.13 justification templates that were added in annex to each Question meeting report, if any._\n\n")
    fid.write("\n\n")
fid.close()
sys.exit()
