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


import xml.etree.ElementTree as xml
from xml.parsers.expat import ExpatError as ParseError

from chroma_agent import shell
from chroma_agent.lib import fence_agents


class PacemakerNode(object):
    def __init__(self, name, attributes=None):
        self.name = name
        self.attributes = attributes
        if not self.attributes:
            self.attributes = {}

    def fence_reboot(self):
        self.fence_off()
        self.fence_on()

    def fence_off(self):
        if self.attributes.get('standby', "off") != "on":
            for agent in self.fence_agents:
                agent.off()

    def fence_on(self):
        if self.attributes.get('standby', "off") != "on":
            for agent in self.fence_agents:
                agent.on()

    @property
    def fence_agents(self):
        agents = []
        for kwargs in self.fence_agent_kwargs:
            try:
                agents.append(getattr(fence_agents, kwargs['agent'])(**kwargs))
            except AttributeError:
                raise RuntimeError("No FenceAgent class for %s" % kwargs['agent'])
        return agents

    @property
    def fence_agent_kwargs(self):
        kwargs = []
        for ad in self.fence_agent_dicts:
            new = {}
            for k, v in ad.items():
                new[k[k.rfind('fence_') + 6:]] = v
            kwargs.append(new)
        return kwargs

    @property
    def fence_agent_dicts(self):
        agents = []
        for agent in [k for k in self.attributes if 'agent' in k]:
            index = agent[0:agent.find('_')]
            agents.append(dict([t for t in self.attributes.items()
                                    if t[0].startswith("%s_fence_" % index)]))

        return agents

    def set_fence_attribute(self, agent, key, value):
        self.set_attribute("%s_fence_%s" % (agent, key), value)

    def clear_fence_attribute(self, agent, key):
        self.set_attribute("%s_fence_%s" % (agent, key))

    def clear_fence_attributes(self):
        for fence_agent in self.fence_agent_dicts:
            for agent_attr in fence_agent:
                self.clear_attribute(agent_attr)

    def enable_standby(self):
        shell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "on", "--lifetime=forever"])

    def disable_standby(self):
        shell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "off", "--lifetime=forever"])

    # These crm_attribute options are undocumented, but they're exactly
    # what the crm utility uses when it does its thing. The documented
    # options don't actually work! Fun.
    def set_attribute(self, key, value):
        shell.try_run(["crm_attribute", "-t", "nodes", "-U", self.name, "-n", key, "-v", str(value)])

    def clear_attribute(self, key):
        shell.try_run(["crm_attribute", "-D", "-t", "nodes", "-U", self.name, "-n", key])


class PacemakerConfig(object):
    @property
    def root(self):
        raw = shell.try_run(["cibadmin", "--query"])
        try:
            return xml.fromstring(raw)
        except ParseError:
            raise RuntimeError("Unable to dump pacemaker config: is it running?")

    @property
    def configuration(self):
        return self.root.find('configuration')

    @property
    def nodes(self):
        nodes = []
        for node in self.configuration.find('nodes'):
            nodeobj = PacemakerNode(node.get('uname'))
            try:
                i_attrs = node.find('instance_attributes')
                for nvpair in i_attrs.findall('nvpair'):
                    nodeobj.attributes[nvpair.get('name')] = nvpair.get('value')
            except AttributeError:
                # No instance_attributes
                pass
            nodes.append(nodeobj)

        return nodes

    @property
    def fenceable_nodes(self):
        return [n for n in self.nodes if len(n.fence_agents) > 0]

    def get_node(self, node_name):
        try:
            return [n for n in self.nodes if n.name == node_name][0]
        except IndexError:
            raise RuntimeError("%s does not exist in pacemaker" % node_name)
