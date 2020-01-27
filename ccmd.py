#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script uses OS utilities such as ping, traceroute, ncat or any other specified by commands,
to run command probes against targets. 


Things to implement:
4) parser.add_argument('-nolog', action='store_true', dest='NOLOG', default=False, help='Do not store any logs N/A')
5) use pretty print colouring of output to make it look nice

Misc:
run pyinstaller --onefile hello.py to convert to exe
"""

from platform import system as platform_system
# from subprocess import call as subprocess_call
import subprocess
from os import path as os_path
from os import mkdir as os_mkdir
from os import system as os_system
from copy import copy as copy_copy
from threading import Thread as threading_Thread
from sys import stdout as sys_stdout                           #need it to delete lines in Linux to clear screen
from argparse import ArgumentParser as argparse_ArgumentParser #used to get variables from user input
from socket import gethostbyaddr
from socket import gethostbyname
from ipaddress import IPv6Network as ipaddress_IPv6Network
from ipaddress import IPv4Network as ipaddress_IPv4Network
import time                                                       #need it to get current time to form timestamps and log files names
try: from dns import reversename, resolver
except: print("No 'dnspython' module installed. Install: python -m pip install dnspython")


LINUX_CURSOR_UP_ONE = '\x1b[1A'
LINUX_ERASE_LINE = '\x1b[2K' 

defaultCommand=[]                   #list - to contain probe command string depending on OS type
hostIndex = ''                      #variable to store target to test index in defaultCommand to replace it later on with target IP or name
ctime = time.ctime()                #get current time to form names of log files
threads=[]                          #list - to contain all started threads for joining them
logMainDir = "./LOGS/"              #main LOG directory
logSumFileName = '{}_SumLOGG.txt'   #name of summary log file to store terminal output
logFileName = '{}_LOG.txt'          #name of log file for each target
targetsList = []                    #list of "targetDict" dictionaries to store target details .
targetDict = {                      #dictionary created for each target to store its details:
            'target': '',           #string - IP or name of target to run probe against
            'Description': '',      #string - description of target to print on screen
            'Command': '',          #string, to save command in string format
            'DNS': '',              #string - FQDN or IP we get from DNS for reverse or forward lookup
            'commandList': '',      #list of strings - to store command parameters to run with subprocess module
            'hostIndex': hostIndex, #indeger, reference to index in defaultCommand to replace it with target IP or name 
            'results': '',          #string - probe run results to print on screen
            'logFile': ''           #file object - file to store logs to for this particular target
            }
splitChar = ','                     #character used to split data in SrcFile
formatter = ''                      #string, used to format results output for cli printing
header = ''                         #string, used to contain header information for priniting to cli

#build argparser based menu:
parser = argparse_ArgumentParser(description="""
Concurrent Command to Multiple Destinations - run
commands against targets in semi-parallel fashion.
""")
parser.add_argument('-c', action='store', dest='PROBECOUNT', default=100, type=int, help='Number of probes to run, default - 100')
parser.add_argument('-b', action='store', dest='barLen', default=60, type=int, help='Length of probe history bar, default - 60')
parser.add_argument('-i', action='store', dest='PROBEINTERVAL', default=1000, type=int, help='Interval between probes in ms, default - 1000ms')
parser.add_argument('-w', action='store', dest='PROBETIMEOUT', default=1000, type=int, help='Probe timout interval in ms, default - 1000ms')
parser.add_argument('-t', action='store', dest='numberOfThreads', default=80, type=int, help='Number of simulteneous probe threads, default - 80')
parser.add_argument('-p', action='store', dest='logSubDirPrefix', default='TEST', type=str, help='String prefix for logs directory name')
parser.add_argument('-C', action='store', dest='USERCOMMAND', default='', type=str, help='Command to run, default - ping.')
parser.add_argument('-s', action='store', dest='SrcFile', default='./targets.txt', type=str, help='Path to targets file, default - ./targets.txt')
parser.add_argument('-ts', action='store', dest='TARGETS', default=False, type=str, help='Targets comma separated string')
parser.add_argument('-T', action='store_true', dest='TRACE', default=False, help='Run traceroute command')
parser.add_argument('-P', action='store_true', dest='PING', default=False, help='Run ping command')
parser.add_argument('-D', action='store_true', dest='DNS', default=False, help='Perform DNS resolution')
parser.add_argument('-DS', action='store', dest='DNSSRV', default=False, help='Same as -D but uses given server IP, need dnspython')
parser.add_argument('-S', action='store_true', dest='SILENT', default=False, help='Silent mode - print results to logfiles only')
parser.add_argument('-SS', action='store_true', dest='SSILENT', default=False, help='Same as -S, but print only final result to summary log')
parser.add_argument('-json-report', action='store_true', dest='JSON_REPORT', default=False, help='Saves report of results to file in JSON format')
parser.add_argument('-diff', action='store', dest='DIFF_SOURCE', default='', type=str, help='OS path to JSON report file to compare results with')
parser.add_argument('-v', action='store_true', dest='SHVER', default=False, help='Show version')


#extract argparser arguments:
args = parser.parse_args()
PROBECOUNT=args.PROBECOUNT             # number of probes to send
barLen=args.barLen                     # len of probes history bar
PROBEINTERVAL=args.PROBEINTERVAL       # interval between probes in ms
PROBETIMEOUT=args.PROBETIMEOUT         # probe timout interval in ms
numberOfThreads=args.numberOfThreads   # counter to regulate the number of simulteneous probe threads
logSubDirPrefix=args.logSubDirPrefix   # prefix used to form log sub directory name
USERCOMMAND=args.USERCOMMAND           # command to run, Default - ping
SrcFile=args.SrcFile                   # file name and location with targets' names or IPs
TRACE=args.TRACE                       # if TRACE==True, run traceroute, means form traceroute command and set thread timeout to 30 seconds
PING=args.PING                         # if PING==True, run PING command
DNS=args.DNS                           # if DNS==True, try to resolve IP addresses of targets to their names using DNS and update description strings accordingly
DNSSRV=args.DNSSRV                     # IP address of DNS Server to use for reverse lookups
TARGETS=args.TARGETS                   # string, contains comma separated targets values, like 8.8.8.8,ya.ru,192.168.1.0/27
SHVER=args.SHVER                       # boolean, if present print version and script info to the screen
SILENT=args.SILENT                     # boolean, if True engage silent mode - do not print progress to terminal screen
SSILENT=args.SSILENT                   # boolean to enable super silent mode, by only printig filnal result to summary log file
JSON_REPORT=args.JSON_REPORT           # boolean to indicate if JSON report need to be produced
DIFF_SOURCE=args.DIFF_SOURCE           # pass to json report of previous runs to compare with

if SSILENT:
    SILENT = True

if SHVER:
    raise SystemExit("""Version: 1.5.0
