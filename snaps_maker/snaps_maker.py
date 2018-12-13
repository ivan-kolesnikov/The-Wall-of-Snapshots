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


def get_cpu_usage():
    try:
        cpu_usage = int(psutil.cpu_percent(interval=1))
    except Exception as err:
        log_sm(get_current_time() + " Could not get the cpu usage. By the following reason: " + str(err))
        return 0
    return cpu_usage


def get_free_video_memory():
    output, ps_err = subprocess.Popen("nvidia-smi --query-gpu=memory.free --format=csv,noheader | awk \'{print $1}\'",
                                      shell=True, stdout=subprocess.PIPE).communicate()
    # if error occurs during ps util execution
    if ps_err != b"":
        return -1
    free_video_memory = output.decode("utf-8")
    return free_video_memory


def log_sm(message):
    with open(log_file, 'a') as log:
        log.write(get_current_time()+' '+message+'\n')


def get_current_time():
    return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


def main():
    cpu = get_cpu_usage()
    video_mem = get_free_video_memory()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Snaps Maker application for creating collections of snapshots')
    parser.add_argument('-r', '--rest_url', help='REST API url', default=default_rest_api_url)
    parser.add_argument('-f', '--ffmpeg_path', help='Path to FFmpeg', default=default_ffmpeg_path)
    parser.add_argument('-s', '--snaps_folder', help='Path to Snaps', default=default_path_to_snaps)
    parser.add_argument('-t', '--desired_time', help='Desired time to take snapshots for all channels',
                        type=int, default=60)
    parser.add_argument('-c', '--max_cpu_usage', help='Max CPU usage. Do not exceed that value to take snapshot',
                        type=int, default=70)
    args = parser.parse_args()
    main()
