#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import tablib


class StandardFormatter(object):
    @classmethod
    def formats(cls):
        return ["human"] + [f.title for f in tablib.formats.available]

    def __init__(self, format="human"):
        if not format in self.__class__.formats():
            raise RuntimeError("%s not in %s" %
                               (format, self.__class__.formats()))
        self.format = format

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
            print command['command']['message']
        except KeyError:
            print command['message']


class FollowFormatter(StandardFormatter):
    def command(self, command):
        pass