Python: 3.x
OS: Windows 7/10, Linux Ubuntu/CentOS
Release: 19/Dec/2019
    """)

#check logic:
if USERCOMMAND != '' and TRACE==True:
    raise SystemExit('ERROR: Cannot simelteniously run traceroute and "{}"'.format(USERCOMMAND))
if USERCOMMAND != '' and PING==True:
    raise SystemExit('ERROR: Cannot simelteniously run ping and "{}"'.format(USERCOMMAND))
elif PING == True and TRACE==True:
    raise SystemExit('ERROR: Cannot simelteniously run ping and traceroute command')

#form logs subdirectory name:
logSubDirName = logSubDirPrefix + '_' + ctime.replace(" ", "_").replace(":","-") +'/'  #string to form log sub directory name using current time

def chmkdir(path):
    #check if directory exists if not, make it:
    if not os_path.exists(path): 
        os_mkdir(path)

#create main LOGS directory, create it if not exists:        
chmkdir(logMainDir)
chmkdir(logMainDir + logSubDirName)

#create summary logs file:
logSumFileObj = open(logMainDir + logSubDirName + logSumFileName.format(ctime.replace(" ", "_").replace(":","-")), 'a', buffering=1)

def checkIP(string):
    """function to check that given string is IPv4 address
    """
    isIP = False
    if '.' in string: #check that '.' in string
        if len(string.split('.')) == 4: #check that we have 4 elements
            for item in string.split('.'): 
                if item.isdigit(): #check that each element is digit and is in range between 0 and 255
                    if int(item) in range(0, 256): #need to check range up to 256 as range not includes last digit - 256 - itself
                        isIP = True
                    else:
                        isIP = False
                        break                        
                else:
                    isIP = False
                    break
        else: isIP = False
    else: isIP = False
    return isIP
    
def DNSresolve(target, dnsServer):
    """
    Variables:
        target - string, ip address of target
        dnsServer - boolean or string, False by default or IP address of DNS server to use for reverse lookups
    Returns:
        Updates global target dictionary with retrived DNS FQDN if any
    """
    #handle case then DNS Server IP given:
    if dnsServer != False and checkIP(dnsServer) == True: #use dns library to query reverse lookup against given DNS server:
        try:
            if SILENT == False:
                #print('Resolving {}...'.format(target['target']))
                pass
            my_resolver = resolver.Resolver()
            my_resolver.nameservers = [dnsServer.strip("'").strip('"')]
            #check that target is IP address, if so - do reverse DNS lookup:
            if checkIP(target['target']) == True:
                rev_name = reversename.from_address(target['target'])
                targetName = str(my_resolver.query(rev_name,"PTR")[0])
                target['DNS'] = targetName
            #if target not IP - have to do forward DNS lookup as name given:
            else:
                targetName = str(my_resolver.query(target['target'], "A")[0])
                target['DNS'] = targetName
        except KeyboardInterrupt:
            closeFiles()
            raise SystemExit('Exit: Interrupted by User')    
        except:
            target['DNS'] = 'host not found'    
            
    elif dnsServer == False: #use sockets library to resolve using default system DNS servers:
        try:
            if SILENT == False:
                #print('Resolving {}...'.format(target['target']))
                pass
            #check that target is IP address, if so - do reverse DNS lookup:
            if checkIP(target['target']) == True:
                targetName = gethostbyaddr(target['target'])[0]
                target['DNS'] = targetName
            #if target not IP - have to do forward DNS lookup as name given:
            else:
                targetName = gethostbyname(target['target'])
                target['DNS'] = targetName
        except KeyboardInterrupt:
            closeFiles()
            raise SystemExit('Exit: Interrupted by User')    
        except:
            target['DNS'] = 'host not found'    

def gettargets(targets_data=SrcFile):
    """
    Function to form list of targets with their parameters from SrcFile
    Variables:
        SrcFile - file object with text data in semi-CSV format.
    Returns:
        Updates global targetsList list with targets dictionaries details.
    """
    #get targets list to probe from targets.txt
    global DNS
    global DNSSRV
    global targetsList
    global TARGETS
    
    if TARGETS:
        targetsSource = [i.replace(' ','') for i in TARGETS.split(',')]
    else:
        try:
            with open(targets_data, 'r') as f:
                #readlines to temp list targetsSource:
                targetsSource = f.read().splitlines()
        except FileNotFoundError:
            print('targets.txt file not found.')
            targetsSource = ['8.8.8.8, Google Public DNS', '8.8.4.4, Google Public DNS']
        
    #Iterate over targetsSource lines and extract targets hosts and description:
    for target in targetsSource:
        targetTempDict = copy_copy(targetDict)
        #skip comments:
        if target.startswith('#'):
            continue
            
        #skip empty lines:
        elif target.strip() == '':
            continue
        
        #check if splitChar (deafult char - ',' comma) in target, if so, try to extract additional parameters like IP, description and command:
        elif splitChar in target:
            targetTempDict['target'] = target.split(splitChar)[0].strip()             #get target name/ip
            targetTempDict['Description'] = target.split(splitChar)[1].strip()       #get target description
            try:
                targetTempDict['commandList'] = target.split(splitChar)[2].strip().strip('"').strip("'")                        #get target command
                #FORM Command to run:
                if PING==True:                                                              #if -P given, has to use ping command and override all commnds given in file
                    targetTempDict['commandList'] = copy_copy(defaultCommand)                #assign defaultCommand list to command item
                    targetTempDict['commandList'][hostIndex] = targetTempDict['target']        #set {target} equal to target IP/name
                    targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])    #append command to description
                elif TRACE==True:                                                           #if -T given, has to use traceroute command and override all commnds given in file
                    targetTempDict['commandList'] = copy_copy(defaultCommand)                #assign defaultCommand list to command item
                    targetTempDict['commandList'][hostIndex] = targetTempDict['target']        #set {target} equal to target IP/name
                    targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])    #append command to description
                elif USERCOMMAND != '':                                                     #if -C commnd given, have to use it
                    targetTempDict['commandList'] = copy_copy(defaultCommand)                #assign defaultCommand list to command item
                    targetTempDict['commandList'][hostIndex] = targetTempDict['target']        #set {target} equal to target IP/name
                    targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])    #append command to description                    
                elif targetTempDict['commandList'] != '':                                                                       #check that command is not empty, if not - use it:
                    targetTempDict['commandList'] = targetTempDict['commandList'].replace('{target}', targetTempDict['target']) #replace {target} in command with target IP/name
                    targetTempDict['Command'] = targetTempDict['commandList']                                                    #add Command string to target
                    targetTempDict['commandList'] = targetTempDict['commandList'].split()                                        #split command based on spaces to create list to run it with subprocess
                elif targetTempDict['commandList'] == '':                                                                       #in case if command is empty - use default command:
                    targetTempDict['commandList'] = copy_copy(defaultCommand)                                                    #assign defaultCommand list to command item
                    targetTempDict['commandList'][hostIndex] = targetTempDict['target']                                            #set {target} equal to target IP/name
                    targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])                                        #append command to description                        
            except: #except occurs when no command give in line, hence target.split(splitChar)[2] will produce an error
                targetTempDict['commandList'] = copy_copy(defaultCommand)                #assign defaultCommand list to command item
                targetTempDict['commandList'][hostIndex] = targetTempDict['target']        #set {target} equal to target IP/name
                targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])    #append command to description
                
            if targetTempDict['target'].count('/') == 1:         #if we have / in target - means subnet given
                targetsList += targets_from_subnet(targetTempDict) #extract and add IPs from subnet to targetsList
            else:
                targetsList.append(targetTempDict)

        #else - no splitChar in target line, get target:
        else:
            targetTempDict['target'] = target.strip()                             #get target and clean it from spaces
            targetTempDict['commandList'] = copy_copy(defaultCommand)             #sign probrparms list to command item
            targetTempDict['commandList'][hostIndex] = targetTempDict['target']     # {target} equal to target IP/name
            targetTempDict['Command'] = (' ').join(targetTempDict['commandList'])#append command to description
            if targetTempDict['target'].count('/') == 1:         #if we have / in target - means subnet given
                targetsList += targets_from_subnet(targetTempDict) #extract and add IPs from subnet to targetsList
            else:
                targetsList.append(targetTempDict)
            
    #perform DNS resolution of targets if -D flag given:
    if DNS == True or DNSSRV != False:
        DNSthreads = []
        #start threads to resolve names:
        for target in targetsList:
            DNSth = threading_Thread(target = DNSresolve, kwargs = dict(target=target, dnsServer=DNSSRV))
            try:
                DNSth.start()
                DNSthreads.append(DNSth)
            except KeyboardInterrupt:
                closeFiles()
                raise SystemExit('Exit: Interrupted by User')        
            except:
                pass
                
        #join threads and wait for them to comlete:
        for DNSth in DNSthreads:
            DNSth.join(timeout = 30 * PROBETIMEOUT/1000)
    
    #create formatter for output formatting:
    getFormatter()
    #print all targets for the first time if SILENT mode not True:
    if SILENT==False:
        #clear screen if Windows, and delte 0 lines if Linux:
        delete_last_lines(0)
        #print targets to the screen:
        printer()
    #create log files and fill dictionary of log file name using index to make them unique:
    for index, target in enumerate(targetsList):
        file_name = target['target'].replace("/","_").replace(":", "_")
        target['logFile'] = open(logMainDir + logSubDirName + str(index+1) + '_' + logFileName.format(file_name), 'a', buffering=1)
    
def targets_from_subnet(TD):
    #TD -  target dictionary based on targetDictglob var
    result = []
    if ":" in TD['target']: #create IPv6 subnet object
        subnetObj = ipaddress_IPv6Network(TD['target'], strict=False)
    elif "." in TD['target']: #create IPv4 subnet object:        
        subnetObj = ipaddress_IPv4Network(TD['target'], strict=False)
    subnet_hosts = [str(i) for i in list(subnetObj.hosts())]
    #go over subnet hosts and copy targetDict parameters on them:
    for subnet_host in subnet_hosts:
        result.append({})
        result[-1].update(TD)
        result[-1]['target'] = subnet_host
        result[-1]['Command'] = TD['Command'].replace(TD['target'], subnet_host)
        #have had to do below to prevent subnet_host becoming equal to last hos tin subnet:
        TD['commandList'][hostIndex] = subnet_host
        result[-1]['commandList'] = copy_copy(TD['commandList'])
    return result
    
def getProbeParams():
    """
    create probe parameters list based on OS type, by default if no command given uses ping command, if -T given uses traceroute command,
    if -C command give, then runs probe using this command
    """
    global defaultCommand #reference global defaultCommand variable
    global TRACE
    global hostIndex

    if 'LINUX' in platform_system().upper():
        # -c number of pings, -i interval between pings, -W timeout sec
        if USERCOMMAND == '' and TRACE==False: #default action to run ping command
            defaultCommand = ['ping', '-c', '1', '-W', '{}'.format(PROBETIMEOUT/1000), '{target}'] #last item will be replaced with IP or name
        elif TRACE==True: #if -T given, run traceroute command
            defaultCommand = ['traceroute', '{target}'] #last item will be replaced with IP or name
        else: #means that command been given, hence need to run it
            defaultCommand = [item for item in USERCOMMAND.split(' ') if item != ''] #list comprehension to loop over items and skip empty items
            #check if no {target} position been given on command, hence have to append it to the end:
            if '{target}' not in defaultCommand:
                defaultCommand.append('{target}')
        hostIndex = defaultCommand.index('{target}')
        
    elif 'WINDOWS' in platform_system().upper():
        # -n numer of pings, -w timeout ms
        if USERCOMMAND == '' and TRACE==False:        
            defaultCommand = ['ping', '-n', '1', '-w', str(PROBETIMEOUT), '{target}'] #last item will be replaced with IP or name
        elif TRACE==True: #if -T given, run traceroute command
            defaultCommand = ['tracert', '-d', '-w', str(PROBETIMEOUT), '{target}'] #last item will be replaced with IP or name
        else: #means that command been given, hence need to run it
            defaultCommand = [item for item in USERCOMMAND.split(' ') if item != ''] #list comprehension to loop over items and skip empty items
            #check if no {target} position been given on command, hence have to append it to the end:
            if '{target}' not in defaultCommand:
                defaultCommand.append('{target}')
        hostIndex = defaultCommand.index('{target}')
        
    else:
        raise SystemExit('ERROR: Unsupported OS, nor Windows nor Linux')
    
def runProbe(target):
    #write probe start indicator to log file:
    target['logFile'].write('\n' + 30*'#' + '\n' + 'Time: {}'.format(time.ctime()) + '\n' + 'Command: ' + (' ').join(target['commandList']) + '\n' + 'Output:')
    
    # try:
    #     returnStatus = subprocess_call(target['commandList'], stdout=target['logFile'], stderr=target['logFile'])
    #     if returnStatus == 0:
    #         target['results'] += '!'
    #     else:
    #         target['results'] += '.'
    # except KeyboardInterrupt:
    #     closeFiles()
    #     raise SystemExit('Exit: Interrupted by User')    
    # except:
    #     target['results'] += 'E'
    #     target['logFile'].write(' ERROR: Something went wrong with subprocess calling command: {}\n'.format((' ').join(target['commandList'])))
    
    try:
        result = subprocess.check_output(target['commandList'], stderr=subprocess.STDOUT)
        result = result.decode(encoding="utf-8")
        target['logFile'].write(result)
        if ("Destination net unreachable" in result or 
            "TTL expired in transit" in result or
            "Destination host unreachable" in result
            ):
            target['results'] += '.'
        else:
            target['results'] += '!'
    except subprocess.CalledProcessError as e:
        target['results'] += '.'
        target['logFile'].write(e.output.decode())
    except KeyboardInterrupt:
        closeFiles()
        raise SystemExit('Exit: Interrupted by User')       
    except:
        target['results'] += 'E'
        target['logFile'].write('ERROR: Something went wrong with subprocess calling command: {}\n'.format((' ').join(target['commandList'])))

def startThread(target):
    #run thread with target command:
    th = threading_Thread(target = runProbe, kwargs = dict(target=target))        
    try:
        th.start()
        threads.append(th)
    except KeyboardInterrupt:
        closeFiles()
        raise SystemExit('Exit: Interrupted by User')    

def startThreads(numberOfThreads):
    global targetsList
    global ctime
    global TRACE
    thread_counter = 0
    probesReverseCounter = copy_copy(PROBECOUNT)
    while probesReverseCounter != 0:
        StartTime = time.time() #cycle start time in 1532321174.2756 format
        for target in targetsList:
            thread_counter += 1
            # continue starting threads until maximum numberOfThreads reached
            # and length of targetsList smaller then count of threads already started
            if thread_counter != numberOfThreads and len(targetsList) != thread_counter: 
                startThread(target)
            # wait for threads to complete by joining them
            else:
                startThread(target)
                thread_counter = 0
                try:
                    for th in threads:
                        if TRACE:#if traceroute command then set timeout to 30 x probetimeout
                            th.join(timeout = 30 * PROBETIMEOUT/1000)
                        else:
                            th.join(timeout = 3 * PROBETIMEOUT/1000)
                    if SSILENT == False: 
                        reprinter()
                except KeyboardInterrupt:
                    closeFiles()
                    raise SystemExit('Exit: Interrupted by User')
        # join remaining threads and run reprinter
        try:
            for th in threads:
                if TRACE:#if traceroute command then set timeout to 30 x probetimeout
                    th.join(timeout = 30 * PROBETIMEOUT/1000)
                else:
                    th.join(timeout = 3 * PROBETIMEOUT/1000)
            if SSILENT == False: 
                reprinter()
            else:
                # write final logs for all probes if end reached
                if probesReverseCounter == 1:
                    reprinter()
        except KeyboardInterrupt:
            closeFiles()
            raise SystemExit('Exit: Interrupted by User')

        probesReverseCounter -= 1
        
        #calculate time spent running above threads/probes, if spent les than PROBEINTERVAL than sleep time remaining:
        TimeElapsed = round(time.time() - StartTime, 4)
        if PROBEINTERVAL/1000 > TimeElapsed:
            TimeToSleep = PROBEINTERVAL/1000 - TimeElapsed
            try:
                time.sleep(TimeToSleep)
            except KeyboardInterrupt:
                closeFiles()
                raise SystemExit('Exit: Interrupted by User')
        
def getFormatter():
    global formatter
    global header
    global barLen
    #list of disctionaries, contains column headers to print on screen and their width:
    headersList = [{'Target': 0}, {'Results': 0}, {'Probes': 0}]  
    
    #fill in actual headers width:
    if barLen < 8: barLen = 8 #override barLen value to smallest possible which is lenght of len('Results:'), which is 8
    headersList[1]['Results'] = barLen
    headersList[2]['Probes'] = len(str(PROBECOUNT) + ' / ' + str(PROBECOUNT))
    if headersList[2]['Probes'] < len('Probes:'): #hadne case then len of MAXWidthProbes is smaller then lenght of probes string:
        headersList[2]['Probes'] = len('Probes:')
        
    MAXDNSWidth = 0
    MAXCommandWidth = 0
    MAXDescriptionWidth = 0
    
    #iterate over targets to get longest values for above variables:
    for target in targetsList:
        if len(target['DNS']) > MAXDNSWidth:
            MAXDNSWidth = len(target['DNS'])
        if len(target['Command']) > MAXCommandWidth:
            MAXCommandWidth = len(target['Command'])
        if len(target['Description']) > MAXDescriptionWidth:
            MAXDescriptionWidth = len(target['Description']) 
        if len(target['target']) >  headersList[0]['Target']:
            headersList[0]['Target'] = len(target['target'])
                                                                
    #form headers list to print:
    if MAXDNSWidth != 0:
        headersList.append({'DNS': MAXDNSWidth})
    if MAXCommandWidth != 0:
        headersList.append({'Command': MAXCommandWidth})    
    if MAXDescriptionWidth != 0:
        headersList.append({'Description': MAXDescriptionWidth})    
    
    #form header string:
    header = 'Start: {};  History: {} Probes;  Timeout: {} sec; Default Cmd: {}'.format(ctime, barLen, int(PROBETIMEOUT/1000), 
                                ' '.join(defaultCommand[:hostIndex]) + ' {target} ' + ' '.join(defaultCommand[hostIndex+1:]))  + '\n' + 'RESULTS: "!" - Success; "." - Fail; "E" - Error ' + '\n\n'
                                                                
    for headerItem in headersList: 
        #form named formatter by geting values of first key - width, and key name - header name and assigning it to name and padding:
        formatter += '{{{name}:<{padding}}} | '.format(name=list(headerItem.keys())[0], padding=list(headerItem.values())[0])
        #get string of first key - header name, and format it into header string - first format is adding padding, second format adds header name:
        header += ('{{:<{padding}}} | '.format(padding=list(headerItem.values())[0])).format(list(headerItem.keys())[0] + ':')
    
    #strip right most ' ' and '|'  and ':'characters:
    formatter = formatter.rstrip(' |:')
    header = header.rstrip(' |')

def printer():
    global targetsList
    global barLen
    global PROBECOUNT
    global logSumFileObj
    global header
    global formatter
    
    #print header info:
    if SILENT==False:
        print(header) #print to screen
    print(header, file=logSumFileObj) #print to logfile

    #iterate over targets list and print results:
    for target in targetsList:
        #construct History column value to print:
        if barLen >= len(target['results']):
            HistoryPrintValue = target['results']
        else:
            HistoryPrintValue = target['results'][-barLen:]
        #print to screen:
        if SILENT==False:
            print(formatter.format(
                    Target = target['target'], 
                    Results = HistoryPrintValue, 
                    Probes = str(len(target['results'])) + ' / ' + str(PROBECOUNT), 
                    DNS = target['DNS'],                  #if DNS not in formatter - its will be ignored and not printed
                    Command = target['Command'],          #if Command not in formatter - its will be ignored and not printed
                    Description = target['Description'])) #if Description not in formatter - its will be ignored and not printed
        #print to logfile:
        print(formatter.format(
                Target = target['target'], 
                Results = HistoryPrintValue, 
                Probes = str(len(target['results'])) + ' / ' + str(PROBECOUNT), 
                DNS = target['DNS'],           
                Command = target['Command'], 
                Description = target['Description']), file=logSumFileObj)
                
def delete_last_lines(n):
    if 'LINUX' in platform_system().upper():
        for _ in range(n):
            sys_stdout.write(LINUX_CURSOR_UP_ONE)
            sys_stdout.write(LINUX_ERASE_LINE)
    elif 'WINDOWS' in platform_system().upper():
        os_system('cls')
        
def reprinter():
    global targetsList
    if SILENT==False: #do not clear screen if Silent mode is True:
        delete_last_lines(len(targetsList) + 4)
    printer()
                
def closeFiles():
    global targetsList
    for target in targetsList:
        target['logFile'].close()
    logSumFileObj.close()
    
def get_results_json_report():
    """
    this function takes targetsList and produced report dictionary, where key 
    is set to target and value of key is a list of checks done, so that 
    it can be used for running deepdiff comaprison
    """
    report_dict = list(targetsList)
    ret = {}
    for item in report_dict:
        _, _, _ = item.pop('logFile'), item.pop('hostIndex'), item.pop('commandList')
        target = item.pop('target')
        if not target in ret:
            ret[target] = [item]
        else:
            ret[target].append(item)
    return ret

def save_json_report():
    from json import dumps
    report_dict = get_results_json_report()
    # generate report
    report_data = dumps(report_dict, sort_keys=True, indent=4, separators=(',', ': '))
    report_file_name = logMainDir + logSubDirName + '{}_JSON_Report.txt'.format(ctime.replace(" ", "_").replace(":","-"))
    with open(report_file_name, 'w', buffering=1) as report_file:
        report_file.write(report_data) 

def produce_deepdiff_report():
    try:
        from deepdiff import DeepDiff
    except ImportError:
        print('Failed to import deepdiff library, make sure it is installed')
        return
    from json import loads
    from  pprint import pprint
    # load data before
    data_before = None
    with open(DIFF_SOURCE, 'r') as f:
        data_before = loads(f.read())    
    # get data after:
    data_after = get_results_json_report()
    # run comparison
    result = DeepDiff(data_before, data_after, verbose_level=2)
    pprint(result)

if __name__ == '__main__':   
    getProbeParams()
    gettargets()
    startThreads(numberOfThreads)
    closeFiles()
    if JSON_REPORT:
        save_json_report()
    if DIFF_SOURCE:
        produce_deepdiff_report()
