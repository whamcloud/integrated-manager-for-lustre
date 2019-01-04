# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging

import settings
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_delete
from south.signals import post_migrate
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.template.defaultfilters import pluralize
from django.utils.timezone import now as tznow

from iml_common.lib.util import platform_info
from chroma_core.models.alert import AlertStateBase
from chroma_core.models.event import AlertEvent
from chroma_core.models.host import ManagedHost
from chroma_core.models.jobs import Job, AdvertisedJob, job_log
from chroma_core.models.utils import DeletableMetaclass
from chroma_core.services.job_scheduler import job_scheduler_notify
from chroma_help.help import help_text

from chroma_core.lib.job import Step


class DeletablePowerControlModel(models.Model):
    __metaclass__ = DeletableMetaclass

    class Meta:
        abstract = True
        app_label = "chroma_core"

    # Stick this here so we can use it with both device and outlet classes
    def validate_inet_address(self, address):
        # Guard against accidental input of single-digit "addresses" which
        # apparently gethostbyname will take anyhow. This is an unlikely
        # problem, but could happen if a BMC identifier field is confused
        # for a regular PDU identifier field (i.e. an outlet number).
        try:
            if int(address):
                raise ValidationError("%s is not a valid address for a BMC" % address)
        except ValueError:
            pass

        import socket

        try:
            return socket.gethostbyname(address)
        except socket.gaierror as e:
            raise ValidationError("Unable to resolve %s: %s" % (address, e))


class PowerControlType(DeletablePowerControlModel):
    agent = models.CharField(
        null=False,
        blank=False,
        max_length=255,
        choices=[(a, a) for a in settings.SUPPORTED_FENCE_AGENTS],
        help_text="Fencing agent (e.g. fence_apc, fence_ipmilan, etc.)",
    )
    make = models.CharField(null=True, blank=True, max_length=50, help_text="Device manufacturer string")
    model = models.CharField(null=True, blank=True, max_length=50, help_text="Device model string")
    max_outlets = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text="The maximum number of outlets which may be associated with an instance of this device type (0 is unlimited)",
    )
    default_port = models.PositiveIntegerField(
        default=23, blank=True, help_text="Network port used to access power control device"
    )
    default_username = models.CharField(null=True, blank=True, max_length=128, help_text="Factory-set admin username")
    default_password = models.CharField(null=True, blank=True, max_length=128, help_text="Factory-set admin password")
    default_options = models.CharField(
        null=True, blank=True, max_length=255, help_text="Default set of options to be passed when invoking fence agent"
    )
    # These defaults have been verified with fence_apc, but should work with
    # most fence agents. Some adjustments may be required (e.g. fence_xvm
    # wants -H <domain> rather than -n).
    poweron_template = models.CharField(
        blank=True,
        max_length=512,
        help_text="Command template for switching an outlet on",
        default="%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o on -n %(identifier)s",
    )
    powercycle_template = models.CharField(
        blank=True,
        max_length=512,
        help_text="Command template for cycling an outlet",
        default="%(agent)s %(options)s  -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o reboot -n %(identifier)s",
    )
    poweroff_template = models.CharField(
        blank=True,
        max_length=512,
        help_text="Command template for switching an outlet off",
        default="%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o off -n %(identifier)s",
    )
    monitor_template = models.CharField(
        blank=True,
        max_length=512,
        help_text="Command template for checking that a PDU is responding",
        default="%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o monitor",
    )
    outlet_query_template = models.CharField(
        blank=True,
        max_length=512,
        help_text="Command template for querying an individual outlet's state",
        default="%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o status -n %(identifier)s",
    )
    outlet_list_template = models.CharField(
        null=True,
        blank=True,
        max_length=512,
        help_text="Command template for listing all outlets on a PDU",
        default="%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o %(list_parameter)s",
    )

    def display_name(self):
        make = self.make if self.make != "" else "Unknown Make"
        model = self.model if self.model != "" else "Unknown Model"
        count = "(%s outlet%s)" % (self.max_outlets, pluralize(self.max_outlets)) if self.max_outlets > 0 else ""
        return ("%s %s %s" % (make, model, count)).strip()

    def __str__(self):
        return self.display_name()

    class Meta:
        app_label = "chroma_core"
        unique_together = ("agent", "make", "model")


