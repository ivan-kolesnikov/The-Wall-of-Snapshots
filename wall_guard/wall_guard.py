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
import shlex
from enum import Enum
import json
import socket

pid_file = os.path.dirname(os.path.realpath(__file__))+'/guard.pid'
log_file = os.path.dirname(os.path.realpath(__file__))+'/guard.log'
r_m_analyzer_path = os.path.dirname(os.path.realpath(__file__))+'/r_m_analyzer'
default_rest_api_url = "http://127.0.0.1:8585/"
sleep_time = 0
min_bitrate_kbs = 0
analyzers_status_sock = 0
tasks = []
analyzers_responses_raw = []
channels_bitrate = []
channels_bitrate_urgent = []
channels_errors = []


class EnTasksNames(Enum):
    sync_analyzers = 0
    collect_analyzers_statuses = 1
    manage_analyzers_statuses = 2


def create_udp_socket(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.settimeout(0.1)
    except socket.error as error:
        log_guard("Can't create udp socket. Detail: "+str(error))
        return -1
    return sock


def close_udp_socket():
    global analyzers_status_sock
    analyzers_status_sock.close()
    analyzers_status_sock = 0


def recreate_udp_socket():
    log_guard("Trying to recreate udp socket...")
    global analyzers_status_sock
    # get guard config from REST API
    config = get_from_rest_api('guards/'+str(args.guard_id)+'/config/')
    if len(config) == 0:
        log_guard("Can't get guard config at udp socket reconnecting step. Check rest_url and guard_id")
        return -1
    # close broken socket
    close_udp_socket()
    # create udp socket again
    analyzers_status_sock = create_udp_socket(config['ip'], config['port'])
    if analyzers_status_sock == -1:
        log_guard("Can't create udp socket at start")
        return -1
    log_guard("UDP socket recreated")
    return 0


def transform_to_daemon():
    # Daemon class. UNIX double fork mechanism
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as error:
        sys.stderr.write(get_current_time()+'_Fork #1 failed: {0}\n'.format(error))
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
    except OSError as error:
        sys.stderr.write(get_current_time()+'_Fork #2 failed: {0}\n'.format(error))
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
    output_processes_byte, ps_err = subprocess.Popen("ps -fela | grep \'" + application_str_for_ps +
                                                     "' | awk \'{print $4,$1=$2=$3=$4=$5=$6=$7=$8="
                                                     "$9=$10=$11=$12=$13=$14=\"\",$0}\'",
                                                     shell=True, stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE).communicate()
    # if error occurs during ps util execution
    if ps_err != b"":
        return -1
    output_processes_str = output_processes_byte.decode("utf-8")
    # if analyzers processes aren't running
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
            except Exception as error:
                log_guard("Can't parse output from ps utility - return an empty list. Detail: " + str(error))
                return []
    return active_processes


def kill_processes_out_of_api_scope():
    # get channels from REST API
    channels = get_from_rest_api('channels/')
    if len(channels) == 0:
        log_guard("The list of channels from REST API is empty. Can't kill processes out of scope")
        return -1
    # get processes from ps utility
    processes = get_active_processes()
    if processes == -1:
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
            except Exception as error:
                log_guard("The process is out of REST API scope. Could not stop it. pid = " +
                          process['pid']+" command = "+process['command'] + ". By the following reason: "+str(error))
    return 0


def run_r_m_analyzers():
    # get guard config from REST API
    config = get_from_rest_api('guards/'+str(args.guard_id)+'/config/')
    if len(config) == 0:
        log_guard("Can't get config for start r_m_analyzers. Check rest_url and guard_id")
        return -1
    # get channels from REST API
    channels = get_from_rest_api('channels/')
    if len(channels) == 0:
        log_guard("The list of channels from REST API is empty. Can't start r_m_analyzers")
        return -1
    # get processes from ps utility
    processes = get_active_processes()
    if processes == -1:
        log_guard("The list of processes from ps utility is empty. "
                  "We don't have any processes to understand how many new instances are necessary to start.")
        return -1
    # run all necessary r_m_analyzer processes
    for channel in channels:
        channel_id_has_not_found_in_processes_list = 1
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
            r_m_analyzer_run_cmd_str = r_m_analyzer_path + " --address-mcast " + channel_ip + \
                                                           " --port-mcast " + channel_port + \
                                                           " -i " + str(channel['id']) + \
                                                           " --channel-name '" + channel['name'] + \
                                                           "' --address-output " + config['ip'] + \
                                                           " --port-output " + str(config['port'])
            command = shlex.split(r_m_analyzer_run_cmd_str)
            # try to start r_m_analyzer
            try:
                r_m_analyzer_process = subprocess.Popen(command, start_new_session=True,
                                                        stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                r_m_analyzer_pid = r_m_analyzer_process.pid
                log_guard("r_m_analyzer has been started. channel_id=" + str(channel['id']) +
                          " channel_name='" + channel['name'] + "' pid=" + str(r_m_analyzer_pid))
            except Exception as error:
                log_guard("r_m_analyzer hasn't started. channel_id=" + str(channel['id']) +
                          " channel_name='" + channel['name'] + "' Detail: " + str(error))


def get_from_rest_api(rest_request):
    response = []
    # get guard config from REST API
    try:
        response = requests.get(args.rest_url+rest_request).json()
    except Exception as error:
        log_guard("Rest server connection error. Detail: "+str(error))
    return response


def add_task(task_name, priority_time, task_id=-1):
    # no one the same task
    for task in tasks:
        if task_name.name == task['task']:
            if task_id == task['task_id']:
                return -1
    tasks.append(json.loads('{"task_id" : '+str(task_id)+', "task" : "'+task_name.name +
                            '", "priority_time" : '+str(priority_time)+'}'))
    return 0


def task_handler():
    global tasks
    for task in tasks:
        task['priority_time'] -= sleep_time
        # if need to do this task
        if task['priority_time'] < 1:
            # check and kill all unnecessary analyzers
            if task['task'] == EnTasksNames.sync_analyzers.name:
                kill_processes_out_of_api_scope()
                run_r_m_analyzers()
            elif task['task'] == EnTasksNames.collect_analyzers_statuses.name:
                collect_analyzers_statuses()
            elif task['task'] == EnTasksNames.manage_analyzers_statuses.name:
                manage_analyzers_statuses()

    # delete completed tasks
    tasks_count = len(tasks)
    i = 0
    j = 0
    while j < tasks_count:
        if tasks[i]['priority_time'] < 1:
            del tasks[i]
            i -= 1
        i += 1
        j += 1


def collect_analyzers_statuses(max_iterations=7500):
    global analyzers_status_sock
    global analyzers_responses_raw
    while max_iterations:
        try:
            # read response from analyzer with buffer size 1024 bytes
            analyzer_response, _ = analyzers_status_sock.recvfrom(1024)
            if analyzer_response != b"":
                analyzers_responses_raw.append(analyzer_response)
            else:
                log_guard("Response from analyzer is empty!")
            max_iterations -= 1
        # socket don't have any new info
        except socket.timeout:
            break
        except Exception as error:
            log_guard("Read data from udp socket unexpected exception. Detail: "+str(error))
            # recreate udp socket
            recreate_udp_socket()
            break


def manage_analyzers_statuses():
    global analyzers_responses_raw
    # make clean responses from analyzers_responses_raw
    analyzers_responses = []
    # foreach raw response
    for analyzer_responses_raw in analyzers_responses_raw:
        analyzer_response_str = analyzer_responses_raw.decode('utf-8')
        # split each analyzer response by items
        analyzer_response_items = analyzer_response_str.split('#')
        # clean analyzer response
        analyzer_response = {}
        # item it's a dictionary: value_name and value
        for analyzer_response_item in analyzer_response_items:
            # split string by values
            analyzer_response_item_lst = analyzer_response_item.split('|')
            # we expect only 2 items after split
            if len(analyzer_response_item_lst) == 2:
                analyzer_response[analyzer_response_item_lst[0]] = analyzer_response_item_lst[1]
            else:
                log_guard("Parsing response from analyzer error. Parsed string: "+analyzer_response_str)
                analyzer_response = {}
                break
        # if everything is fine with that response
        if len(analyzer_response) != 0:
            # append it to analyzers responses list
            analyzers_responses.append(analyzer_response)

    # managing analyzers statuses
    global channels_bitrate
    global channels_bitrate_urgent
    global channels_errors
    # foreach analyzer response
    for analyzer_response in analyzers_responses:
        # looking for errors in that response
        udp_raises = analyzer_response.get('udp_errors', 0)
        udp_amount = analyzer_response.get('udp_lost_packages', 0)
        cc_raises = analyzer_response.get('cc_errors', 0)
        # if error(s) exist add that response to the channels error list
        if udp_raises or udp_amount or cc_raises:
            channels_errors.append(analyzer_response)

        # foreach existing bitrate
        channel_has_not_found_in_bitrate_list = 1
        for channel_bitrate_index in range(len(channels_bitrate)):
            # if found that channel in the bitrate list
            if analyzer_response['id'] == channels_bitrate[channel_bitrate_index]['id']:
                channel_has_not_found_in_bitrate_list = 0
                # get last bitrate for current channel
                last_bitrate = analyzer_response.get('bitrate', -1)
                # if last bitrate has been good
                if last_bitrate >= min_bitrate_kbs and last_bitrate != -1:
                    # if current bitrate from analyzer also is good
                    if int(analyzer_response['bitrate']) >= min_bitrate_kbs:
                        # update bitrate in the channels_bitrate list
                        channels_bitrate[channel_bitrate_index]['timestamp'] = analyzer_response['timestamp']
                        channels_bitrate[channel_bitrate_index]['bitrate'] = analyzer_response['bitrate']
                    # if current bitrate from analyzer is bad
                    else:
                        # added that response to urgent bitrate list
                        channels_bitrate_urgent.append(analyzer_response)
                        # and update bitrate in channels_bintrate list
                        channels_bitrate[channel_bitrate_index]['timestamp'] = analyzer_response['timestamp']
                        channels_bitrate[channel_bitrate_index]['bitrate'] = analyzer_response['bitrate']
                # if last bitrate hasn't been good
                else:
                    # if current bitrate from analyzer is good
                    if int(analyzer_response['bitrate']) >= min_bitrate_kbs:
                        # added that response to urgent bitrate list
                        channels_bitrate_urgent.append(analyzer_response)
                        # and update bitrate in channels_bitrate list
                        channels_bitrate[channel_bitrate_index]['timestamp'] = analyzer_response['timestamp']
                        channels_bitrate[channel_bitrate_index]['bitrate'] = analyzer_response['bitrate']
                    # if current bitrate from analyzer is still bad
                    else:
                        # update bitrate in the channels_bitrate list
                        channels_bitrate[channel_bitrate_index]['timestamp'] = analyzer_response['timestamp']
                        channels_bitrate[channel_bitrate_index]['bitrate'] = analyzer_response['bitrate']
        # if that channel hasn't found in existing channels_bitrate list
        if channel_has_not_found_in_bitrate_list:
            # add bitrate from that response in the channels_bitrate list
            channels_bitrate.append({'id': analyzer_response['id'], 'timestamp': analyzer_response['timestamp'],
                                     'bitrate': analyzer_response['bitrate']})
    m = 0


def run():
    global analyzers_status_sock
    # get guard config from REST API
    config = get_from_rest_api('guards/'+str(args.guard_id)+'/config/')
    if len(config) == 0:
        log_guard("Can't get guard config at start. Check rest_url and guard_id")
        return -1
    # create udp socket to get data from analyzers
    analyzers_status_sock = create_udp_socket(config['ip'], config['port'])
    if analyzers_status_sock == -1:
        log_guard("Can't create udp socket at start")
        return -1
    # sync processes at guard start
    add_task(EnTasksNames.sync_analyzers, sleep_time)
    while True:
        # collect socket data
        add_task(EnTasksNames.collect_analyzers_statuses, sleep_time)
        # handle read data from socket
        add_task(EnTasksNames.manage_analyzers_statuses, sleep_time)
        task_handler()
        # all necessary tasks have done - sleep
        time.sleep(sleep_time)


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
    except OSError as os_err:
        e = str(os_err.args)
        if e.find("No such process") > 0:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        else:
            print(str(os_err.args))
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
    output, ps_err = subprocess.Popen("ps -ela | grep "+str(pid)+" | grep "+application_name+" | awk \'{print $2}\'",
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
    # get guard config
    guard_config = get_from_rest_api('guards/'+str(args.guard_id)+'/config/')
    if len(guard_config) == 0:
        print('Can not connect to the rest server. Check rest_url and guard_id.')
        sys.exit(1)
    else:
        sleep_time = guard_config['sleep_time']
        min_bitrate_kbs = guard_config['min_bitrate_kbs']

    main()
