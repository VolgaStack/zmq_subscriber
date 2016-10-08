#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import ConfigParser
import zmq
import lockfile
import time
from mailchimp3 import MailChimp


class Subscriber:
    def __init__(self, settings, working_directory, logger=None):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = os.path.join(working_directory, 'subscribe_daemon.pid')
        self.pidfile_timeout = 5

        self.settings = settings
        self.logger = logger

        lockfile.FileLock(self.pidfile_path)

    def run(self):
        self.initial_program_setup()
        self.do_main_program

    def initial_program_setup(self):

        config = ConfigParser.ConfigParser()
        config.read(self.settings)

        self.log("debug", "read settings file")

        # setting up MailChimpClient
        self.list_id = config.get('MAILCHIMP', 'list_id')
        client_login = config.get('MAILCHIMP', 'client_login')
        client_apikey = config.get('MAILCHIMP', 'client_apikey')

        self.client = MailChimp(client_login, client_apikey)

        self.log("debug", "created mail chimp client")

        # setting up zmq
        port = config.get('ZEROMQ', 'port')

        socket_context = zmq.Context()

        self.socket = socket_context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:{0}".format(port))

        self.socket.setsockopt_string(zmq.SUBSCRIBE, 'SUB'.decode('ascii'))
        self.socket.setsockopt(zmq.RCVTIMEO, 1000)

        self.log("debug", "socket created and subscribed on port {0}".format(port))

    def do_main_program(self):

        def hour_passed(oldepoch):
            return time.time() - oldepoch >= 3600

        start_time = time.time()
        email_set = set()
        # TODO: механизм сохранения емейлов при выходе из функции, механизм загрузки при входе

        while True:
            # receive email from a zmq socket
            try:
                email = self.socket.recv_string()
                email = email.split('$')[1]
                email_set.add(email)

                self.log("debug", "received email {0}".format(email))
            except zmq.error.Again:
                pass

            if hour_passed(start_time):
                self.log("debug", "starting subscribing emails")
                # retrieve all users in a desired list
                # check if we already have a user with email we trying to add
                members = self.client.member.all(self.list_id)
                for member in members['members']:
                    if member['email_address'] in email_set:
                        email_set.remove(member['email_address'])

                # if we wasn't able to find email then add it to a list
                # TODO: fix fname, lname
                for email in email_set:
                    self.client.member.create(self.list_id, {
                        'email_address': email,
                        'status': 'subscribed',
                        'merge_fields': {
                            'FNAME': '',
                            'LNAME': '',
                        },
                    })

                # since we just run lets upgrade start_time variable
                # and set email_set to empty
                start_time = time.time()
                email_set = set()

    def log(self, level, message):
        if self.logger is not None:
            if level == "debug":
                self.logger.debug(message)
            elif level == "info":
                self.logger.info(message)