def create_default_power_types(app, **kwargs):
    if app != "chroma_core":
        return

    import os
    import json
    import chroma_core

    chroma_core = os.path.abspath(os.path.dirname(chroma_core.__file__))

    with open(os.path.join(chroma_core, "fixtures/default_power_types.json")) as f:
        default_types = json.load(f)

    for power_type in default_types:
        try:
            PowerControlType.objects.get(agent=power_type["agent"], make=power_type["make"], model=power_type["model"])
        except PowerControlType.DoesNotExist:
            PowerControlType.objects.create(**power_type)

    print("Loaded %d default power device types." % len(default_types))


post_migrate.connect(create_default_power_types)


@receiver(pre_delete, sender=PowerControlType)
def delete_power_control_units(sender, instance, **kwargs):
    [d.mark_deleted() for d in instance.instances.all()]


class PowerControlDeviceUnavailableAlert(AlertStateBase):
    # This is WARNING because if a power control device is out
    # of touch it may be behaving in an undefined way, therefore
    # may be unable to participate in a failover operation, resulting
    # in a reduced level of filesystem availability.
    default_severity = logging.WARNING

    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    def alert_message(self):
        return "Unable to monitor power control device %s" % self.alert_item

    def end_event(self):
        return AlertEvent(
            message_str="Monitoring resumed for power control device %s" % self.alert_item,
            alert_item=self.alert_item,
            alert=self,
            severity=logging.INFO,
        )


class IpmiBmcUnavailableAlert(AlertStateBase):
    # This is WARNING because if a power control device is out
    # of touch it may be behaving in an undefined way, therefore
    # may be unable to participate in a failover operation, resulting
    # in a reduced level of filesystem availability.
    default_severity = logging.WARNING

    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    def alert_message(self):
        return "Unable to monitor BMC %s on server %s" % (self.alert_item, self.alert_item.host)

    def end_event(self):
        return AlertEvent(
            message_str="Monitoring resumed for BMC %s on server %s" % (self.alert_item, self.alert_item.host),
            alert_item=self.alert_item.host,
            alert=self,
            severity=logging.INFO,
        )


class PowerControlDevice(DeletablePowerControlModel):
    device_type = models.ForeignKey("PowerControlType", related_name="instances")
    name = models.CharField(
        null=False, blank=True, max_length=50, help_text="Optional human-friendly display name (defaults to address)"
    )
    # We need to work with a stable IP address, not a hostname. STONITH must
    # work even if DNS doesn't!
    address = models.IPAddressField(null=False, blank=False, help_text="IP address of power control device")
    port = models.PositiveIntegerField(
        default=23, blank=True, help_text="Network port used to access power control device"
    )
    username = models.CharField(null=False, blank=True, max_length=64, help_text="Username for device administration")
    # FIXME: (HYD-1913) Don't store these passwords in plaintext!
    password = models.CharField(null=False, blank=True, max_length=64, help_text="Password for device administration")
    options = models.CharField(
        null=True, blank=True, max_length=255, help_text="Custom options to be passed when invoking fence agent"
    )

    def __str__(self):
        return self.name

    class Meta:
        app_label = "chroma_core"
        unique_together = ("address", "port")

    def clean(self):
        # Allow the device_type to set defaults for unsupplied fields.
        type_defaults = ["username", "password", "options", "port"]
        for default in type_defaults:
            if getattr(self, default) in ["", None]:
                setattr(self, default, getattr(self.device_type, "default_%s" % default))

        if self.address in ["", None]:
            raise ValidationError("Address may not be blank")

        self.address = self.validate_inet_address(self.address)

        if self.name in ["", None]:
            self.name = self.address

    def save(self, *args, **kwargs):
        self.full_clean()
        super(PowerControlDevice, self).save(*args, **kwargs)

    @property
    def is_ipmi(self):
        return self.device_type.max_outlets == 0

    @property
    def all_outlets_known(self):
        return all([True if o.has_power in [True, False] else False for o in self.outlets.all()])

    @property
    def sockaddr(self):
        "Convenience method for getting at (self.address, self.port)"
        return (self.address, self.port)

    def _template_to_command(self, template, identifier=None):
        import re
        from os.path import expanduser

        cmd_str = getattr(self.device_type, "%s_template" % template) % {
            "agent": self.device_type.agent,
            "address": self.address,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "identifier": identifier,
            "options": self.options,
            "home": expanduser("~"),
            "list_parameter": "list-status" if platform_info.distro_version >= 7.0 else "list",
        }
        return re.split(r"\s+", cmd_str)

    def poweron_command(self, identifier):
        return self._template_to_command("poweron", identifier)

    def poweroff_command(self, identifier):
        return self._template_to_command("poweroff", identifier)

    def powercycle_command(self, identifier):
        return self._template_to_command("powercycle", identifier)

    def monitor_command(self, identifier=None):
        return self._template_to_command("monitor", identifier)

    def outlet_query_command(self, identifier):
        return self._template_to_command("outlet_query", identifier)

    def outlet_list_command(self):
        return self._template_to_command("outlet_list")


