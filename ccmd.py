"""
Script uses OS utility to run command against devices. Version 1.
"""

import platform
import subprocess
import os
import time
import copy
import threading
import sys
import argparse

LINUX_CURSOR_UP_ONE = '\x1b[1A'
LINUX_ERASE_LINE = '\x1b[2K' 

probeParamsList=[]                  #list to contain probe command string depending on OS type
ctime = time.ctime()                #get current time to form names of log files
threads=[]                          #list to contain all started threads
devices = []                        #list of devices to run command against
printList=[]                        #list of dictionaries to store command result for printing, key = device
logMainDir = "./LOGS/"              #main LOG directory
logFilesDict = {}                   #dictionary key - address/name of device, value - file object to store logs
logSumFileName = '{}_SumLOGG.txt'   #name of summary log file to store terminal output
logFileName = '{}_LOG.txt'          #name of log file for each device

#build argparser based menu:
parser = argparse.ArgumentParser(description='Concurrent Command to Multiple Destinations')
parser.add_argument('-c', action='store', dest='PROBECOUNT', default=100, type=int, help='Number of probes to run. Default 100.')
parser.add_argument('-b', action='store', dest='barLen', default=60, type=int, help='Length of probe history bar, Default 60.')
parser.add_argument('-i', action='store', dest='PROBEINTERVAL', default=1000, type=int, help='Interval between probes in ms. Default 1000ms.')
parser.add_argument('-w', action='store', dest='PROBETIMEOUT', default=1000, type=int, help='Probe timout interval in ms. Default 1000ms.')
parser.add_argument('-t', action='store', dest='numberOfThreads', default=80, type=int, help='Number of simulteneous probe threads. Default 80.')
parser.add_argument('-p', action='store', dest='logSubDirPrefix', default='TEST', type=str, help='Prefix used to form log sub directory name')
parser.add_argument('-C', action='store', dest='COMMAND', default='', type=str, help='Command to run. Default - ping.')
parser.add_argument('-s', action='store', dest='SrcFile', default='./devices.txt', type=str, help='Location of file with IP/Names. Default - ./devices.txt')
parser.add_argument('-T', action='store_true', dest='TRACE', default=False, help='If -T present run traceroute')

args = parser.parse_args()

PROBECOUNT=args.PROBECOUNT             #number of probes to send
barLen=args.barLen                     #len of probes history bar
PROBEINTERVAL=args.PROBEINTERVAL       #interval between probes in ms
PROBETIMEOUT=args.PROBETIMEOUT         #probe timout interval in ms
numberOfThreads=args.numberOfThreads   #counter to regulate the number of simulteneous probe threads
logSubDirPrefix=args.logSubDirPrefix   #prefix used to form log sub directory name
COMMAND=args.COMMAND                   #command to run, Default - ping
SrcFile=args.SrcFile                   #file name and location with devices' names or IPs
TRACE=args.TRACE                       #if TRACE==True, run traceroute, means form traceroute command and set thread timeout to 30 seconds

#check logic:
if COMMAND != '' and TRACE==True:
	raise SystemExit('Cannot simelteniously run traceroute and "{}"'.format(COMMAND))

#form logs subdirectory name:
logSubDirName = logSubDirPrefix + '_' + ctime.replace(" ", "_").replace(":","-") +'/'  #string to form log sub directory name using current time

#create header information string:
header = 'Start: {};  History: {} Probes;  Timeout: {} sec;'.format(ctime, barLen, int(PROBETIMEOUT/1000)) #header string to print on the screen

def chmkdir(path):
	#check if directory exists if not, make it:
	if not os.path.exists(path): 
		os.mkdir(path)

#create main LOGS directory, create it if not exists:		
chmkdir(logMainDir)
chmkdir(logMainDir + logSubDirName)

#create summary logs file:
logSumFileObj = open(logMainDir + logSubDirName + logSumFileName.format(ctime.replace(" ", "_").replace(":","-")), 'a', buffering=1)


def getDevices(devices_data=SrcFile):
	#get devices list to probe from devices.txt
	global devices
	global printList
	global logFileName
	with open(devices_data, 'r') as f:
		devices = f.read().splitlines()
		#skip line tht starts with # sign and strip all spaces:
		devices = [device.strip() for device in devices if not device.startswith('#')]
	#form list of dictionaries to store probe results:
	printList=[{device:''} for device in devices]
	#print all devices for the first time:
	printer(printList)
	#create log files and fill dictionary of log files:
	for device in devices:
		logFilesDict[device] = open(logMainDir + logSubDirName + logFileName.format(device), 'a', buffering=1)
			
def getProbeParams():
	"""
	create probe parameters list based on OS type, by default if no command given uses ping command, if -T given uses traceroute command,
	if -C command give, then runs probe using this command
	"""
	global probeParamsList #reference global probeParamsList variable
	global TRACE
	if 'LINUX' in platform.system().upper():
		# -c number of pings, -i interval between pings, -W timeout sec
		if COMMAND == '' and TRACE==False: #default action to run ping command
			probeParamsList = ['ping', '-c', '1', '-W', '{}'.format(PROBETIMEOUT/1000), 'host to probe'] #last item will be replaced with IP or name
		elif TRACE==True: #if -T given, run traceroute command
			probeParamsList = ['traceroute', 'host to probe'] #last item will be replaced with IP or name
		else: #means that command been given, hence need to run it
			probeParamsList = COMMAND.split(' ')
			probeParamsList.append('host to probe')
	elif 'WINDOWS' in platform.system().upper():
		# -n numer of pings, -w timeout ms
		if COMMAND == '' and TRACE==False:		
			probeParamsList = ['ping', '-n', '1', '-w', str(PROBETIMEOUT), 'host to probe'] #last item will be replaced with IP or name
		elif TRACE==True:
			probeParamsList = ['tracert', '-d', '-w', str(PROBETIMEOUT), 'host to probe'] #last item will be replaced with IP or name
		else:
			probeParamsList = COMMAND.split(' ')
			probeParamsList.append('host to probe')
	else:
		raise SystemExit('Unsupported OS, nor Windows nor Linux')
	
