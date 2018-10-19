#!/usr/bin/python3.5
# coding: utf-8
import os
import sys
import time
import argparse
import signal
import atexit
from datetime import datetime
import subprocess
import requests
import re

pid_file = os.path.dirname(os.path.realpath(__file__))+'/guard.pid'
log_file = os.path.dirname(os.path.realpath(__file__))+'/guard.log'
r_m_analyzer_path = os.path.dirname(os.path.realpath(__file__))+'/r_m_analyzer'
default_rest_api_url = "http://127.0.0.1:8585/"
sleep_time = 0


def transform_to_daemon():
    # Daemon class. UNIX double fork mechanism
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as err:
        sys.stderr.write(get_current_time()+'_Fork #1 failed: {0}\n'.format(err))
        sys.exit(1)
    # decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as err:
        sys.stderr.write(get_current_time()+'_Fork #2 failed: {0}\n'.format(err))
        sys.exit(1)
    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    # when application stopped correctly
    atexit.register(del_pid)
    pid = str(os.getpid())
    with open(pid_file, 'a+') as f:
        f.write(pid + '\n')


def del_pid():
    os.remove(pid_file)


def start():
    # Open the pid_file to check is guard running
    try:
        with open(pid_file, 'r') as pf:
            pid = int(pf.read().strip())
    except IOError:
        pid = None
    # pid file has been found
    if pid is not None:
        # get the real guard status only by pid
        real_guard_state = get_process_state(pid, str(pid))
        # if the guard stopped or need to start the guard in any case
        if real_guard_state == "stopped" or args.force_start:
            # remove the old pid file
            os.remove(pid_file)
        # if the guard process exist
        else:
            print("\033[91m"+"The Wall Guard is already running"+"\033[0m")
            log_guard("Trying to start the Wall Guard, but it's already running, pid="+str(pid))
            sys.exit(1)
    # Start the daemon
    # transform_to_daemon()
    run()


def get_active_processes():
    active_processes = []
    application_str_for_ps = "[r]_m_analyzer"
    output_processes_byte, err = subprocess.Popen("ps -fela | grep \'" + application_str_for_ps +
                                                  "' | awk \'{print $4,$1=$2=$3=$4=$5=$6=$7=$8="
                                                  "$9=$10=$11=$12=$13=$14=\"\",$0}\'",
                                                  shell=True, stdout=subprocess.PIPE).communicate()
    output_processes_str = output_processes_byte.decode("utf-8")
    # if no one running process for this application
    if output_processes_str != "":
        output_processes = output_processes_str.rstrip().split("\n")
        for output_process in output_processes:
            try:
                # 15 spaces between pid and command in the output_process !!!EXTRA ATTENTION 15 or 16 spaces
                output_process_info = output_process.split("               ")
                if " --channel-id " in output_process_info[1]:
                    re_pattern = "--channel-id\s\d*"
                else:
                    re_pattern = "-i\s\d*"
                channel_id_from_ps = re.findall(re_pattern, output_process_info[1])
                if len(channel_id_from_ps) != 0:
                    channel_id_lst = channel_id_from_ps[0].split(" ")
                    channel_id = channel_id_lst[1]
                else:
                    channel_id = -1
                # append the result list
                active_processes.append({"pid": int(output_process_info[0]),
                                         "command": output_process_info[1], "id": int(channel_id)})
            # return an empty processes list in case of parsing error
            except Exception as err:
                log_guard("Can't parse output from ps utility - return an empty list.")
                return []
    return active_processes


def kill_processes_out_of_api_scope():
    # get channels from REST API
    try:
        channels = requests.get(args.rest_url+'channels/').json()
    except Exception as err:
        log_guard('Can not get channels from rest server. Detail: '+str(err))
    if len(channels) == 0:
        print('The list of channels from REST API is empty')
        return -1
    # get processes from ps utility
    processes = get_active_processes()
    if len(processes) == 0:
        log_guard("The list of processes from ps utility is empty. "
                  "We don't have any processes to check and kill then.")
        return -1
    for process in processes:
        channel_id_has_not_found_in_api = 1
        for channel in channels:
            if process['id'] == channel['id']:
                channel_id_has_not_found_in_api = 0
                break
        if channel_id_has_not_found_in_api:
            try:
                os.kill(process['pid'], signal.SIGKILL)
            except Exception as err:
                log_guard("The process is out of REST API scope. Could not stop it. pid = " +
                          process['pid']+" command = "+process['command'] + ". By the following reason: "+str(err))
    return 0


def run_r_m_analyzers():
    # get guard config from REST API
    try:
        config = requests.get(args.rest_url+'guards/'+str(args.guard_id)+'/config/').json()
    except Exception as err:
        log_guard('Rest server connection error. Detail: '+str(err))
        config = []
    if len(config) == 0:
        print('Can not connect to the rest server. Check rest_url and guard_id.')
        return -1
    # get channels from REST API
    try:
        channels = requests.get(args.rest_url+'channels/').json()
    except Exception as err:
        log_guard('Can not get channels from rest server. Detail: '+str(err))
    if len(channels) == 0:
        print('The list of channels from REST API is empty')
        return -1
    # get processes from ps utility
    processes = get_active_processes()
    if len(processes) == 0:
        log_guard("The list of processes from ps utility is empty. "
                  "We don't have any processes to understand how many new instances are necessary to start.")
        return -1

    for channel in channels:
        channel_id_has_not_found_in_processes_list= 1
        for process in processes:
            if channel['id'] == process['id']:
                channel_id_has_not_found_in_processes_list = 0
                break
        if channel_id_has_not_found_in_processes_list:
            # try to run process
            channel_ip_port = channel['multicast'].split(":")
            # magic number 2 to skip '//' in multicast address
            channel_ip = channel_ip_port[1][2:]
            channel_port = channel_ip_port[2]

            r_m_analyzer_run_cmd_str = r_m_analyzer_path+" --address-mcast "+channel['']






    cc = "./r_m_analyzer --address-mcast 235.1.10.2 --port-mcast 10000 -i 110 --channel-name 'rossiya1' -A 127.0.0.1 -P 8787"




