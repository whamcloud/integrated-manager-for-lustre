#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


from chroma_core.lib.cache import ObjectCache
from chroma_core.services import log_register
from chroma_core.services.job_scheduler.lock_cache import LockCache
from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
from django.contrib.contenttypes.models import ContentType
from django.db.models import DateTimeField


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
               'create_host',
               'create_targets',
               'available_transitions',
               'available_jobs'
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

        difference = False
        for attr, value in update_attrs.items():
            old_value = getattr(instance, attr)
            if old_value != value:
                difference = True

        if ((not from_states) or instance.state in from_states) and difference:
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
        from chroma_core.models import ManagedHost, Command

        host_id, command_id = JobSchedulerRpc().create_host_ssh(address, server_profile, root_pw, pkey, pkey_pw)
        return ManagedHost.objects.get(pk=host_id), Command.objects.get(pk=command_id)

    @classmethod
    def test_host_contact(cls, address, root_pw=None, pkey=None, pkey_pw=None):
        return JobSchedulerRpc().test_host_contact(
            address, root_pw, pkey, pkey_pw)

    @classmethod
    def create_filesystem(cls, fs_data):
        return JobSchedulerRpc().create_filesystem(fs_data)

    @classmethod
    def create_host(cls, fqdn, nodename, address, server_profile_id):
        from chroma_core.models import ManagedHost, Command
        # The address of a host isn't something we can learn from it (the
        # address is specifically how the host is to be reached from the manager
        # for outbound connections, not just its FQDN).  If during creation we know
        # the address, then great, accept it.  Else default to FQDN, it's a reasonable guess.
        if address is None:
            address = fqdn

        host_id, command_id = JobSchedulerRpc().create_host(fqdn, nodename, address, server_profile_id)

        return ManagedHost.objects.get(pk = host_id), Command.objects.get(pk = command_id)

    @classmethod
    def create_targets(cls, targets_data):
        from chroma_core.models import ManagedTarget, Command

        target_ids, command_id = JobSchedulerRpc().create_targets(targets_data)
        return list(ManagedTarget.objects.filter(id__in=target_ids)), Command.objects.get(pk = command_id)