def runProbe(probeParamsList, logFileObj, devices, printList):
	device=probeParamsList[-1]
	logFileObj.write(30*'#' + '\n' + 'Time: {}'.format(time.ctime()) + '\n' + 'Command: ' + (' ').join(probeParamsList) + '\n' + 'Output:')
	try:
		returnStatus = subprocess.call(probeParamsList, stdout=logFileObj, stderr=logFileObj)
		if returnStatus == 0:
			printList[devices.index(device)][device] += '!'
		else:
			printList[devices.index(device)][device] += '.'
	except KeyboardInterrupt:
		closeFiles()
		raise SystemExit('Exit: Interrupted by User')	

def startThread(device):
	global devices
	global printList
	global logSubDirName
	probeParamsList[-1] = device
	#runProbe:
	th = threading.Thread(target = runProbe, args = (copy.copy(probeParamsList), logFilesDict[device], devices, printList))
	try:
		th.start()
		threads.append(th)
	except KeyboardInterrupt:
		closeFiles()
		raise SystemExit('Exit: Interrupted by User')		

def startThreads(devices, numberOfThreads):
	thread_counter = 0
	global ctime
	global TRACE
	probesReverseCounter = copy.copy(PROBECOUNT)
	while probesReverseCounter != 0:
		StartTime = time.time() #cycle start time in 1532321174.2756 format
		joined=False
		for device in devices:
			thread_counter += 1
			if thread_counter != numberOfThreads: 
				startThread(device)
			else:
				startThread(device)
				thread_counter = 0
				try:
					for th in threads:
						if TRACE:#if traceroute command then set timeout to 30 x probetimeout
							th.join(timeout = 30 * PROBETIMEOUT/1000)
							joined=True						
						else:
							th.join(timeout = 3 * PROBETIMEOUT/1000)
							joined=True
					reprinter(printList)
				except KeyboardInterrupt:
					closeFiles()
					raise SystemExit('Exit: Interrupted by User')
					
		if joined == False:
			try:
				for th in threads:
					if TRACE:#if traceroute command then set timeout to 30 x probetimeout
						th.join(timeout = 30 * PROBETIMEOUT/1000)
					else:
						th.join(timeout = 3 * PROBETIMEOUT/1000)
				reprinter(printList)
			except KeyboardInterrupt:
				closeFiles()
				raise SystemExit('Exit: Interrupted by User')
			
		probesReverseCounter -= 1
		
		#calculate time spent running above threads/probes, if spent less than PROBEINTERVAL than slip time remaining:
		TimeElapsed = round(time.time() - StartTime, 4)
		if PROBEINTERVAL/1000 > TimeElapsed:
			TimeToSleep = PROBEINTERVAL/1000 - TimeElapsed
			try:
				time.sleep(TimeToSleep)
			except KeyboardInterrupt:
				closeFiles()
				raise SystemExit('Exit: Interrupted by User')

def delete_last_lines(n):
	if 'LINUX' in platform.system().upper():
		for _ in range(n):
			sys.stdout.write(LINUX_CURSOR_UP_ONE)
			sys.stdout.write(LINUX_ERASE_LINE)
	elif 'WINDOWS' in platform.system().upper():
		os.system('cls')

def printer(printList):
	global barLen
	global PROBECOUNT
	global header
	global logSumFileObj
	print(header)
	print(header, file=logSumFileObj)
	for i in printList:
		for k,v in i.items():
			if barLen >= len(v):
				print('{:<16}| {}'.format(k,v) + ' ' * (barLen - len(v)) + ' | ' + 'Probes: {} / {}'.format(len(v), PROBECOUNT))
				print('{:<16}| {}'.format(k,v) + ' ' * (barLen - len(v)) + ' | ' + 'Probes: {} / {}'.format(len(v), PROBECOUNT), file=logSumFileObj)
			else:
				printValue = v[-barLen:]
				print('{:<16}| {}'.format(k,printValue) + ' ' * (barLen - len(printValue)) + ' | ' + 'Probes: {} / {}'.format(len(v), PROBECOUNT))
				print('{:<16}| {}'.format(k,printValue) + ' ' * (barLen - len(printValue)) + ' | ' + 'Probes: {} / {}'.format(len(v), PROBECOUNT), file=logSumFileObj)
		
def reprinter(printList):
	delete_last_lines(len(printList) + 1)
	printer(printList)
				
def closeFiles():
	global logFilesDict
	for key, file in  logFilesDict.items():
		file.close()
	logSumFileObj.close()

if __name__ == '__main__':	
	getProbeParams()
	getDevices()
	startThreads(devices, numberOfThreads)
	closeFiles()
