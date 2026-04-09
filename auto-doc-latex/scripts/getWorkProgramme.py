class WorkItem(object):
    def __init__(self,workItem = None,question = None,title = None,timing = None,group = None,period = None,version = None,status = None):
        self.workItem = workItem
        self.question = question
        self.title = title
        self.timing = timing
        self.group = group
        self.period = period
        self.version = version
        self.status = status
    def dump(self):
        print("wotkItem " + str(self.workItem))
        print("question " + str(self.question))
        print("title" + str(self.title))
        print("timing " + str(self.timing))
        print("group " + str(self.group))
        print("period " + str(self.period))
        print("version " + str(self.version))
        print("status " + str(self.status))

def getWorkProgramme(workProgrammeFile):
    workItems = []
    try:
        fid = open(workProgrammeFile,"rt",encoding = "iso-8859-1")
        lines = fid.readlines()
        fid.close()
    except:
        print("Error while reading work program file\n")
        return None
    first = False
    for line in lines:
        elements = line[:len(line) - 1].split(";")
        if not first:
            if elements[0] == "Work Item":
                first = True
        else:
            if len(elements) > 7:
                workItem = WorkItem(workItem = elements[0],question = elements[1],title = elements[2],timing = elements[3],group = elements[4],period = elements[5],version = elements[6],status = elements[7])
            else:
                workItem = WorkItem(workItem = elements[0],question = elements[1],title = elements[2],group = elements[3],period = elements[4],version = elements[5],status = elements[6])
                timing = ""
            workItems.append(workItem)
    return workItems
