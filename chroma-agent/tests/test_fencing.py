import mock
from django.utils import unittest

from chroma_agent.action_plugins.manage_corosync import configure_fencing
from chroma_agent.lib.pacemaker import PacemakerNode


class FencingTestCase(unittest.TestCase):
    fake_node_hostname = 'fake.host.domain'
    fake_node_kwargs = {fake_node_hostname: {'name': fake_node_hostname,
                                             'attributes': {}}}
    stdin_lines = None

    def setUp(self):
        super(FencingTestCase, self).setUp()
        import chroma_agent.shell
        patcher = mock.patch.object(chroma_agent.shell, 'try_run')
        self.try_run = patcher.start()

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
                self.try_run.assert_any_call(['crm_attribute', '-t', 'nodes', '-U', self.fake_node_hostname, '-n', '%d_fence_%s' % (i, key), '-v', val])

    def test_empty_agents_clears_fence_config(self):
        fake_attributes = {'0_fence_agent': 'fake_agent',
                           '0_fence_login': 'admin',
                           '0_fence_password': 'yourmom'}
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = fake_attributes

        configure_fencing([])
        for key in fake_attributes:
            self.try_run.assert_any_call(['crm_attribute', '-D', '-t', 'nodes', '-U', self.fake_node_hostname, '-n', key])


class TestFenceAgent(FencingTestCase):
    fake_attributes = {'0_fence_agent': 'fence_apc',
                           '0_fence_login': 'admin',
                           '0_fence_password': 'yourmom',
                           '0_fence_ipaddr': '1.2.3.4',
                           '0_fence_plug': '1'}

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
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'off'])
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'on'])

        # Command-line should work too
        agent_main(['-o', 'reboot', '-n', self.fake_node_hostname])
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'off'])
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'on'])

    def test_fence_agent_on_off(self):
        self.fake_node_kwargs[self.fake_node_hostname]['attributes'] = self.fake_attributes

        from chroma_agent.fence_chroma import main as agent_main

        # These options aren't likely to be used for STONITH, but they
        # should still work for manual invocation.
        agent_main(['-o', 'off', '-n', self.fake_node_hostname])
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'off'])

        agent_main(['-o', 'on', '-n', self.fake_node_hostname])
        self.try_run.assert_any_call(['fence_apc', '-a', '1.2.3.4', '-u', '23', '-l', 'admin', '-p', 'yourmom', '-n', '1', '-o', 'on'])

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
