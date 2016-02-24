import mock
from django.utils import unittest
from chroma_agent.chroma_common.lib.ntp import NTPConfig


class TestNTPConfig(unittest.TestCase):
    """ Test class for NTPConfig """

    def setUp(self):

        self.ntp = NTPConfig()

        # each time we run _reset_and_read_conf, pre-chroma config file is reloaded and config reset
        mock.patch.object(self.ntp, '_reset_and_read_conf', return_value=None,
                          side_effect=self._reset_lines).start()
        mock.patch.object(self.ntp, '_write_conf', return_value=None).start()

        self.addCleanup(mock.patch.stopall)

        self.existing_server = 'iml.ntp.com'
        self.existing_directive = self._directive(self.existing_server)

        # Constants for retrieving from legacy IML config files
        self.existing_directive_old = 'server ' + self.existing_server
        self.manager_marker = '# Added by chroma-manager\n'
        self.manager_comment = '# Commented out by chroma-manager: '

    def _reset_lines(self):
        self.ntp.lines = self._get_lines('pre-iml')

    def _get_lines(self, variant):
        lines = {
            'no-servers': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                '#server 0.centos.pool.ntp.org iburst\n',
                '#server 1.centos.pool.ntp.org iburst\n',
                '#server 2.centos.pool.ntp.org iburst\n',
                '#server 3.centos.pool.ntp.org iburst\n',
                '\n'],
            'pre-iml': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                'server 0.centos.pool.ntp.org iburst\n',
                'server 1.centos.pool.ntp.org iburst\n',
                'server 2.centos.pool.ntp.org iburst\n',
                'server 3.centos.pool.ntp.org iburst\n',
                '\n'],
            'iml': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                '{0} {1} server 0.centos.pool.ntp.org iburst\n'.format(
                    self.existing_directive, self.ntp.MARKER),
                '{0} server 1.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '{0} server 2.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '{0} server 3.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '\n'],
            'local-ip-insert': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                'server  127.127.1.0 {0} local clock\n'.format(self.ntp.MARKER),
                'fudge   127.127.1.0 stratum 10 {0}\n'.format(self.ntp.MARKER),
                '{0} server 0.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '{0} server 1.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '{0} server 2.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '{0} server 3.centos.pool.ntp.org iburst\n'.format(self.ntp.MARKER),
                '\n'],
            'local-ip-append': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                '#server 0.centos.pool.ntp.org iburst\n',
                '#server 1.centos.pool.ntp.org iburst\n',
                '#server 2.centos.pool.ntp.org iburst\n',
                '#server 3.centos.pool.ntp.org iburst\n',
                '\n',
                'server  127.127.1.0 {0} local clock\n'.format(self.ntp.MARKER),
                'fudge   127.127.1.0 stratum 10 {0}\n'.format(self.ntp.MARKER)],
            'iml-manager-old': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                self.manager_marker,
                self.existing_directive_old,
                self.manager_marker,
                '{0}server 0.centos.pool.ntp.org iburst\n'.format(self.manager_comment),
                '{0}server 1.centos.pool.ntp.org iburst\n'.format(self.manager_comment),
                '{0}server 2.centos.pool.ntp.org iburst\n'.format(self.manager_comment),
                '{0}server 3.centos.pool.ntp.org iburst\n'.format(self.manager_comment),
                '\n'],
            'local-ip-insert-manager-old': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                '#server 0.centos.pool.ntp.org iburst\n',
                '#server 1.centos.pool.ntp.org iburst\n',
                '#server 2.centos.pool.ntp.org iburst\n',
                '#server 3.centos.pool.ntp.org iburst\n',
                '#fudge \n',
                self.manager_marker,
                'server  127.127.1.0    # local clock\n',
                'fudge   127.127.1.0 stratum 10\n',
                self.manager_marker,
                '\n'],
            'local-ip-append-manager-old': [
                '# Use public servers from the pool.ntp.org project.\n',
                '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                self.manager_marker,
                'server  127.127.1.0    # local clock\n',
                'fudge   127.127.1.0 stratum 10\n',
                self.manager_marker,
                '# Enable public key cryptography.',
                '\n']}
        return lines[variant]

    @staticmethod
    def _directive(hostname):
        """ helper method to return config file server directive """
        return 'server {0} iburst'.format(hostname)

    def test_get_server(self):
        """
        test fetching server hostname from ntp config,
        test possible sentinel and comment strings in config for backward compatibility

        because get_configured_server() doesn't use _{read|write}_conf as add() does,
        we need to mock open explicitly and make the return file object return a specific
        list of strings on readlines() call
        """
        mock_open = mock.mock_open()
        mock_open.return_value.readlines.return_value = self._get_lines('iml')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=None)
        self.assertEqual(server, self.existing_server)

        # now test with old style config syntax for compatibility with legacy IML config files
        mock_open.return_value.readlines.return_value = self._get_lines('iml-manager-old')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=[self.manager_marker])
        self.assertEqual(server, self.existing_server)

    def test_get_server_localhost(self):
        """
        test fetching server when specified as localhost in ntp config
        test possible sentinel and comment strings in config for backward compatibility

        because get_configured_server() doesn't use _{read|write}_conf as add() does,
        we need to mock open explicitly and make the return file object return a specific
        list of strings on readlines() call
        """
        mock_open = mock.mock_open()
        mock_open.return_value.readlines.return_value = self._get_lines('local-ip-insert')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=None)
        self.assertEqual(server, 'localhost')

        mock_open.return_value.readlines.return_value = self._get_lines('local-ip-insert-manager-old')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=[self.manager_marker])
        self.assertEqual(server, 'localhost')

        mock_open.return_value.readlines.return_value = self._get_lines('local-ip-append')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=None)
        self.assertEqual(server, 'localhost')

        mock_open.return_value.readlines.return_value = self._get_lines('local-ip-append-manager-old')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=[self.manager_marker])
        self.assertEqual(server, 'localhost')

    def test_get_server_from_empty_config(self):
        """
        test fetching server from ntp config with no active entry
        test possible sentinel and comment strings in config for backward compatibility

        because get_configured_server() doesn't use _{read|write}_conf as add() does,
        we need to mock open explicitly and make the return file object return a specific
        list of strings on readlines() call
        """
        mock_open = mock.mock_open()
        mock_open.return_value.readlines.return_value = self._get_lines('pre-iml')
        mock.patch('__builtin__.open', mock_open, create=True).start()

        server = self.ntp.get_configured_server(markers=None)
        self.assertEqual(server, None)

        server = self.ntp.get_configured_server(markers=[self.manager_marker])
        self.assertEqual(server, None)

    def test_add_remove_configured(self):
        """
        test adding and then removing IML configuration from ntp config content
        by restoring previous configuration
        """
        # add desired line to config
        error = self.ntp.add(self.existing_server)
        self.assertEqual(error, None)
        self.assertListEqual(self.ntp.lines, self._get_lines('iml'))

        # remove any iml configuration
        error = self.ntp.add(None)
        self.assertEqual(error, None)
        self.assertListEqual(self.ntp.lines, self._get_lines('pre-iml'))

    def test_add_localhost(self):
        """
        test adding localhost to ntp config content
        if server directives exist, replace the first one with local clock fudge,
        if no server directives exist, append local clock fudge to end of file
        """
        self.ntp.add('localhost')
        self.assertListEqual(self.ntp.lines, self._get_lines('local-ip-insert'))

    def test_add_localhost_empty_config(self):
        """
        test adding localhost to ntp config content with no active server directives
        IP address and local clock 'fudge' directives should be appended when applying localhost
        """
        self.ntp.lines = self._get_lines('no-servers')

        # we don't want _reset_and_read_conf to reload 'iml' lines, override the mock patch
        mock.patch.object(self.ntp, '_reset_and_read_conf', return_value=None).start()

        self.ntp.add('localhost')
        self.assertListEqual(self.ntp.lines, self._get_lines('local-ip-append'))