@receiver(post_save, sender=PowerControlDevice)
def prepopulate_outlets(sender, instance, created, **kwargs):
    # Prepopulate outlets for real PDUs. IPMI "PDUs" don't have a
    # fixed number of outlets
    if created and not instance.is_ipmi:
        for i in xrange(1, instance.device_type.max_outlets + 1):
            instance.outlets.create(identifier=i)


@receiver(post_save, sender=PowerControlDevice)
def register_power_device(sender, instance, created, **kwargs):
    from chroma_core.services.power_control.rpc import PowerControlRpc

    if instance.not_deleted is None:
        return

    if not created:
        PowerControlRpc().reregister_device(instance.id)
    else:
        PowerControlRpc().register_device(instance.id)


@receiver(post_delete, sender=PowerControlDevice)
def unregister_power_device(sender, instance, **kwargs):
    from chroma_core.services.power_control.rpc import PowerControlRpc

    PowerControlRpc().unregister_device(instance.sockaddr)


@receiver(pre_delete, sender=PowerControlDevice)
def delete_outlets(sender, instance, **kwargs):
    [o.mark_deleted() for o in instance.outlets.all()]


class PowerControlDeviceOutlet(DeletablePowerControlModel):
    device = models.ForeignKey("PowerControlDevice", related_name="outlets")
    # http://www.freesoft.org/CIE/RFC/1035/9.htm (max dns name == 255 octets)
    identifier = models.CharField(
        null=False,
        blank=False,
        max_length=254,
        help_text="A string by which the associated device can identify the controlled resource (e.g. PDU outlet number, libvirt domain name, ipmi mgmt address, etc.)",
    )
    host = models.ForeignKey(
        "ManagedHost",
        related_name="outlets",
        null=True,
        blank=True,
        help_text="Optional association with a ManagedHost instance",
    )
    has_power = models.NullBooleanField(help_text="Outlet power status (On, Off, Unknown)")

    def clean(self):
        try:
            # Irritating. There is no way to tell from the constructed instance
            # if the validation is for a new object or one being updated.
            PowerControlDeviceOutlet.objects.get(identifier=self.identifier, device=self.device)
            is_update = True
        except PowerControlDeviceOutlet.DoesNotExist:
            is_update = False

        # Do not allow mixed PDU/IPMI configurations for a server. It's
        # just asking for trouble. We may support it eventually, but not
        # now.
        if self.host and self.host.outlets.count() > 0:
            devices = [o.device for o in self.host.outlets.all()] + [self.device]
            if any([d.is_ipmi for d in devices]) and not all([d.is_ipmi for d in devices]):
                raise ValidationError("Mixing of IPMI and PDU power control is not supported.")

        if self.device.is_ipmi and self.device.device_type.agent not in ["fence_virsh", "fence_vbox"]:
            # Special-case for IPMI "outlets". The identifier is the BMC
            # address.
            self.identifier = self.validate_inet_address(self.identifier)

        max_device_outlets = self.device.device_type.max_outlets
        if not is_update and not self.device.is_ipmi:
            if self.device.outlets.count() >= max_device_outlets:
                raise ValidationError(
                    "Device %s is already at maximum number of outlets: %d" % (self.device.name, max_device_outlets)
                )

        super(PowerControlDeviceOutlet, self).clean()

    def _hosts_for_fence_reconfiguration(self, current, previous):
        hosts = []

        job_log.debug("Fence reconfiguration plan for new: %s, old: %s" % (current, previous))
        if current:
            job_log.debug("* %s: add outlet %s" % (current, self.id))
            hosts.append(current)

        if previous and previous != current:
            job_log.debug("* %s: remove outlet %s" % (previous, self.id))
            hosts.append(previous)

        return hosts

    def save(self, *args, **kwargs):
        self.full_clean()

        # Grab a copy of the outlet pre-save so that we can determine
        # which hosts need to have their fencing reconfigured.
        try:
            old_self = PowerControlDeviceOutlet.objects.get(pk=self.pk)
        except PowerControlDeviceOutlet.DoesNotExist:
            old_self = None

        super(PowerControlDeviceOutlet, self).save(*args, **kwargs)

        # Need to force a commit here to ensure that the updated outlet
        # configuration is available to other threads (e.g. fence reconfig).
        from django.db import transaction

        transaction.commit()

        reconfigure = {"reconfigure_fencing": True}
        previous = old_self.host if old_self else None
        for host in self._hosts_for_fence_reconfiguration(self.host, previous):
            if host.pacemaker_configuration:
                job_scheduler_notify.notify(host.pacemaker_configuration, tznow(), reconfigure)
            else:
                job_log.debug("Skipping reconfiguration of non-server %s" % host)

    @property
    def power_state(self):
        if self.has_power is None:
            return "Unknown"
        else:
            return "ON" if self.has_power else "OFF"

    def __str__(self):
        return self.identifier

    class Meta:
        app_label = "chroma_core"
        unique_together = ("device", "identifier")


class PoweronHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)
    requires_confirmation = True
    classes = ["ManagedHost"]
    verb = "Power On"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 70

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        if host.immutable_state:
            return False

        # We should only be able to issue a Poweron if:
        # 1. The host is associated with >= 1 outlet
        # 2. At least one associated outlet is in a known state (On or Off)
        # 3. None of the associated outlets are On
        return (
            host.outlets.count()
            and any([True if o.has_power in [True, False] else False for o in host.outlets.all()])
            and not any([o.has_power for o in host.outlets.all()])
        )

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["poweron_host"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    def description(self):
        return "Restore power for server %s" % self.host

    def get_steps(self):
        return [(TogglePduOutletStateStep, {"outlets": self.host.outlets.all(), "toggle_state": "on"})]


class PoweroffHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)
    requires_confirmation = True
    classes = ["ManagedHost"]
    verb = "Power Off"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 80

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        if host.immutable_state:
            return False

        # We should only be able to issue a Poweroff if:
        # 1. The host is associated with >= 1 outlet
        # 2. All associated outlets are in a known state (On or Off)
        # 3. At least one of the associated outlets is On
        return (
            host.outlets.count()
            and all([True if o.has_power in [True, False] else False for o in host.outlets.all()])
            and any([o.has_power for o in host.outlets.all()])
        )

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["poweroff_host"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    def description(self):
        return "Kill power for server %s" % self.host

    def get_steps(self):
        return [(TogglePduOutletStateStep, {"outlets": self.host.outlets.all(), "toggle_state": "off"})]


class PowercycleHostJob(AdvertisedJob):
    host = models.ForeignKey(ManagedHost)
    requires_confirmation = True
    classes = ["ManagedHost"]
    verb = "Power cycle"

    display_group = Job.JOB_GROUPS.INFREQUENT
    display_order = 90

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def get_args(cls, host):
        return {"host_id": host.id}

    @classmethod
    def can_run(cls, host):
        if host.immutable_state:
            return False

        # We should be able to issue a Powercycle if:
        # 1. The host is associated with >= 1 outlet
        #
        # NB: Issuing a powercycle will always result in the outlet being
        # switched On, so we can rely on this to get into a known state.
        return host.outlets.count() > 0

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["powercycle_host"]

    @classmethod
    def get_confirmation(cls, stateful_object):
        return cls.long_description(stateful_object)

    def description(self):
        return "Cycle power for server %s" % self.host

    def get_steps(self):
        # We can't use the PDU 'reboot' action, because that's per-outlet, and
        # a multi-PSU server will survive the cycling of each outlet unless
        # they're done in unison.
        outlets = self.host.outlets.all()
        outlets_off_step = (TogglePduOutletStateStep, {"outlets": outlets, "toggle_state": "off"})
        outlets_on_step = (TogglePduOutletStateStep, {"outlets": outlets, "toggle_state": "on"})
        return [outlets_off_step, outlets_on_step]


class TogglePduOutletStateStep(Step):
    idempotent = True
    # FIXME: This is necessary in order to invoke RPCs (HYD-1912)
    database = True

    def run(self, args):
        from chroma_core.services.power_control.client import PowerControlClient

        PowerControlClient.toggle_device_outlets(args["toggle_state"], args["outlets"])
