#!/usr/bin/python3.5
# coding: utf-8
import os
import sys
import time
import argparse
import configparser
import signal
import atexit
from datetime import datetime
import subprocess

pid_file = ""
log_file = ""
node_name = ""
sleep_time = 0
default_config_path = os.path.dirname(os.path.realpath(__file__))+'/wall_guard.ini'


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
        # if the guard stopped or need to start the worker in any case
        if real_guard_state == "stopped" or args.force_start:
            # remove the old pid file
            os.remove(pid_file)
        # if the worker process exist
        else:
            print("\033[91m"+"The Wall Guard is already running"+"\033[0m")
            log_guard(get_current_time()+" Trying to start the Wall Guard, but it's already running, pid="+str(pid))
            sys.exit(1)
    # Start the daemon
    transform_to_daemon()
    run()


def run():
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
        log_guard(get_current_time()+" Trying to start the Wall Guard. Pid file does not exist")
        # empty return - no error in case of restart
        return

    # kill the worker
    try:
        # no more than 10 tries to stop the guard
        for _ in range(0, 10):
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
        # can not kill the worker correctly, sleep 5 seconds
        time.sleep(5)
        # check the worker status
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
    # Open the pid_file to get the worker pid
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
    if args.worker_state == 'start':
        start()
    elif args.worker_state == 'stop':
        stop()
    elif args.worker_state == 'restart':
        restart()
    elif args.worker_state == 'status':
        status()
    else:
        parser.print_help()


def get_config():
    config_ini = configparser.ConfigParser(interpolation=None)
    try:
        config_ini.read(args.config_path)
    except Exception as err:
        log_guard(get_current_time()+" Failed to open config file. "+str(err))
        return -1
    return config_ini


def log_guard(message):
    with open(log_file, 'a') as log:
        log.write(message+'\n')


def get_current_time():
    return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Wall Guard application for the Processing Control')
    parser.add_argument('-s', '--guard_state', help='start/stop/restart/status guard', default='start')
    parser.add_argument('-f', '--force_start', help='guard force start flag', default=0, type=int)
    parser.add_argument('-c', '--config_path', help='configuration file path', default=default_config_path)
    args = parser.parse_args()
    # read configuration file
    configuration_file = get_config()
    # can not open database connection without credentials
    if configuration_file == -1:
        print('Can not open configuration file. Check the -c parameter')
        sys.exit(1)
    else:
        pid_file = configuration_file['GUARD']['pid']
        log_file = configuration_file['GUARD']['log']
        sleep_time = int(configuration_file['GUARD']['sleep_time_seconds'])

    main()
