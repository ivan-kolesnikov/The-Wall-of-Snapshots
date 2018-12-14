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
import psutil

default_rest_api_url = "http://127.0.0.1:8585/"
default_ffmpeg_path = "/usr/bin/ffmpeg"
default_path_to_snaps = os.path.dirname(os.path.realpath(__file__))+'/Snaps'
log_file = os.path.dirname(os.path.realpath(__file__))+'/snaps_maker.log'


def get_cpu_usage(interval_sec):
    try:
        cpu_usage = int(psutil.cpu_percent(interval=interval_sec))
    except Exception as err:
        log_sm(get_current_time() + " Could not get the cpu usage. By the following reason: " + str(err))
        return 0
    return cpu_usage


def get_free_video_memory():
    output, ps_err = subprocess.Popen("nvidia-smi --query-gpu=memory.free --format=csv,noheader | awk \'{print $1}\'",
                                      shell=True, stdout=subprocess.PIPE).communicate()
    # if error occurs during nvidia-smi execution
    if ps_err != b"":
        return -1
    free_video_memory = output.decode("utf-8")
    return free_video_memory


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


def take_snapshot(channel, on_gpu):
    if on_gpu:
        command = "-i "+channel['']


def main():
    while True:
        # get all channels from the rest server
        channels = get_from_rest_api('channels/')
        # if channels list is empty
        if not channels:
            log_sm("Channels list is empty")
            time.sleep(1)
            continue

        channels_len = len(channels)
        i = 0
        while i < channels_len:
            # get and update CPU each 5th iteration
            if not (i % 5):
                cpu_usage = get_cpu_usage(0.1)
            # get free video memory
            free_video_memory = get_free_video_memory()
            # if enough video memory
            if free_video_memory >= 100:
                # take snapshot on GPU
                take_snapshot(channels[i], 1)
            # if CPU performance hasn't exceeded
            elif cpu_usage < args.max_cpu_usage:
                # take snapshot on CPU
                take_snapshot(channels[i], 0)
            else:
                # get and update CPU usage during 1 second
                cpu_usage = get_cpu_usage(1)
                # try to take a snapshot for that channel again
                continue
            i += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Snaps Maker application for creating collections of snapshots')
    parser.add_argument('-r', '--rest_url', help='REST API url', default=default_rest_api_url)
    parser.add_argument('-f', '--ffmpeg_path', help='Path to FFmpeg', default=default_ffmpeg_path)
    parser.add_argument('-s', '--snaps_folder', help='Path to Snaps', default=default_path_to_snaps)
    parser.add_argument('-t', '--desired_time', help='Desired time to take snapshots for all channels',
                        type=int, default=60)
    parser.add_argument('-c', '--max_cpu_usage', help='Max CPU usage. Do not exceed that value to take snapshot',
                        type=int, default=30)
    args = parser.parse_args()
    # test connection to the REST server
    test_response = get_from_rest_api('channels/')
    if not test_response:
        print("Can't connect to the REST server")
        sys.exit(1)

    main()
