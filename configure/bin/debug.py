#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.core.management import setup_environ
import settings
setup_environ(settings)

from monitor.models import *
from configure.models import *
from configure.lib.state_manager import StateManager

from collections_24 import defaultdict
import sys

import cmd

class HydraDebug(cmd.Cmd, object):
    def __init__(self):
        super(HydraDebug, self).__init__()
        self.prompt = "Hydra> "

    def do_EOF(self, line):
        raise KeyboardInterrupt()

    def do_load_config(self, config_file):
        from configure.lib.load_config import load_file
        load_file(config_file)

    def do_format_fs(self, fs_name):
        fs = ManagedFilesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            if target.state == 'unformatted':
                StateManager.set_state(target, 'formatted')

    def do_start_fs(self, fs_name):
        fs = ManagedFilesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            StateManager.set_state(target.downcast(), 'mounted')

    def do_stop_fs(self, fs_name):
        fs = ManagedFilesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            if not target.state == 'unmounted':
                StateManager.set_state(target.downcast(), 'unmounted')

    def do_lnet_up(self, args):
        for host in ManagedHost.objects.all():
            StateManager.set_state(host, 'lnet_up')
    def do_lnet_down(self, args):
        for host in ManagedHost.objects.all():
            StateManager.set_state(host, 'lnet_down')

    def do_lnet_unload(self, args):
        for host in ManagedHost.objects.all():
            StateManager.set_state(host, 'lnet_unloaded')

    def do_poke_queue(self, args):
        from configure.models import Job
        Job.run_next()

    def do_apply_conf_params(self, mgs_host_name):
        # Create an ApplyConfParams job for this MGS
        from configure.models import ManagedMgs, ApplyConfParams
        mgs = ManagedMgs.objects.get(targetmount__host__address = mgs_host_name)
        job = ApplyConfParams(mgs = mgs)

        # Submit the job
        from configure.lib.state_manager import StateManager
        StateManager().add_job(job)

    def _conf_param_test_instance(self, key, val, klass):
        if klass == MdtConfParam:
            try:
                mdt = ManagedMdt.objects.latest('id')
                return MdtConfParam(mdt = mdt, key = key, value = val)
            except ManagedMdt.DoesNotExist:
                return None
        elif klass == OstConfParam:
            try:
                ost = ManagedOst.objects.latest('id')
                return OstConfParam(ost = ost, key = key, value = val)
            except ManagedOst.DoesNotExist:
                return None
        elif klass in [FilesystemClientConfParam, FilesystemGlobalConfParam]:
            try:
                fs = ManagedFilesystem.objects.latest('id')
                return klass(filesystem = fs, key = key, value = val)
            except ManagedFilesystem.DoesNotExist:
                return None
        else:
            raise NotImplementedError()
    
    def do_test_conf_param(self, args):
        from configure.lib.conf_param import all_params
        from sys import stderr, stdout
        stdout.write("#!/bin/bash\n")
        stdout.write("set -e\n")
        for p,(param_obj_klass, param_validator, help_text) in all_params.items():
            for test_val in param_validator.test_vals():
                instance = self._conf_param_test_instance(p, test_val, param_obj_klass)
                if not instance:
                    stderr.write("Cannot create test instance for %s\n" % p)
                else:
                    stdout.write("echo lctl conf_param %s=%s\n" % (instance.get_key(), test_val))
                    stdout.write("lctl conf_param %s=%s\n" % (instance.get_key(), test_val))

    def do_create_storage_resource(self, args):
        """Development placeholder for UI for creating
           arbitrary parentless StorageResources e.g. inputting
           IP addresses of controllers"""
        args = args.split()
        plugin, resource = args[0:2]
        kwargs_list = args[2:]
        kwargs = {}
        for k in kwargs_list:
            tokens = k.split('=')
            kwargs[tokens[0]] = tokens[1]
        from configure.lib.storage_plugin import storage_plugin_manager
        storage_plugin_manager.create_root_resource(plugin, resource, **kwargs)

    def do_run_storage_plugin(self, module_name):
        """Development stub for quickly loading and scanning storage
           plugins."""
        from configure.lib.storage_plugin import ResourceQuery, storage_plugin_manager
        from configure.models import StorageResourceRecord
        import time

        klass = storage_plugin_manager.load_plugin(module_name)
        scannable_ids = storage_plugin_manager.get_scannable_resource_ids(module_name)

        if len(scannable_ids) > 1:
            print "Warning, multiple root resources, picking the first one"
        root_resource = ResourceQuery().get_resource(scannable_ids[0]['id'])

        instance = klass()
        instance.do_initial_scan(root_resource)
        while True:
            instance.do_periodic_update(root_resource)
            time.sleep(5)
            
    def do_storage_graph(self, arg_string):
        from configure.lib.storage_plugin import ResourceQuery
        resources = ResourceQuery().get_all_resources()
        import pygraphviz as pgv
        G = pgv.AGraph(directed=True)
        for r in resources:
            G.add_node(r._handle, label="%s:%s" % (r.human_class(), r.human_string()))

        for r in resources:
            for p in r.get_parents():
                G.add_edge(r._handle, p._handle)

        G.layout(prog='dot')
        output_file = 'resources.png'
        G.draw(output_file)
        print "Wrote graph to %s" % output_file

if __name__ == '__main__':
    cmdline = HydraDebug

    if len(sys.argv) == 1:
        try:
            cmdline().cmdloop()
        except KeyboardInterrupt:
            print "Exiting..."
    else:
        cmdline().onecmd(" ".join(sys.argv[1:]))

