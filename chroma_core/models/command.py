# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import traceback
import logging

from django.db import models
from django.contrib.contenttypes.models import ContentType

from chroma_core.lib.job import job_log
from chroma_core.services.rpc import RpcError
from chroma_core.models.alert import AlertState
from chroma_core.models.alert import AlertStateBase
from chroma_core.models.jobs import SchedulingError


class CommandRunningAlert(AlertStateBase):
    default_severity = logging.INFO

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Command %s running" % self.alert_item.message

    @property
    def require_mail_alert(self):
        """
        We do not want to email somebody every time a command is run, it will really annoy them!
        :return: False
        """
        return False


class CommandSuccessfulAlert(AlertStateBase):
    default_severity = logging.INFO

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Command %s successful" % self.alert_item.message

    @property
    def require_mail_alert(self):
        """
        We do not want to email somebody every time a command is successful, it will really annoy them!
        :return: False
        """
        return False


class CommandCancelledAlert(AlertStateBase):
    default_severity = logging.ERROR

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Command %s cancelled" % self.alert_item.message


class CommandErroredAlert(AlertStateBase):
    default_severity = logging.ERROR

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "Command %s failed" % self.alert_item.message


class Command(models.Model):
    command_alert_types = [CommandRunningAlert, CommandSuccessfulAlert, CommandCancelledAlert, CommandErroredAlert]

    jobs = models.ManyToManyField("Job")

    complete = models.BooleanField(
        default=False,
        help_text="True if all jobs have completed, or no jobs were needed to \
                     satisfy the command",
    )
    errored = models.BooleanField(
        default=False,
        help_text="True if one or more of the command's jobs failed, or if \
        there was an error scheduling jobs for this command",
    )
    cancelled = models.BooleanField(
        default=False,
        help_text="True if one or more of the command's jobs completed\
            with its cancelled attribute set to True, or if this command\
            was cancelled by the user",
    )
    message = models.CharField(
        max_length=512,
        help_text="Human readable string about one sentence long describing\
            the action being done by the command",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        The 'force_insert' and 'force_update' parameters can be used to insist
        that the "save" must be an SQL insert or update (or equivalent for
        non-SQL backends), respectively. Normally, they should not be set.

        Once the command is saved we can then create the alert, we need it to be saved or it has no id.

        :param force_insert: bool
        :param force_update: bool
        :param using: str
        """
        super(Command, self).save(force_insert, force_update, using, update_fields)

        # This is a little bit messy and maybe shouldn't go here. We want to get the existing alert, if it exists
        # which could be of a number of types. CommandRunningAlert, CommandSuccessfulAlert, CommandCancelledAlert
        # or CommandErroredAlert so fetch those filter and be sure we have 1 or 0 alerts.
        try:
            potential_command_alerts = AlertState.objects.filter(
                alert_item_id=self.id, alert_item_type=ContentType.objects.get_for_model(self)
            )
            # We should have tests for the case of more than one and if we find more than 1 then lets not make the users life a misery but take the first one.
            command_alert = next(
                potential_command_alert
                for potential_command_alert in potential_command_alerts
                if type(potential_command_alert) in self.command_alert_types
            )
        except StopIteration:
            command_alert = CommandRunningAlert.notify(self, True)

        # Now change to the correct alert type.
        if not self.complete:
            if type(command_alert) != CommandRunningAlert:
                command_alert.cast(CommandRunningAlert)
        else:
            if self.errored:
                if type(command_alert) != CommandErroredAlert:
                    command_alert = command_alert.cast(CommandErroredAlert)
            elif self.cancelled:
                if type(command_alert) != CommandCancelledAlert:
                    command_alert = command_alert.cast(CommandCancelledAlert)
            else:
                if type(command_alert) != CommandSuccessfulAlert:
                    command_alert = command_alert.cast(CommandSuccessfulAlert)

            command_alert.__class__.notify(self, False)

    @classmethod
    def set_state(cls, objects, message=None, **kwargs):
        """The states argument must be a collection of 2-tuples
        of (<StatefulObject instance>, state)"""

        # If you ever work on this function please talk to Chris. It should not be in this class. It has nothing to
        # do with the Command class other than it makes use of a Command and should be moved to the Stateful object
        # class because think about it can only operate on stateful objects.

        from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient

        for object, state in objects:
            # Check if the state is modified
            if object.state != state:
                if not message:
                    old_state = object.state
                    new_state = state
                    route = object.get_route(old_state, new_state)
                    from chroma_core.services.job_scheduler.command_plan import Transition

                    job = Transition(object, route[-2], route[-1]).to_job()
                    message = job.description()

                object_ids = [
                    (ContentType.objects.get_for_model(object).natural_key(), object.id, state)
                    for object, state in objects
                ]
                try:
                    command_id = JobSchedulerClient.command_set_state(object_ids, message, **kwargs)
                except RpcError as e:
                    job_log.error("Failed to set object state: " + traceback.format_exc())
                    # FIXME: Would be better to have a generalized mechanism
                    # for reconstituting remote exceptions, as this sort of thing
                    # won't scale.
                    if e.remote_exception_type == "SchedulingError":
                        raise SchedulingError(e.description)
                    else:
                        raise

                return Command.objects.get(pk=command_id)

        return None

    def completed(self, errored, cancelled):
        """
        Called when the command completes, sets the appropriate completion more of a notification than something requiring any action.
        :param errored: bool True if the command contains an error job.
        :param cancelled: bool True if the command was cancelled because of for example a failed job, or user cancelled...
        cancelled: Boolean indicating if the command contains a job that was cancelled (ie. the command was cancelled)
        """
        self.errored = errored
        self.cancelled = cancelled
        self.complete = True
        self.save()

    def __repr__(self):
        return "<Command %s: '%s'>" % (self.id, self.message)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]
