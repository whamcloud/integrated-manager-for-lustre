import abc
import mock
from django.utils import unittest

from chroma_agent.chroma_common.lib.ntp import AgentNTPConfig
from chroma_agent.chroma_common.lib.ntp import ManagerNTPConfig


class BaseTest:
    """ Encapsulating BasedTestNTPConfig allows it to contain base test cases without them being
    run on the base class and to have setUp/teardown methods that are called by unittest.TestCase.
    The alternative solution of multiple inheritance results in having to have the mixin class
    first in the MRO, which feels like a more error-prone solution.
    """

    class BaseTestNTPConfig(unittest.TestCase):
        """ Base class for NTP configuration with abstract methods """
        __metaclass__ = abc.ABCMeta

        @abc.abstractmethod
        def __init__(self, *args, **kwargs):
            """ Prefix test docstrings with the subclass name so we don't have to override base
            class methods just to add subclass specific docstring. Call 'super' AFTER making
            changes to allow TestCase parent class to use modified docstring
            """
            # iterate through test method names
            for name in [meth for meth in dir(self) if meth.startswith('test_')]:
                test = getattr(self, name)
                cls_name = self.__class__.__name__
                if test.__doc__ and test.__doc__.startswith(' test '):
                    # prepend docstring with subclass name
                    test.im_func.__doc__ = '{0}: {1}'.format(cls_name, test.__doc__)
            super(BaseTest.BaseTestNTPConfig, self).__init__(*args, **kwargs)

        def init_ntp(self, ntp_class):
            self.ntp = ntp_class()

        def setUp(self):
            # each time we run _reset_and_read_conf, pre-chroma config file is reloaded and config reset
            mock.patch.object(self.ntp, '_reset_and_read_conf', return_value=None,
                              side_effect=self._reset_lines).start()
            mock.patch.object(self.ntp, '_write_conf', return_value=None).start()

            self.addCleanup(mock.patch.stopall)

            self.existing_server = 'iml.ntp.com'
            self.existing_directive = self._directive(self.existing_server)

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
                'local-ip': [
                    '# Use public servers from the pool.ntp.org project.\n',
                    '# Please consider joining the pool (http://www.pool.ntp.org/join.html).\n',
                    '#server 0.centos.pool.ntp.org iburst\n',
                    '#server 1.centos.pool.ntp.org iburst\n',
                    '#server 2.centos.pool.ntp.org iburst\n',
                    '#server 3.centos.pool.ntp.org iburst\n',
                    '\n',
                    'server 127.127.1.0     {0} local clock\n'.format(self.ntp.MARKER),
                    'fudge   127.127.1.0 stratum 10 {0}\n'.format(self.ntp.MARKER)]}
            return lines[variant]

        def _directive(self, hostname):
            """ helper method to return config file server directive """
            return 'server {0} iburst'.format(hostname)

        def test_get_server(self):
            """ test fetching server hostname from ntp config,
            test possible sentinel and comment strings in config for backward compatibility

            because get_configured_server() doesn't use _{read|write}_conf as add() does,
            we need to mock open explicitly and make the return file object return a specific
            list of strings on readlines() call
            """
            mock_open = mock.mock_open()
            mock_open.return_value.readlines.return_value = self._get_lines('iml')
            mock.patch('__builtin__.open', mock_open, create=True).start()

            server = self.ntp.get_configured_server()
            self.assertEqual(server, self.existing_server)

        def test_get_server_localhost(self):
            """ test fetching server when specified as localhost in ntp config
            test possible sentinel and comment strings in config for backward compatibility

            because get_configured_server() doesn't use _{read|write}_conf as add() does,
            we need to mock open explicitly and make the return file object return a specific
            list of strings on readlines() call
            """
            mock_open = mock.mock_open()
            mock_open.return_value.readlines.return_value = self._get_lines('local-ip')
            mock.patch('__builtin__.open', mock_open, create=True).start()

            server = self.ntp.get_configured_server()
            self.assertEqual(server, 'localhost')

        def test_get_server_from_empty_config(self):
            """ test fetching server from ntp config with no active entry
            test possible sentinel and comment strings in config for backward compatibility

            because get_configured_server() doesn't use _{read|write}_conf as add() does,
            we need to mock open explicitly and make the return file object return a specific
            list of strings on readlines() call
            """
            mock_open = mock.mock_open()
            mock_open.return_value.readlines.return_value = self._get_lines('pre-iml')
            mock.patch('__builtin__.open', mock_open, create=True).start()

            server = self.ntp.get_configured_server()
            self.assertEqual(server, None)

        def test_add_remove_configured(self):
            """ test adding and then removing IML configuration from ntp config content by
            restoring previous configuration
            """
            # add desired line to config
            error = self.ntp.add(self.existing_server)
            self.assertEqual(error, None)
            self.assertListEqual(self.ntp.lines, self._get_lines('iml'))

            # remove any iml configuration
            error = self.ntp.add(None)
            self.assertEqual(error, None)
            self.assertListEqual(self.ntp.lines, self._get_lines('pre-iml'))

        @abc.abstractmethod
        def test_add_localhost(self):
            """ test adding localhost to ntp config file content, behaviour differs for
            different subclasses of NTPConfig
            """
            return 'NotImplemented'

        @abc.abstractmethod
        def test_add_localhost_empty_config(self):
            """ test adding localhost to ntp config content with no active server directives """
            return 'NotImplemented'


