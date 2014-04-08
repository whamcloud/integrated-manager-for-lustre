import mock
from django.utils import unittest

from chroma_agent.action_plugins.manage_corosync import configure_fencing, set_node_standby, set_node_online
from chroma_agent.lib.pacemaker import PacemakerNode


class FencingTestCase(unittest.TestCase):
    fake_node_hostname = 'fake.host.domain'
    fake_node_kwargs = {fake_node_hostname: {'name': fake_node_hostname,
                                             'attributes': {}}}
    stdin_lines = None

    def setUp(self):
        super(FencingTestCase, self).setUp()
        import chroma_agent.shell
        patcher = mock.patch.object(chroma_agent.shell, '_run',
                                    return_value=(0, '', ''))
        self._run = patcher.start()

        def fake_hostname():
            return self.fake_node_hostname
        patcher = mock.patch('socket.gethostname', fake_hostname)
        patcher.start()

        @property
        def nodes(obj):
            return [PacemakerNode(**self.fake_node_kwargs[self.fake_node_hostname])]
        patcher = mock.patch('chroma_agent.lib.pacemaker.PacemakerConfig.nodes', nodes)
        patcher.start()

        import chroma_agent.fence_chroma
        real_stdin_to_args = chroma_agent.fence_chroma.stdin_to_args

        def stdin_to_args(**kwargs):
            return real_stdin_to_args(self.stdin_lines)
        patcher = mock.patch('chroma_agent.fence_chroma.stdin_to_args', stdin_to_args)
        patcher.start()

        # nose confuses things
        import sys
        sys.argv = ['fence_chroma']

        # Guaranteed cleanup with unittest2
        self.addCleanup(mock.patch.stopall)


class TestAgentConfiguration(FencingTestCase):
    def test_multi_agent_config(self):
        agents = [{'agent': 'fence_virsh',
                   'ipaddr': '1.2.3.4',
                   'ipport': '22',
                   'login': 'monkey',
                   'password': 'banana',
                   'plug': 'monkey_vm'},
                  {'agent': 'fence_apc',
                   'ipaddr': '4.3.2.1',
                   'ipport': '23',
                   'login': 'apc',
                   'password': 'apc',
                   'plug': '1'}]

        configure_fencing(agents)
        for i, agent in enumerate(agents):
            for key, val in agent.items():
                self._run.assert_any_call(['crm_attribute', '-t', 'nodes', '-U', self.fake_node_hostname, '-n', '%d_fence_%s' % (i, key), '-v', val])

        # HYD-2104: Ensure that the N_fence_agent attribute was added
        # last.
        for i in xrange(len(agents)):
            # We lost an attribute to pop()
            attr_len = len(agents[0]) + 1
            # Gnarly, but it works...
            call_index = ((((len(agents) * attr_len) - (attr_len * i) - attr_len) + 1) * -1)
            self.assertIn('%d_fence_agent' % i, self._run.mock_calls[call_index][1][0])

    def test_empty_agents_clears_fence_config(self):
        fake_attributes = {'0_fence_agent': 'fake_agent',
                           '0_fence_login': 'admin',
                           '0_fence_password': 'yourmom'}
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = fake_attributes

        configure_fencing([])
        for key in fake_attributes:
            self._run.assert_any_call(['crm_attribute', '-D', '-t', 'nodes', '-U', self.fake_node_hostname, '-n', key])

        # HYD-2104: Ensure that the N_fence_agent attribute was removed
        # first.
        call_index = len(fake_attributes) * -1
        self.assertIn('0_fence_agent', self._run.mock_calls[call_index][1][0])

    def test_node_standby(self):
        set_node_standby(self.fake_node_hostname)

        self._run.assert_any_call(['crm_attribute', '-N', self.fake_node_hostname, '-n', 'standby', '-v', 'on', '--lifetime=forever'])

    def test_node_online(self):
        set_node_online(self.fake_node_hostname)

        self._run.assert_any_call(['crm_attribute', '-N', self.fake_node_hostname, '-n', 'standby', '-v', 'off', '--lifetime=forever'])


class TestFenceAgent(FencingTestCase):
    fake_attributes = {'0_fence_agent': 'fence_apc',
                           '0_fence_login': 'admin',
                           '0_fence_password': 'yourmom',
                           '0_fence_ipaddr': '1.2.3.4',
                           '0_fence_plug': '1'}
    call_template = "%(0_fence_agent)s -a %(0_fence_ipaddr)s -u 23 -l %(0_fence_login)s -p %(0_fence_password)s -n %(0_fence_plug)s" % fake_attributes
    call_base = call_template.split()

    def test_finding_fenceable_nodes(self):
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = self.fake_attributes

        # Not strictly an agent test, but the tested method is used by
        # the agent to generate the -o list output.
        from chroma_agent.lib.pacemaker import PacemakerConfig
        p_cfg = PacemakerConfig()
        self.assertEqual(len(p_cfg.fenceable_nodes), 1)

    def test_fence_agent_reboot(self):
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = self.fake_attributes

        from chroma_agent.fence_chroma import main as agent_main

        # Normal use, stonithd feeds commands via stdin
        self.stdin_lines = ["nodename=%s" % self.fake_node_hostname,
                            "action=reboot",
                            "port=%s" % self.fake_node_hostname]
        agent_main()
        self._run.assert_any_call(self.call_base + ['-o', 'off'])
        self._run.assert_any_call(self.call_base + ['-o', 'on'])

        # Command-line should work too
        agent_main(['-o', 'reboot', '-n', self.fake_node_hostname])
        self._run.assert_any_call(self.call_base + ['-o', 'off'])
        self._run.assert_any_call(self.call_base + ['-o', 'on'])

    def test_fence_agent_on_off(self):
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = self.fake_attributes

        from chroma_agent.fence_chroma import main as agent_main

        # These options aren't likely to be used for STONITH, but they
        # should still work for manual invocation.
        agent_main(['-o', 'off', '-n', self.fake_node_hostname])
        self._run.assert_any_call(self.call_base + ['-o', 'off'])

        agent_main(['-o', 'on', '-n', self.fake_node_hostname])
        self._run.assert_any_call(self.call_base + ['-o', 'on'])

    def test_fence_agent_monitor(self):
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = self.fake_attributes

        patcher = mock.patch('sys.exit')
        exit = patcher.start()

        # Kind of a silly test, but we just want to make sure that our
        # agent's monitor option doesn't barf.
        from chroma_agent.fence_chroma import main as agent_main
        agent_main(['-o', 'monitor'])
        exit.assert_called_with(0)

        # Make sure running with args from stdin works...
        self.stdin_lines = ["nodename=%s" % self.fake_node_hostname,
                            "action=monitor"]
        agent_main()
        exit.assert_called_with(0)

        # Apparently stonithd sometimes(?) uses option instead of action...
        self.stdin_lines = ["nodename=%s" % self.fake_node_hostname,
                            "option=monitor"]
        agent_main()
        exit.assert_called_with(0)

    def test_standby_node_not_fenced(self):
        # a node in standby should not be fenced
        attributes = self.fake_attributes.copy()
        attributes['standby'] = "on"
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = attributes

        from chroma_agent.fence_chroma import main as agent_main

        agent_args = ['-o', 'off', '-n', self.fake_node_hostname]
        agent_main(agent_args)

        # Trim the -n hostname args off because they're not actually used
        # in the production code -- we just need them due to the hokey
        # fake_node_kwargs stuff.
        mock_call = self.call_base + agent_args[:-2]
        self.assertNotIn(mock.call(mock_call),
                         self._run.mock_calls)
