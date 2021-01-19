# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from django.core.management.base import BaseCommand
from chroma_core.lib.storage_plugin.query import ResourceQuery
from chroma_core.models import StorageResourceRecord


class Command(BaseCommand):
    help = """For debugging, dump a graph view of all storage resources."""

    def execute(self, *args, **kwargs):
        try:
            import pygraphviz as pgv
        except ImportError:
            print("This command requires pygraphviz")
            return

        if len(args) == 0:
            resources = ResourceQuery().get_all_resources()
        else:
            resources = []

            def iterate(record):
                res = record.to_resource()
                resources.append(res)
                for p in record.parents.all():
                    p_res = iterate(p)
                    res._parents.append(p_res)
                return res

            start_id = int(args[0])
            start_record = StorageResourceRecord.objects.get(pk=start_id)
            iterate(start_record)
        G = pgv.AGraph(directed=True)
        for r in resources:
            G.add_node(r._handle, label="%s:%s:%s" % (r._handle, r._meta.label, r.get_label()))

        for r in resources:
            for p in r.get_parents():
                G.add_edge(r._handle, p._handle)

        G.layout(prog="dot")
        output_file = "resources.png"
        G.draw(output_file)
        print("Wrote graph to %s" % output_file)
