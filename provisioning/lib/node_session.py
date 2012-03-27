
import settings

import fabric
from boto.ec2.connection import EC2Connection
from fabric.operations import run
import time
import datetime


class NodeSession(object):
    """Wait for an EC2 instance to be in a ready state and SSH-contactable,
    then provide the fabric parameters for running shell operations on it"""
    def __init__(self, node):
        self.node = node
        conn = EC2Connection(settings.AWS_KEY_ID, settings.AWS_SECRET)
        reservations = conn.get_all_instances([node.ec2_id])
        assert(len(reservations) == 1)
        instance = reservations[0].instances[0]

        # FIXME: modify an env for this class, rather than process scope
        while instance.state_code == 0:
            print "%s Waiting (state %s)..." % (datetime.datetime.now(), instance.state_code)
            time.sleep(10)
            reservations = conn.get_all_instances([node.ec2_id])
            assert(len(reservations) == 1)
            instance = reservations[0].instances[0]

        self.instance = instance

        if instance.state_code != 16:
            raise RuntimeError("Instance %s has bad state code %s" % (node.ec2_id, instance.state_code))

        with self.fabric_settings():
            from fabric.exceptions import NetworkError
            connected = False
            while not connected:
                try:
                    run('uname -a')
                    connected = True
                    print "%s Connected" % (datetime.datetime.now())
                except NetworkError:
                    print "%s Connecting to %s..." % (datetime.datetime.now(), node.ec2_id)
                    time.sleep(10)

    def fabric_settings(self):
        return fabric.context_managers.settings(
            user = self.node.username,
            key_filename = [settings.AWS_SSH_PRIVATE_KEY],
            host_string = self.instance.ip_address)


