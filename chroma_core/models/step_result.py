# coding=utf-8
# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
from base64 import b64decode

from django.db import models
from django.db.models import CASCADE

from picklefield.fields import PickledObjectField
from tastypie.serializers import Serializer

from iml_common.lib import util
from chroma_core.lib.job import Step

MAX_STATE_STRING = 32


class StepResult(models.Model):
    def __init__(self, *args, **kwargs):
        super(StepResult, self).__init__(*args, **kwargs)
        self.class_name = self.step_klass.__name__
        self.args_json = Serializer().to_json(self.args)
        self.description = self.describe()

    job = models.ForeignKey("Job", on_delete=CASCADE)
    step_klass = PickledObjectField()
    args = PickledObjectField(help_text="Dictionary of arguments to this step")
    class_name = models.CharField(default=b"", max_length=128)
    args_json = models.TextField(default="{}")
    description = models.TextField(default=b"")

    step_index = models.IntegerField(
        help_text="Zero-based index of this step within the steps of\
            a job.  If a step is retried, then two steps can have the same index for the same job."
    )
    step_count = models.IntegerField(help_text="Number of steps in this job")

    log = models.TextField(help_text="Human readable summary of progress during execution.")

    console = models.TextField(
        help_text="Combined standard out and standard error from all\
            subprocesses run while completing this step.  This includes output from successful\
            as well as unsuccessful commands, and may be very verbose."
    )
    backtrace = models.TextField(help_text="Backtrace of an exception, if one occurred")

    # FIXME: we should have a 'cancelled' state for when a step is running while its job is cancelled
    state = models.CharField(max_length=32, default="incomplete", help_text="One of incomplete, failed, success")

    modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    result = models.TextField(null=True, help_text="Arbitrary result data.")

    _step_types = {}

    @property
    def step_class(self):
        """
        PickleFields are a bad idea in this case, the references are to the full Class name such as
        chroma_core.models.host.ConfigureNTPStep so if you move them, or rename them, the
        PickleField fails. To make matters worse debugging the failures is really hard.

        This code below decodes the Picklefield by hand if it fails (we only have 1 case so it's easy) and then
        returns an instance of the class. In a future patch I would suggest the Picklefield is abandoned
        completely.

        The field will be of the form.

        "�cchroma_core.models.host
         ConfigureCorosyncStep
         q."

        We are interested in the middle line.

        This doesn't solve the whole problem, because anything in args could break it, but as of 3.0 it is OK.

        Truthfully the describe string should be created when the step is created and not created dynamically. Something
        for 3.1 maybe.
        """

        # If PickleField succeeds you get a type, otherwise a string.
        if type(self.step_klass) is type:
            return self.step_klass
        else:
            # Very have to build this now, because at module level all the children may not exist yet.
            if self._step_types == {}:
                for step_type in util.all_subclasses(Step):
                    self._step_types[step_type.__name__] = step_type

            return self._step_types[b64decode(self.step_klass).split()[1]]

    def describe(self):
        return self.step_class.describe(self.args)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]
