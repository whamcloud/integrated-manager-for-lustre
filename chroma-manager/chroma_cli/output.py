#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import tablib
from chroma_cli.exceptions import AbnormalCommandCompletion


class StandardFormatter(object):
    @classmethod
    def formats(cls):
        return ["human"] + [f.title for f in tablib.formats.available]

    def __init__(self, format="human", nowait=False, command_monitor=None):
        if not format in self.__class__.formats():
            raise RuntimeError("%s not in %s" %
                               (format, self.__class__.formats()))
        self.format = format
        self.nowait = nowait
        self.command_monitor = command_monitor

    def __call__(self, input):
        try:
            if isinstance(input, dict):
                self.command(input)
            elif isinstance(input, list):
                self.list(input)
            else:
                self.show(input)
        except AttributeError:
            print input

    def show(self, entity):
        self.list([entity])

    def list(self, entities):
        if self.format == "json":
            from tablib.packages import omnijson as json
            print json.dumps([e.all_attributes for e in entities])
        elif self.format == "yaml":
            from tablib.packages import yaml
            print yaml.safe_dump([e.all_attributes for e in entities])
        else:
            try:
                header = entities[0].as_header()
                rows = []
                for entity in entities:
                    rows.append(entity.as_row())

                if self.format == "human":
                    from prettytable import PrettyTable, NONE
                    table = PrettyTable(header, hrules=NONE)
                    for row in rows:
                        table.add_row(row)
                    print table
                else:
                    data = tablib.Dataset(*rows, headers=header)
                    format = getattr(data, self.format)
                    print format
            except IndexError:
                print "Found 0 results"

    def command(self, command):
        try:
            if 'command' in command.keys():
                command = command['command']
        except AttributeError:
            print command
            return

        if self.nowait:
            print command['message']
        else:
            import sys
            monitor = self.command_monitor(command)
            last_len = 0
            while not monitor.completed:
                jobs = monitor.incomplete_jobs
                if len(jobs) > 0:
                    line = "\r%s, waiting on jobs: %s" % (command['message'], jobs)
                else:
                    line = "\r%s, waiting ..." % command['message']

                if len(line) < last_len:
                    sys.stderr.write("\r" + " " * last_len)
                sys.stderr.write(line)
                last_len = len(line)

                monitor.update()
            print "\r" + " " * last_len,
            print "\r%s: %s" % (command['message'], monitor.status)
            if monitor.status != "Finished":
                raise AbnormalCommandCompletion(command, monitor.status)