def run():
    kill_processes_out_of_api_scope()
    g = 0
    # task for start necessary and stop unnecessary channels


    #r = requests.post("http://127.0.0.1:8585/channels/", json=[{'id': '125247', 'name': 'test_e', 'multicast': 'rtp://rrrr', 'number_default': 44}, {'id': '125246', 'name': 'test_e', 'multicast': 'rtp://rrrr', 'number_default': 44}])
    #r = requests.put("http://127.0.0.1:8585/channels/125245/", data={'id': 125245, 'name': 'test_e', 'multicast': 'rtp://ttttttttt', 'number_default': 44})
    r = requests.delete("http://127.0.0.1:8585/channels/125244/")
    print(r.status_code, r.reason)
    print(r.text[:300] + '...')
    # fields = ['id', 'name', 'multicast', 'number_default']
    i = 0


def stop():
    # check pid
    try:
        with open(pid_file, 'r') as pf:
            pid = int(pf.read().strip())
    except IOError:
        pid = None
    if not pid:
        print("\033[91m"+"Pid file does not exist. The Wall Guard is not running"+"\033[0m")
        log_guard("Trying to start the Wall Guard. Pid file does not exist")
        # empty return - no error in case of restart
        return

    # kill the guard
    try:
        # no more than 10 tries to stop the guard
        for _ in range(0, 10):
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
        # can not kill the guard correctly, sleep 5 seconds
        time.sleep(5)
        # check the guard status
        real_guard_state = get_process_state(pid, str(pid))
        # if the guard still running
        if real_guard_state != 'stopped':
            print("\033[91m" + "Can't stop the Wall Guard correctly" + "\033[0m")
            sys.exit(1)
    except OSError as err:
        e = str(err.args)
        if e.find("No such process") > 0:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        else:
            print(str(err.args))
            sys.exit(1)


def restart():
    stop()
    start()


def status():
    # Open the pid_file to get the guard pid
    try:
        with open(pid_file, 'r') as pf:
            pid = int(pf.read().strip())
    except IOError:
        pid = None

    # pid file did not found, print info in the console
    if pid is None:
        print("The Wall Guard "+"\033[91m"+"stopped"+"\033[0m"+" (pid file didn't found)")
    # check the process state
    else:
        # get the real guard status only by pid
        real_guard_state = get_process_state(pid, str(pid))
        if real_guard_state == 'active':
            print("The Wall Guard is " + "\033[92m" + "running" + "\033[0m" + " pid="+str(pid))
        elif real_guard_state == 'stopped':
            print("The Wall Guard " + "\033[91m" + "stopped" +
                  "\033[0m" + " (the process with pid "+str(pid)+" doesn't exist)")
        else:
            print("The Wall Guard state is unknown need to manually check the process, pid="+str(pid))
    sys.exit(0)


def get_process_state(pid, command):
    # get the application name from the command
    application_name = command.split(' ', 1)[0]
    output, err = subprocess.Popen("ps -ela | grep "+str(pid)+" | grep "+application_name+" | awk \'{print $2}\'",
                                   shell=True, stdout=subprocess.PIPE).communicate()
    state = output.decode('utf-8')
    # in case of the several output results -> choose the first one
    if len(state) > 1:
        state = state[0]
    if state == "S":
        return "active"
    elif state == "T":
        return "paused"
    elif state == "":
        return "stopped"
    else:
        return "unsupported"


def main():
    if args.guard_state == 'start':
        start()
    elif args.guard_state == 'stop':
        stop()
    elif args.guard_state == 'restart':
        restart()
    elif args.guard_state == 'status':
        status()
    else:
        parser.print_help()


def log_guard(message):
    with open(log_file, 'a') as log:
        log.write(get_current_time()+' '+message+'\n')


def get_current_time():
    return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Wall Guard application for the Processing Control')
    parser.add_argument('-s', '--guard_state', help='start/stop/restart/status guard', default='start')
    parser.add_argument('-f', '--force_start', help='guard force start flag', default=0, type=int)
    parser.add_argument('-r', '--rest_url', help='REST API url', default=default_rest_api_url)
    parser.add_argument('-i', '--guard_id', help='guard id', default=1, type=int)
    args = parser.parse_args()
    try:
        # get all channels from API
        guard_config = requests.get(args.rest_url+'guards/'+str(args.guard_id)+'/config/').json()
    except Exception as err:
        print(str(err))
        guard_config = []
    if len(guard_config) == 0:
        print('Can not connect to the rest server. Check rest_url and guard_id.')
        sys.exit(1)
    else:
        sleep_time = guard_config['sleep_time']

    main()
