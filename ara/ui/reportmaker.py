#!/usr/bin/python

import os
import sys
import csv
from datetime import datetime, timedelta

####################################################################
## ----------------------------TODO---------------------------------
## - handle missing log parts (in progress)
##   need to finish correctmissingdata()
## - fix linux problems (testing)
## - collect updates from sles
## ---------------------------HISTORY-------------------------------
## last update: 2019.03.11
## - more status on console
## last update: 2019.03.27
## - updates on loghandling
## last update: 2019.04.16
## - listfiles() to getfiles()
## last update: 2019.04.17
## - implement checkfiles()
## last update: 2019.04.18
## - update writetocsv() -> new format to fix linux problems
##   not finished yet
## - rewrote arguement handling
## last update: 2019.04.25
## - implement getlogsbydate()
## - linux problems seems to be fixed
## - collected updated stuff for ubuntus
## - removed updates from writetocsv()
## - corrected some comments, added new info, refactor, etc
## last update: 2019.05.21
## - fix loglisting
## - rewrite logcollecting method (not older than 7 days)
####################################################################

class ReportMaker:

    ## write the logdata from dictionary list into csv file
    def writetocsv(logdata, logdate, logname):
            filename = '{}_{}.csv'.format(logname, logdate)
            try:
                    with open(filename, 'w', newline='') as logfile:
                            logdatawriter = csv.writer(logfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                            logdatawriter.writerow(
                                    [
                                            'PC Name',
                                            'Updates Required Before Patching',
                                            'Updates Installed On This Month',
                                            'Total Missing Updates After Patching',
                                            'Missing Critical Or Security Updates',
                                            'Current Compliance',
                                            'OS',
                                            'Comments'
                                    ]
                            )

                            for log in logdata:
                                    tmparr = []
                                    for k in log:
                                            tmparr.append(log[k])
                                    logdatawriter.writerow(tmparr)
                    return "{} is ready".format(filename)
            except Exception as e:
                    return e

    ## detecting os from zypper patch list
    ## using zypper patch list result
    ## return back osdict
    ## osdict = {pcname:pcname,os:os}
    def detectos(datadict):
            osdict = {}
            for k, v in datadict.items():
                    if v != "skipping":
                            osdict[k] = "Ubuntu"
                    else:
                            osdict[k] = "SLES"
            return osdict

    ## merging unattended and zypper patch resultdicts into one dict
    ## resultdictlist = [{pcname:pcname,os:os,log:log},{pcname:pcname,os:os,log:log}]
    def mergedicts(taskdictlist, osdict):
            resultdictlist = []
            resultdict = {}

            if len(taskdictlist) == 2:
                    for k in taskdictlist[0]:
                            tmpdict = {}
                            tmpdict['pcname'] = k
                            tmpdict['os'] = osdict[k]
                            if taskdictlist[0][k] == "skipping":
                                    tmpdict['log'] = taskdictlist[1][k]
                            else:
                                    tmpdict['log'] = taskdictlist[0][k]
                            resultdictlist.append(tmpdict)
            elif len(taskdictlist) == 3:
                    for k in taskdictlist[0]:
                            tmpdict = {}
                            tmpdict['pcname'] = k
                            tmpdict['os'] = osdict[k]
                            if taskdictlist[1][k] == "skipping":
                                    tmpdict['log'] = taskdictlist[2][k]
                            else:
                                    tmpdict['log'] = taskdictlist[1][k]
                            resultdictlist.append(tmpdict)
            return resultdictlist

    ## rework the lines
    ## remove empty lines and lines starts with play
    def makeloglinelist(lines):
            syslogs = []
            options = ['all', 'sles', 'ubuntu']
            tmplines = []

            for i in range (0, len(lines)):
                    tmplist = lines[i].split()
                    if lines[i][0] == "PLAY" and lines[i][1][1:(len(tmplist[1]) - 1)] in options:
                            if len(lines[i]) > 0:
                                    syslogs.append(lines[i])
                                    tmplines = []
                    else:
                            tmplines.append(lines[i])

            if len(tmplines) > 0:
                    syslogs.append(tmplines)
            return syslogs

    def makedict(taskarr, detect):
            taskdict = {}
            osdict = False
            for x in range(0, len(taskarr)):
                    tmparr = taskarr[x].split()
                    if tmparr[0][0:(len(tmparr[0]) - 1)] == "skipping":
                            taskdict[tmparr[1][1:(len(tmparr[1]) - 1)]] = "skipping"
                    elif "=>" in tmparr and tmparr[(tmparr.index('=>')) + 1] == "{":
                            taskdict[tmparr[1][1:(len(tmparr[1]) - 1)]] = taskarr[x + 1].split('\\n\\n')[-1]

            if detect:
                    osdict = detectos(taskdict)
            return [taskdict, osdict]

    ## remove the useless parts from the array
    ## only keep the unattended and zypper patch list for the merge function
    ## returning a list with only the print the list results (2 or 3 item)
    ## unattended patch list, unattended updated list, zypper patch list
    def cleantaskarray(taskdict):
            tasklist = []

            for k, v in taskdict.items():
                    if k.split(':')[1] == "Print the list":
                            tasklist.append(v)
            return tasklist

    ## cut out the current taskname from the line
    def gettaskname(linearr):
            taskarr = []
            isname = False

            for tmpstr in linearr:
                    if tmpstr[0] == "[":
                            isname = True
                            tmpname = tmpstr
                            if tmpname[-1] == "]":
                                    return tmpname[0:(len(tmpname) - 1)]
                            taskarr.append(tmpstr)
                    elif isname and tmpstr[-1] != "]":
                            taskarr.append(tmpstr)
                    elif isname and tmpstr[-1] == "]":
                            taskarr.append(tmpstr)
                            isname = False
            tmpstr = " ".join(taskarr)
            return tmpstr[1:(len(tmpstr) - 1)]

    ## split lines into taskarray
    ## and send it to cleantaskarray function
    ## taskdict = [{'taskx:taskname':content},{'taskx:taskname':content}]
    def maketaskarray(loglinelist):
            taskdict = {}
            tmparr = []
            taskname = ""
            istask = False

            for x in range(0, len(loglinelist)):
                    tmplinearr = loglinelist[x].split()

                    if istask and tmplinearr[0] != "TASK" and tmplinearr[0] != "PLAY":
                            tmparr.append(loglinelist[x])

                    if tmplinearr[0] == "TASK":
                            istask = True
                            if len(tmparr) > 0:
                                    taskdict['task{}:{}'.format(x, taskname)] = tmparr
                                    tmparr = []
                            taskname = gettaskname(tmplinearr)
                    elif tmplinearr[0] == "PLAY":
                            istask = False
                            if len(tmparr) > 0:
                                    taskdict['task{}:{}'.format(x, taskname)] = tmparr
                                    tmparr = []
            return cleantaskarray(taskdict)

    ## return the current vmname from the line
    def getvmname(line):
            return line.split(':')[1].split('=>')[0]

    ## this function open the file, read the content
    ## cut the usable infos and make dict
    def handlelog(logfile, prefix):
            loglinelist = []
            taskdictlist = []
            boollist = [True, False, False]
            osdict = {}

            try:
                    with open(logfile, 'r') as f:
                            text = f.read()
                            lines = list(filter(bool, text.split('\n')))
                            loglinelist = makeloglinelist(lines)
                            print("logfile {} parsed".format(logfile))
            except:
                    print("'{}' not found".format(logfile))
                    exit()
            tmparr = loglinelist[0]
            tasklist = maketaskarray(tmparr)

            for x in range(0, len(tasklist)):
                    result = makedict(tasklist[x], boollist[x])
                    if result[1]:
                            osdict = result[1]
                    taskdictlist.append(result[0])
            return mergedicts(taskdictlist, osdict)


    ## check arguements and giving back the filelist
    ## if only one filename was given this function give an another one depends on given
    def handlelognames(filenames):
            acceptedext = ['txt', 'log']
            defaultext = "log"
            filelist = []
            tmpfilelist = filenames

            ## this part add a secondary filename to the list if its missing
            if len(tmpfilelist) < 2:
                    tmparr = tmpfilelist[0].split('_')
                    secondfilename = ""
                    secondary = ""
                    if "pre" in tmparr:
                            tmparr[tmparr.index('pre')] = "post"
                    elif "post" in tmparr:
                            tmparr[tmparr.index('post')] = "pre"
                    else:
                            print('there is a problem with the filenames!')
                            exit()
                    tmpfilelist.append("_".join(tmparr))

            for tmpfname in tmpfilelist:
                    tmpfname = tmpfname.strip()
                    tmparr = tmpfname.split('.')
                    if len(tmparr) == 1:
                            tmparr.append(defaultext)
                            filelist.append('.'.join(tmparr))
                    elif tmparr[-1] in acceptedext:
                            filelist.append('.'.join(tmparr))

            if len(filelist) < 1:
                    print('there is a problem with the filenames!')
                    exit()
            return filelist

    ## check logdate in filenames and use currentdate if not find
    ## this function was made for the older version but I leave it here for later
    def getdate(fnames):
                currentdate = datetime.now()
            logdate = currentdate.strftime('%Y-%m-%d')

            for fname in fnames:
                    fname = fname.split('.')[0].split('_')[-1]
                    if len(fname.split('-')) == 3 and fname != logdate:
                            return fname
            return logdate

    ## patches "needed" after
    def getmissingsecurityupdates(data):
            missingsecuritynumber = 0
            tmparr = data.split('\\n')
            tmplinearr = tmparr[-1].split()
            if tmplinearr[0].isdigit():
                    return tmplinearr[0]
            return missingsecuritynumber

    ## "needed" from prelog
    def getsecurityupdatesbeforepatch(data):
            securityupdatesbeforepatch = 0
            tmparr = data.split('\\n')[-1].split()

            if tmparr[2] == "needed" and tmparr[0].isdigit():
                    return tmparr[0]
            return securityupdatesbeforepatch

    ## found from pastlog
    def gettotalmissingafterpatch(data):
            securityupdatesafterpatch = 0
            tmparr = data.split()
            for i in range (0, len(tmparr)):
                    if tmparr[i] == "needed" and tmparr[i - 1] == "patches" and tmparr[i - 2].split('\\n')[-1].isdigit():
                            return tmparr[i - 2].split('\\n')[-1]
            return securityupdatesafterpatch

    ## collecting updatedatas from log
    ## return dict = {'secupbefpatch':int,'totmisupdaftpatch':int, 'updated':[mysql, tzdata, initframz, ..]}
    def collectubuntuupdates(data):
            resultdict = {}
            resultdict['secupbefpatch'] = 0
            resultdict['totmisupdaftpatch'] = 0
            resultdict['updated'] = []
            updated = []
            resultarr = []
            tmparr = data.split('\\n')

            for tmp in tmparr:
                    tmplinestr = tmp.strip()
                    tmplinearr = tmplinestr.split(':')[-1].split()
                    for tmpstr in tmplinearr:
                            tmpname = tmpstr[0:(len(tmpstr) - 1)] if tmpstr[-1] == '"' else tmpstr
                            resultarr.append(tmpname)

            if len(resultarr) > 0:
                    resultdict['updated'] = list(dict.fromkeys(resultarr))
                    resultdict['secupbefpatch'] = len(resultarr)
            return resultdict

    def evaluatelogs(prelogs, postlogs):
            resultlogdictlist = []

            ## need to sort logdicts because its originally messed up
            ## and sometimes giving shit results
            prelogs = sorted(prelogs, key=lambda k: k['pcname'])
            postlogs = sorted(postlogs, key=lambda k: k['pcname'])

            for x in range(0, len(prelogs)):
                    tmpdict = {}
                    ##############################################################
                    # the necessary keys are:
                    # - pcname
                    # - securityupdates required before
                    #   patching (secupbefpatch)
                    # - updates installed on this month (updinsthismon)
                    # - total missing updates after patching (totmisupdaftpatch)
                    # - missing critical or security Updates (miscritorsecupd)
                    # - current compliance (currentcomp)
                    #   [updates installed on this month/
                    #   securityupdates required before patching]
                    # - os
                    # - comments
                    ##############################################################

                    ## predefined variables
                    pcos = prelogs[x]['os']
                    securityupdatesbeforepatch = 0
                    totalmissingafterpatch = 0
                    currentcompliance = "0%"
                    missingcritical = getmissingsecurityupdates(postlogs[x]['log'])

                    ## this part is depends on the os
                    if pcos == "Ubuntu":
                            ubuntuupdates = collectubuntuupdates(postlogs[x]['log'])
                            securityupdatesbeforepatch = ubuntuupdates['secupbefpatch']
                            totalmissingafterpatch = ubuntuupdates['totmisupdaftpatch']
                    else:
                            securityupdatesbeforepatch = getsecurityupdatesbeforepatch(prelogs[x]['log'])
                            totalmissingafterpatch = gettotalmissingafterpatch(postlogs[x]['log'])
                    updatesinstalledthismonth = int(securityupdatesbeforepatch) - int(totalmissingafterpatch)

                    if int(updatesinstalledthismonth) > 0 and int(securityupdatesbeforepatch) > 0:
                            currentcompliancenumber = int(int(int(updatesinstalledthismonth) / int(securityupdatesbeforepatch)) * 100)
                            currentcompliance = "{}%".format(currentcompliancenumber) if int(currentcompliancenumber) != 0 else "100%"

                    ## build up log dictionary
                    tmpdict['pcname'] = prelogs[x]['pcname']
                    tmpdict['secupbefpatch'] = securityupdatesbeforepatch
                    tmpdict['updinsthismon'] = updatesinstalledthismonth
                    tmpdict['totmisupdaftpatch'] = totalmissingafterpatch
                    tmpdict['miscritorsecupd'] = missingcritical
                    tmpdict['currentcomp'] = currentcompliance
                    tmpdict['os'] = pcos
                    tmpdict['comments'] = " "
                    resultlogdictlist.append(tmpdict)
            return resultlogdictlist

    def askforfile(filenames):
            if len(filenames) == 2:
                    return input('{}, {} are correct? [y,n]\n'.format(filenames[0], filenames[1]))
            else:
                    return input('choose a date: [02-04]\n')

    def getfiles(path):
            #files = [f for f in os.listdir(path) if os.path.isfile(f)]
            files = [f for f in os.listdir(path)]
            return [f for f in files if f.split('.')[-1] == "log"]

    def getlogsbydate(logdate, loglist):
            logs = []
            for log in loglist:
                    datearr = log.split('_')[-1].split('.')[0].split('-')
                    del datearr[0]
                    if '-'.join(datearr) == logdate:
                            logs.append(log)
            return logs

    ## check 'logs' directory (/home/toor/logs)
    def checklogdir():
            if os.name == 'nt':
                    return False
            return os.path.isdir('/home/toor/logstest ')

    ## check if there is logfiles for the current date and ask to use it
    ## pattern = "update_pre_sun_2019-01-06"
    def checkfiles(filelist, currentdate):
            logfiles = []
            if "update_pre_sat_{}".format(currentdate) in filelist and "update_post_sat_{}".format(currentdate) in filelist:
                    logfiles.append('update_pre_sat_{}'.format(currentdate))
                    logfiles.append('update_post_sat_{}'.format(currentdate))
            elif "update_pre_sun_{}".format(currentdate) in filelist and "update_post_sun_{}".format(currentdate) in filelist:
                    logfiles.append('update_pre_sun_{}'.format(currentdate))
                    logfiles.append('update_post_sun_{}'.format(currentdate))
            return logfiles

    ## check if there is a missing data or server and fill it with 0
    def correctmissingdata(prelog, postlog):
            if len(prelog) == len(postlog):
                    return [prelog, postlog]
            elif len(prelog) > len(postlog):
                    newpostlog = []
                    for i in range (0, len(prelog)):
                            if prelog[i]['pcname'] == postlog[i]['pcname'] or i > len(postlog):
                                    newpostlog.append(postlog[i])
                            else:
                                    newpostlog.append(prelog[i])
                    postlog = newpostlog
            return [prelog, postlog]

    def checkdayrange(date, logs):
            filteredlogs = []
            for i in range (0, len(logs)):
                    logarr = logs[i].split('.')
                    del logarr[-1]
                    if ".".join(logarr).split('_')[-1] != "sed" and ".".join(logarr).split('_')[-1] != "x":
                            logdate = ".".join(logarr).split('_')[-1]
                            dateobj = datetime.strptime(date, '%Y-%m-%d')
                            logdateobj = datetime.strptime(logdate, '%Y-%m-%d')
                            datediff = abs(dateobj - logdateobj).days
                            if datediff <= 7:
                                    filteredlogs.append(logs[i])
            return filteredlogs

    ## handle arguements
    ## day before date = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
    def run(args):
            logfiles = []
            fname = "patchlog"
            isfilenamedefault = True
            currentdate = datetime.now()
            formatdate = currentdate.strftime('%Y-%m-%d')

            if len(args) == 2:
                    logfilename = args[1]
                    print(logfilename)
            #exit()
            ## check arguements and call the requested functions to build the datas for generate
            if "-l" in args and len(args) >= (args.index('-l') + 1):
                    logfiles = handlelognames(args[args.index('-l') + 1])

            ## check or ask for log files if its not in arguments
            if len(logfiles) < 2:
                    filelist = getfiles('.')
                    if checklogdir():
                            filelist = []
                            morelogs = getfiles('/home/toor/logstest')
                            filteredlogs = checkdayrange(formatdate, morelogs)
                            for i in range (0, len(filteredlogs)):
                                    filelist.append(filteredlogs[i])
                    for f in filelist:
                            print('filename: {}'.format(f))
                    answer = askforfile(checkfiles(filelist, formatdate))
                    if answer.lower() == "y":
                            logfiles = filelist
                    else:
                            logfiles = handlelognames(getlogsbydate(answer, filelist))
            ## it does matter how files are sorted be thats why this part is here and work this way
            logfiles.sort()
            logfiles.sort(reverse=True)

            if isfilenamedefault:
                    tmparr = logfiles[0].split('_')
                    if "sat" in tmparr:
                            fname = fname + "_sat"
                    elif "sun" in tmparr:
                            fname = fname + "_sun"

            ## handlelog returns: resultdictlist = [{pcname:pcname,os:os,log:log},{pcname:pcname,os:os,log:log}]
            predata = handlelog(logfiles[0], 'pre')
            postdata = handlelog(logfiles[1], 'post')
            #logdictlist = evaluatelogs(correctmissingdata(predata, postdata))
            logdictlist = evaluatelogs(predata, postdata)
            logdate = getdate(logfiles)
            return writetocsv(logdictlist, logdate, fname)

    def get_reports():
        getfiles('home/ara/reports')

    def get_logs():
        getfiles('/home/ara/logs/')

#    ## run the program with args
#    if __name__ == "__main__":
#            print(run(sys.argv))
