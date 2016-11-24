import mock


from chroma_agent.action_plugins import manage_targets
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class TestManagePacemaker(CommandCaptureTestCase):
    def setUp(self):
        super(TestManagePacemaker, self).setUp()

        mock.patch('time.sleep').start()
        mock.patch('chroma_agent.action_plugins.manage_targets.get_resource_locations').start()

        self.target_disk = 'target_disk'
        self.target_node = 'target.node.com'

        self.add_commands(CommandCaptureCommand(('crm_mon', '-1')),
                          CommandCaptureCommand(('crm_resource', '--resource', self.target_disk, '--cleanup')),
                          CommandCaptureCommand(('crm_resource', '--resource', self.target_disk, '--move', '--node', self.target_node)),
                          CommandCaptureCommand(('crm_resource', '--resource', self.target_disk, '--un-move', '--node', self.target_node)))

    def test__move_target(self):
        mock.patch('chroma_agent.action_plugins.manage_targets.get_resource_location',
                   side_effect=[self.target_node]).start()

        self.assertEqual(manage_targets._move_target(self.target_disk, self.target_node), None)
        self.assertRanAllCommandsInOrder()

    def test__move_target_retry(self):
        mock.patch('chroma_agent.action_plugins.manage_targets.get_resource_location',
                   side_effect=['', '', self.target_node]).start()

        self.assertEqual(manage_targets._move_target(self.target_disk, self.target_node), None)
        self.assertRanAllCommandsInOrder()

    def test__move_target_fail(self):
        mock.patch('chroma_agent.action_plugins.manage_targets.get_resource_location', return_value='').start()

        self.assertEqual(manage_targets._move_target(self.target_disk, self.target_node),
                         'Failed to move target %s to node %s' % (self.target_disk, self.target_node))
        self.assertRanAllCommandsInOrder()
