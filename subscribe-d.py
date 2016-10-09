#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import logging
from daemon import runner
from subscribe import Subscriber


working_directory = os.path.dirname(os.path.realpath(__file__))
log = 'subscribe-daemon.log'
settings = 'settings.ini'

log_file = os.path.join(working_directory, log)
settings_file = os.path.join(working_directory, settings)

# creating daemon folder
try:
    if not os.path.isdir(working_directory):
        os.mkdir(working_directory)
except (IOError, OSError):
    print("can't create directory {0} for a daemon".format(working_directory))
    exit(1)

# create logger
logger = logging.getLogger("subscribe_daemon")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler(log_file)
handler.setFormatter(formatter)
logger.addHandler(handler)

# creating daemon object
daemon = Subscriber(settings_file, working_directory, logger)

# starting daemon
daemon_runner = runner.DaemonRunner(daemon)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()

