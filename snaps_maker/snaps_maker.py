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
import psutil

default_rest_api_url = "http://10.0.255.125:8585/"
default_ffmpeg_path = "ffmpeg"
default_path_to_snaps = os.path.dirname(os.path.realpath(__file__))+'/Snaps'
log_file = os.path.dirname(os.path.realpath(__file__))+'/snaps_maker.log'
pid_file = os.path.dirname(os.path.realpath(__file__))+'/snaps_maker.pid'


def get_cpu_usage(interval_sec):
    try:
        cpu_usage = int(psutil.cpu_percent(interval=interval_sec))
    except Exception as err:
        log_sm(get_current_time() + " Could not get the cpu usage. By the following reason: " + str(err))
        return 0
    return cpu_usage


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
    pid = str(os.getpid())
    # write pid to file
    with open(pid_file, 'w') as f:
        f.write(pid + '\n')


def get_from_rest_api(rest_request):
    response = []
    # get guard config from REST API
    try:
        response = requests.get(args.rest_url+rest_request).json()
    except Exception as error:
        log_sm("Rest server connection error. Detail: "+str(error))
    return response


def log_sm(message):
    with open(log_file, 'a') as log:
        log.write(get_current_time()+' '+message+'\n')


def get_current_time():
    return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


def take_snapshot(channel):
    # remove the previous snapshot
    try:
        os.remove(args.snaps_folder_dir+"/"+str(channel['id'])+".jpg")
    except Exception as err:
        log_sm("Can not remove the old snapshot. Reason: "+str(err))
    # get an input source
    try:
        udpxy_ip = "0.0.0.0"
        udpxy_port = "5556"
        multicast = re.findall("([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+)", channel['multicast'])[0]
        input_address = "http://"+udpxy_ip+":"+udpxy_port+"/rtp/"+multicast
    except Exception as err:
        log_sm("Can not cut the multicast address. "+str(err))
        return -1

    command = args.ffmpeg_path+" -i "+input_address+" -s 120x70 -vframes 1 " + \
                               args.snaps_folder_dir+"/"+str(channel['id'])+".jpg"
    command = "timeout -s 9 10 " +command
    command = shlex.split(command)
    try:
        ffmpeg_proc = subprocess.Popen(command, start_new_session=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except Exception as err:
        ffmpeg_proc.kill()
        log_sm("Can't start the ffmpeg process to take a snapshot. "+str(err))


def main():
    #transform_to_daemon()
    while True:
        # get all channels from the rest server
        channels = get_from_rest_api('channels/')
        # if channels list is empty
        if not channels:
            log_sm("Channels list is empty")
            time.sleep(1)
            continue

        channels_len = len(channels)
        cpu_usage = 0
        i = 0
        start_epoch = int(datetime.now().timestamp())
        print("start "+str(start_epoch))
        while i < channels_len:
            print(str(cpu_usage))
            # get and update CPU each 5th iteration
            if not (i % 3):
                cpu_usage = get_cpu_usage(0.1)
            # if CPU performance hasn't exceeded
            if cpu_usage < args.max_cpu_usage:
                # take snapshot on CPU
                take_snapshot(channels[i])
            else:
                # get and update CPU usage during 1 second
                cpu_usage = get_cpu_usage(1)
                # try to take a snapshot for that channel again
                continue
            i += 1
        end_epoch = int(datetime.now().timestamp())
        print("end " + str(end_epoch))
        delta_epoch = end_epoch-start_epoch
        print("delta " + str(delta_epoch)+"\n")
        time.sleep(12)
        break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Snaps Maker application for creating collections of snapshots')
    parser.add_argument('-r', '--rest_url', help='REST API url', default=default_rest_api_url)
    parser.add_argument('-p', '--ffmpeg_path', help='Path to FFmpeg', default=default_ffmpeg_path)
    parser.add_argument('-d', '--snaps_folder_dir', help='Path to Snaps', default=default_path_to_snaps)
    parser.add_argument('-c', '--max_cpu_usage', help='Max CPU usage. Do not exceed that value to take snapshot',
                        type=int, default=30)
    args = parser.parse_args()
    # test connection to the REST server
    test_response = get_from_rest_api('channels/')
    if not test_response:
        print("Can't connect to the REST server")
        sys.exit(1)

    main()
