#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

import os
import shutil
import tempfile
import abc


class BaseNTPConfig(object):
    """Base class for NTP configuration with abstract methods"""
    __metaclass__ = abc.ABCMeta

    DEFAULT_CONFIG_FILE = '/etc/ntp.conf'
    PRE_CHROMA_CONFIG_FILE = '/etc/ntp.conf.pre-chroma'
    # use only a single marker for replace, comment and insert actions on config file
    MARKER = '# IML_EDITv1'
    PREFIX = 'server'
    IBURST = 'iburst'

    def __init__(self, config_file=DEFAULT_CONFIG_FILE, logger=None):
        """Init configures instance variables

        :param config_file: destination directory for resultant config file
        :param logger: external logger to write messages to
        """
        self.logger = logger
        self.config_path = config_file
        self.lines = []       # lines to be read in from config file

    def get_configured_server(self, markers):
        """Return the IML-configured server found in the ntp conf file

        if IML did not set the server or if any error occurs return None.
        If IML did set the server and IML-markers are found, return server value

        Additional markers can be added as a list parameter, these will then be used to
        determine if the config file has IML edits

        :return: IML-set server found in config, None if no IML-configured server or IOError
        """
        if not markers:
            markers = []
        assert type(markers) is list
        markers.append(self.MARKER)

        # read in file content
        try:
            with open(self.config_path, 'r') as f:
                lines = f.readlines()
        except IOError as e:
            self._log(e.message, level='error')
            return None

        found = None
        # verify this config file has iml custom edits
        for line in lines:
            try:
                found = next(mark for mark in markers if line.find(mark) >= 0)
                # we have found an iml edit in configurations file
                break
            except StopIteration:
                pass
        if not found:
            # no iml edits found
            return None

        # find first server directive in iml-modified file
        try:
            server = next(line.split()[1] for line in lines if line.startswith('server '))
        except StopIteration:
            self._log('no configured server found in iml-modified ntp config file', level='debug')
            return None
        if server == '127.127.1.0':
            # ntp configured to use local clock
            return 'localhost'
        return server

    @abc.abstractmethod
    def add(self, server):
        """Add server directive to the ntp config file, this may differ subtly for agent
        and manager NTP configuration. Must implement in subclass, can make use of _add() fn
        """
        return 'NotImplemented'  # pragma: no cover

    def _log(self, msg, level='info'):
        """ utility function for using reference to an external logger """
        if self.logger and hasattr(self.logger, level):
            getattr(self.logger, level)('{0}: {1}'.format(self.__class__.__name__, msg))

    def _reset_and_read_conf(self):
        """Read the contents of the config file into list of strings/lines, because we are using a
        pre-configured file there should be no IML changes and only standard ntp (v4) formatting

        :return: None for success, error string otherwise
        """
        try:
            # if pre-iml config file exists, revert back to using it (remove iml configuration)
            if os.path.exists(self.PRE_CHROMA_CONFIG_FILE):
                shutil.copyfile(self.PRE_CHROMA_CONFIG_FILE, self.config_path)
            else:
                # otherwise backup the starting point before changes are made
                shutil.copyfile(self.config_path, self.PRE_CHROMA_CONFIG_FILE)

            # read in file content
            with open(self.config_path, 'r') as f:
                self.lines = f.readlines()
            return None
        except IOError as e:
            self._log(e.message, level='error')
            return e.message

    def _write_conf(self):
        """Create and open temporary file and write new config content, rename to config
        destination file. Close any open files and file descriptors

        :return: None for success, error string otherwise
        """
        try:
            tmp_fd, tmp_name = tempfile.mkstemp(dir='/etc')
            os.write(tmp_fd, ''.join(self.lines))
            os.close(tmp_fd)
            os.chmod(tmp_name, 0644)
            shutil.move(tmp_name, self.config_path)
            return None
        except (IOError, OSError) as e:
            self._log(e.message, level='error')
            return e.message

    def _index_containing_directive(self):
        """ Helper method to return first index of string containing substring in list """
        try:
            return next(idx for idx, value in enumerate(self.lines) if
                        value.startswith(self.PREFIX + ' '))
        except StopIteration:
            return None

    def _add(self, server):
        """Replace server directive in ntp config file data, new server at the same index as the
        first server directive found.
        Appends directive to file if no active server is found in config file.

        Note: we don't make any assumptions as to the location of directives within the file

        :input: server    replacement server to add in config file directive
        """
        if server == 'localhost':
            new_directive = ' '.join([self.PREFIX, server])
        else:
            new_directive = ' '.join([self.PREFIX, server, self.IBURST])

        directive_index = self._index_containing_directive()

        if directive_index is not None:
            # Mark the index of the first directive we find, this is where we want add the server
            first_directive_index = directive_index

            # remove this server directive and comment subsequent ones
            line_to_replace = self.lines.pop(directive_index)
            directive_index = self._index_containing_directive()

            # while server directive directive_found in lines, comment out line with marker
            while directive_index is not None:
                self.lines[directive_index] = ' '.join([self.MARKER, self.lines[directive_index]])
                directive_index = self._index_containing_directive()

            # once all server directives have been commented out, add ours where the first one was
            self.lines.insert(first_directive_index, ' '.join([new_directive, self.MARKER,
                                                               line_to_replace]))
        else:
            # no server directives found in file, append ours to the end of the file contents
            self.lines.append(''.join([new_directive, ' ', self.MARKER, '\n']))


class AgentNTPConfig(BaseNTPConfig):
    """ Concrete implementation for the agent NTP configuration """

    def add(self, server):
        """If no server in config then append given hostname in directive at end of file,
        otherwise, replace existing server directive with that provided
        Comment any additional server directives

        If server parameter is empty/None, reinstate saved backup file to reset any IML changes

        :return: None for success, error string otherwise
        """
        error = self._reset_and_read_conf()

        # proceed if we have no error and server name has been provided
        if (error is None) and server:
            self._add(server)
            error = self._write_conf()

        return error


class ManagerNTPConfig(BaseNTPConfig):
    """ Concrete implementation for the manager NTP configuration """

    def get_configured_server(self, markers=None):
        """Override base method to look for old-style sentinel in config file

        :param markers: list of sentinels to look for
        :return: configured server name if successful, None if not
        """
        return super(ManagerNTPConfig, self).get_configured_server(markers=['# Added by chroma-manager\n'])

    def add(self, server):
        """If no server in config then append given hostname in directive at end of file
        Localhost can be used with local clock as the reference, but don't override existing
        server with localhost

        If server parameter is empty/None, reinstate saved backup file to reset any IML changes

        :return: None for success, error string otherwise
        """
        error = self._reset_and_read_conf()

        # proceed if we have no error and server name has been provided
        if (error is None) and server:
            if server == 'localhost':
                if self._index_containing_directive() is None:
                    for line in ['server 127.127.1.0     {0} local clock\n'.format(self.MARKER),
                                 'fudge   127.127.1.0 stratum 10 {0}\n'.format(self.MARKER)]:
                        self.lines.append(line)
                else:
                    self._log('not overriding existing server directive with localhost, '
                              'no changes made to ntp.conf', 'debug')
                    return None
            else:
                self._add(server)
            error = self._write_conf()

        return error