class TestAgentNTPConfig(BaseTest.BaseTestNTPConfig):

    def __init__(self, *args, **kwargs):
        """ initialise correct NTP config instance from class, call ntp initialisation with
        this subclass
        """
        super(TestAgentNTPConfig, self).__init__(*args, **kwargs)
        self.init_ntp(AgentNTPConfig)

    def test_add_localhost(self):
        """ test adding localhost to ntp config content, server directive with localhost or
        hostname is added or replaces current configuration
        """
        server = 'localhost'
        self.ntp.add(server)
        self.assertIn('server localhost {0} server 0.centos.pool.ntp.org iburst\n'.format(
            self.ntp.MARKER), self.ntp.lines)
        self.assertNotIn(self.existing_directive, self.ntp.lines)

    def test_add_localhost_empty_config(self):
        """ test adding localhost to ntp config content with no active server directives """
        server = 'localhost'
        self.ntp.lines = self._get_lines('no-servers')
        # we don't want _reset_and_read_conf to reload 'iml' lines, override the mock patch
        mock.patch.object(self.ntp, '_reset_and_read_conf', return_value=None).start()
        self.ntp.add(server)
        self.assertIn('server localhost {0}\n'.format(self.ntp.MARKER), self.ntp.lines)


class TestManagerNTPConfig(BaseTest.BaseTestNTPConfig):

    def __init__(self, *args, **kwargs):
        """ initialise correct NTP config instance from class, call ntp initialisation with
        this subclass
        """
        super(TestManagerNTPConfig, self).__init__(*args, **kwargs)
        self.init_ntp(ManagerNTPConfig)

    def test_add_localhost(self):
        """ test adding localhost to ntp config content, existing server configurations are not
        replaced by localhost server directives
        """
        server = 'localhost'
        self.ntp.add(server)
        self.assertListEqual(self.ntp.lines, self._get_lines('pre-iml'))

    def test_add_localhost_empty_config(self):
        """ test adding localhost to ntp config content with no active server directives,
        IP address and local clock 'fudge' directives should be added when applying localhost
        as ntp server
        """
        server = 'localhost'
        self.ntp.lines = self._get_lines('no-servers')
        # we don't want _reset_and_read_conf to reload 'iml' lines, override the mock patch
        mock.patch.object(self.ntp, '_reset_and_read_conf', return_value=None).start()
        self.ntp.add(server)
        self.assertListEqual(self.ntp.lines, self._get_lines('local-ip'))
