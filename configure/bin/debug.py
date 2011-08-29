#!/usr/bin/env python
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
            StateManager.set_state(target.targetmount_set.get(primary = True).downcast(), 'mounted')

    def do_stop_fs(self, fs_name):
        fs = ManagedFilesystem.objects.get(name = fs_name)
        for target in fs.get_targets():
            if not target.state == 'unmounted':
                StateManager.set_state(target.targetmount_set.get(primary = True).downcast(), 'unmounted')

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

    def do_apply_conf_param(self, args):
        from configure.models import ManagedMgs, ApplyConfParams
        job = ApplyConfParams(mgs = ManagedMgs.objects.get())
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

if __name__ == '__main__':
    cmdline = HydraDebug

    if len(sys.argv) == 1:
        try:
            cmdline().cmdloop()
        except KeyboardInterrupt:
            print "Exiting..."
    else:
        cmdline().onecmd(" ".join(sys.argv[1:]))

