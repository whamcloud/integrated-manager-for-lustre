# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import tablib
from chroma_cli.exceptions import AbnormalCommandCompletion


class StandardFormatter(object):
    @classmethod
    def formats(cls):
        return ["human"] + [f.title for f in tablib.formats.available]

    def __init__(self, format="human", nowait=False, command_monitor=None):
        if not format in self.__class__.formats():
            raise RuntimeError("%s not in %s" % (format, self.__class__.formats()))
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
            print(input)

    def show(self, entity):
        self.list([entity])

    def list(self, entities):
        if self.format == "json":
            from tablib.packages import omnijson as json

            print(json.dumps([e.all_attributes for e in entities]))
        elif self.format == "yaml":
            from tablib.packages import yaml

            print(yaml.safe_dump([e.all_attributes for e in entities]))
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
                    print(table)
                else:
                    data = tablib.Dataset(*rows, headers=header)
                    format = getattr(data, self.format)
                    print(format)
            except IndexError:
                print("Found 0 results")

    def command(self, command):
        try:
            if "command" in command.keys():
                command = command["command"]
        except AttributeError:
            print(command)
            return

        if self.nowait:
            print(command["message"])
        else:
            import sys

            monitor = self.command_monitor(command)
            last_len = 0
            while not monitor.completed:
                jobs = monitor.incomplete_jobs
                if len(jobs) > 0:
                    line = "\r%s, waiting on jobs: %s" % (command["message"], jobs)
                else:
                    line = "\r%s, waiting ..." % command["message"]

                if len(line) < last_len:
                    sys.stderr.write("\r" + " " * last_len)
                sys.stderr.write(line)
                last_len = len(line)

                monitor.update()
            print("\r" + " " * last_len)
            print("\r%s: %s" % (command["message"], monitor.status))
            if monitor.status != "Finished":
                raise AbnormalCommandCompletion(command, monitor.status)
