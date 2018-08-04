# CCMD - Concurrent Command to Multiple Destinations
Tool to run command against multiple destinations (IP or Domain Name) and display results in nice format. 

## Example Usage
Issue ping command for multiple hosts in devices.txt file in parralel and display results.

C:\>python3 ccmd.py
<img src="winExample.jpg">

Warning: for Windows script runs clear screen (cls) to print new results to terminal.

By default detailed logs saved into ./LOG/{ctime}/ directory

### Run Options
'-c' Int. Number of probes to run. Default 100.

'-b' Int. Length of probe history bar. Default 60.

'-i' Int. Minimum interval between probes in ms. Default 1000ms. Previous probe must finish prior for next probe to be sent.  
'-w' Int. Probe timout interval in ms. Default 1000ms. For ping and traceroute used as timout value.  
'-t' Int. Number of simulteneous probes (threads) to run. Default 80.  
'-p' String. Prefix used to form log sub directory name.  
'-C' Command to run. Default - ping.  
'-s' Location of source file with IP/Names. Default - ./devices.txt'.  
'-T' If present, run traceroute command instead of ping.  

## Python Version.
Only Python 3.x supported

## Supported OS.
So far tested on Windows 7,10 and Linux CentOS only.
