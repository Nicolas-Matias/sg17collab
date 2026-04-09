def commaSeparatedList(elements):
    first = True
    elementList = ""
    for element in elements:
        if not first:
            elementList = elementList + ", "
        first = False
        elementList = elementList + str(element)
    return elementList

def findTDByName(tableRows,name):
    questionName = ""
    tD = None
    for tableRow in tableRows:
        if name in tableRow.title:
            questionName = tableRow.questions[0].value
            tD = tableRow
            break
    return (questionName,tD)

def findTDByNumber(tableRows,number):
    questionName = ""
    tD = None
    for tableRow in tableRows:
        if str(number) == tableRow.number.value:
            questionName = tableRow.questions[0].value
            tD = tableRow
            break
    return (questionName,tD)

def findQuestionNameTDandA5(tableRows,number):
    questionName = ""
    tD = None
    a5 = None
    title = None
    for tableRow in tableRows:
        questionName = tableRow.questions[0].value
        if str(number) == tableRow.number.value:
            tD = tableRow
            title = tableRow.title
            break
    if not title is None:
        for tableRow in tableRows:
            if title in tableRow.title and "A.5" in tableRow.title:
                a5 = tableRow
                break
    return(questionName,tD,a5)

def compareStripped(string1,string2):
    stripped1 = string1.replace(' ','')
    stripped2 = string2.replace(' ','')
    return stripped1 == stripped2

def strippedStartsWith(string1,string2):
    stripped1 = string1.replace(' ','')
    stripped2 = string2.replace(' ','')
    return string2.startswith(string1)

def insertEscape(text):
    updatedText = ""
    for character in text:
        if character == '|':
            updatedText = updatedText + "\\"
        updatedText = updatedText + character
    return updatedText

def isNewWorkItem(string):
    lowerString = string.lower()
    if 'new' in lowerString and 'work' in lowerString and 'item' in lowerString:
        return True
    else:
        return False
