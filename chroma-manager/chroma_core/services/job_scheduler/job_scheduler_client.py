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


"""
The service `job_scheduler` handles both RPCs (JobSchedulerRpc) and a queue (NotificationQueue).
The RPCs are used for explicit requests to modify the system or run a particular task, while the queue
is used for updates received from agent reports.  Access to both of these, along with some additional
non-remote functionality is wrapped in JobSchedulerClient.

"""
import datetime

from django.contrib.contenttypes.models import ContentType
from django.db.models import DateTimeField

from chroma_core.lib.cache import ObjectCache
from chroma_core.services import log_register
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
from chroma_core.models import ManagedHost, Command


log = log_register(__name__)


class NotificationQueue(ServiceQueue):
    name = 'job_scheduler_notifications'


class JobSchedulerRpc(ServiceRpcInterface):
    methods = ['set_state',
               'run_jobs',
               'cancel_job',
               'create_host_ssh',
               'test_host_contact',
               'create_filesystem',
               'create_client_mount',
               'create_copytool',
               'register_copytool',
               'unregister_copytool',
               'update_nids',
               'update_lnet_configuration',
               'create_host',
               'set_host_profile',
               'create_targets',
               'available_transitions',
               'available_jobs',
               'get_locks'
               ]


class JobSchedulerClient(object):
    """Because there are some tasks which are the domain of the job scheduler but do not need to
    be run in the context of the service, the RPCs and queue operations are accompanied in this
    class by some operations that run locally.  The local operations are
    read-only operations such as querying what operations are possible for a particular object.

    """
    @classmethod
    def command_run_jobs(cls, job_dicts, message):
        """Create and run some Jobs, within a single Command.

        :param job_dicts: List of 1 or more dicts like {'class_name': 'MyJobClass', 'args': {<dict of arguments to Job constructor>}}
        :param message: User-visible string describing the operation, e.g. "Detecting filesystems"
        :return: The ID of a new Command

        """
        return JobSchedulerRpc().run_jobs(job_dicts, message)

    @classmethod
    def command_set_state(cls, object_ids, message, run = True):
        """Modify the system in whatever way is necessary to reach the state
        specified in `object_ids`.  Creates Jobs under a single Command.  May create
        no Jobs if the system is already in the state, or already scheduled to be
        in that state.  If the system is already scheduled to be in that state, then
        the returned Command will be connected to the existing Jobs which take the system to
        the desired state.

        :param cls:
        :param object_ids: List of three-tuples (natural_key, object_id, new_state)
        :param message: User-visible string describing the operation, e.g. "Starting filesystem X"
        :param run: Test only.  Schedule jobs without starting them.
        :return: The ID of a new Command

        """
        return JobSchedulerRpc().set_state(object_ids, message, run)

    @classmethod
    def notify(cls, instance, time, update_attrs, from_states = []):
        """Having detected that the state of an object in the database does not
        match information from real life (i.e. chroma-agent), call this to
        request an update to the object.

        :param instance: An instance of a StatefulObject
        :param time: A UTC datetime.datetime object
        :param update_attrs: Dict of attribute name to json-serializable value of the changed attributes
        :param from_states: (Optional) A list of states from which the instance may be
                            set to the new state.  This lets updates happen
                            safely without risking e.g. notifying an 'unconfigured'
                            LNet state to 'lnet_down'.  If this is ommitted, the notification
                            will be applied irrespective of the object's state.

        :return: None

        """

        if (not from_states) or instance.state in from_states:
            log.info("Enqueuing notify %s at %s:" % (instance, time))
            for attr, value in update_attrs.items():
                log.info("  .%s %s->%s" % (attr, getattr(instance, attr), value))

            # Encode datetimes
            encoded_attrs = {}
            for attr, value in update_attrs.items():
                try:
                    field = [f for f in instance._meta.fields if f.name == attr][0]
                except IndexError:
                    # e.g. _id names, they can't be datetimes so pass through
                    encoded_attrs[attr] = value
                else:
                    if isinstance(field, DateTimeField):
                        assert isinstance(value, datetime.datetime), "Attribute %s of %s must be datetime" % (attr, instance.__class__)
                        encoded_attrs[attr] = value.isoformat()
                    else:
                        encoded_attrs[attr] = value

            time_serialized = time.isoformat()
            NotificationQueue().put({
                'instance_natural_key': ContentType.objects.get_for_model(instance).natural_key(),
                'instance_id': instance.id,
                'time': time_serialized,
                'update_attrs': encoded_attrs,
                'from_states': from_states
            })

    @classmethod
    def available_transitions(cls, object_list):
        """Return the transitions available for each object in list

        See the Job Scheduler method of the same name for details.
        """

        return JobSchedulerRpc().available_transitions(object_list)

    @classmethod
    def available_jobs(cls, object_list):
        """Query which jobs (other than changes to state) can be run on this object.

        See the Job Scheduler method of the same name for details.
        """

        return JobSchedulerRpc().available_jobs(object_list)

    @classmethod
    def get_transition_consequences(cls, stateful_object, new_state):
        """Query what the side effects of a state transition are.  Effectively does
        a dry run of scheduling jobs for the transition.

        The return format is like this:
        ::

            {
                'transition_job': <job dict>,
                'dependency_jobs': [<list of job dicts>]
            }
            # where each job dict is like
            {
                'class': '<job class name>',
                'requires_confirmation': <boolean, whether to prompt for confirmation>,
                'confirmation_prompt': <string, confirmation prompt>,
                'description': <string, description of the job>,
                'stateful_object_id': <ID of the object modified by this job>,
                'stateful_object_content_type_id': <Content type ID of the object modified by this job>
            }

        :param stateful_object: A StatefulObject instance
        :param new_state: Hypothetical new value of the 'state' attribute

        """
        from chroma_core.services.job_scheduler.command_plan import CommandPlan

        # FIXME: deps calls use a global instance of ObjectCache, calling them from outside
        # the JobScheduler service is a problem -- get rid of the singletons and pass refs around.
        ObjectCache.clear()
        return CommandPlan(LockCache(), None).get_transition_consequences(stateful_object, new_state)

    @classmethod
    def cancel_job(cls, job_id):
        """Attempt to cancel a job which is already scheduled (and possibly running)

        :param job_id: ID of a Job object
        """
        JobSchedulerRpc().cancel_job(job_id)

    @classmethod
    def create_host_ssh(cls, address, server_profile, root_pw=None, pkey=None, pkey_pw=None):
        """
        Create a host which will be set up using SSH

        :param address: SSH address
        :return: (<ManagedHost instance>, <Command instance>)
        """
        host_id, command_id = JobSchedulerRpc().create_host_ssh(address, server_profile, root_pw, pkey, pkey_pw)
        return ManagedHost.objects.get(pk=host_id), Command.objects.get(pk=command_id)

    @classmethod
    def test_host_contact(cls, address, root_pw=None, pkey=None, pkey_pw=None):
        command_id = JobSchedulerRpc().test_host_contact(address, root_pw, pkey, pkey_pw)

        return Command.objects.get(pk = command_id)

    @classmethod
    def create_filesystem(cls, fs_data):
        return JobSchedulerRpc().create_filesystem(fs_data)

    @classmethod
    def update_nids(cls, nid_data):
        return JobSchedulerRpc().update_nids(nid_data)

    @classmethod
    def update_lnet_configuration(cls, lnet_configuration_list):
        return JobSchedulerRpc().update_lnet_configuration(lnet_configuration_list)

    @classmethod
    def create_host(cls, fqdn, nodename, address, server_profile_id):
        # The address of a host isn't something we can learn from it (the
        # address is specifically how the host is to be reached from the manager
        # for outbound connections, not just its FQDN).  If during creation we know
        # the address, then great, accept it.  Else default to FQDN, it's a reasonable guess.
        if address is None:
            address = fqdn

        host_id, command_id = JobSchedulerRpc().create_host(fqdn, nodename, address, server_profile_id)

        return ManagedHost.objects.get(pk = host_id), Command.objects.get(pk = command_id)

    @classmethod
    def set_host_profile(cls, host_id, server_profile_id):
        '''
        Set the profile for the given host to the given profile, this includes updating the manager view
        and making the appropriate changes to the host.
        :param host_id:
        :param server_profile_id:
        :return: Command for the host job.
        '''
        command_id = JobSchedulerRpc().set_host_profile(host_id, server_profile_id)

        return Command.objects.filter(pk = command_id) if command_id else None

    @classmethod
    def create_targets(cls, targets_data):
        from chroma_core.models import ManagedTarget, Command

        target_ids, command_id = JobSchedulerRpc().create_targets(targets_data)
        return list(ManagedTarget.objects.filter(id__in=target_ids)), Command.objects.get(pk = command_id)

    @classmethod
    def create_client_mount(cls, host, filesystem, mountpoint):
        from chroma_core.models import LustreClientMount

        client_mount_id = JobSchedulerRpc().create_client_mount(host.id,
                                                                filesystem.id,
                                                                mountpoint)
        return LustreClientMount.objects.get(id = client_mount_id)

    @classmethod
    def create_copytool(cls, copytool_data):
        from chroma_core.models import Copytool

        copytool_id = JobSchedulerRpc().create_copytool(copytool_data)
        return Copytool.objects.get(id = copytool_id)

    @classmethod
    def register_copytool(cls, copytool_id, uuid):
        JobSchedulerRpc().register_copytool(copytool_id, uuid)

    @classmethod
    def unregister_copytool(cls, copytool_id):
        JobSchedulerRpc().unregister_copytool(copytool_id)

    @classmethod
    def get_locks(cls, obj_key, obj_id):
        return JobSchedulerRpc().get_locks(obj_key, obj_id)
