#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import ConfigParser
import lockfile
import time
from mailchimp3 import MailChimp


class Subscriber:
    def __init__(self, settings, working_directory, logger=None):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/console'
        self.stderr_path = '/dev/console'
        self.pidfile_path = os.path.join(working_directory, 'subscribe-daemon.pid')
        self.pidfile_timeout = 5

        self.settings = settings
        self.logger = logger
        self.emails_file = os.path.join(working_directory, 'emails.data')

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

    def do_main_program(self):

        def time_passed(oldepoch):
            return time.time() - oldepoch >= 60

        start_time = time.time()
        email_set = set()

        while True:
            # receive all emails from a file and then delete it
            with open(self.emails_file, 'r') as f:
                emails = f.read().splitlines()
            os.remove(self.emails_file)

            # clear from garbage
            emails = [email.strip() for email in emails if email.strip()]

            # add everything to a set
            for email in emails:
                self.log("debug", "received email {0}".format(email))
                email_set.add(email)

            if time_passed(start_time):
                self.log("debug", "starting subscribing emails")
                # retrieve all users in a desired list
                # check if we already have a user with email we trying to add
                members = self.client.member.all(self.list_id)
                for member in members['members']:
                    if member['email_address'] in email_set:
                        email_set.remove(member['email_address'])

                # if we wasn't able to find email then add it to a list
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
            else:
                self.logger.info(message)
