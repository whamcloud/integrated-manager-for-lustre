# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import shutil
import tempfile

from iml_common.lib.util import PreserveFileAttributes


class NTPConfig(object):
    """ Class to enable IML to automatically configure NTP """

    DEFAULT_CONFIG_FILE = "/etc/ntp.conf"
    # use only a single marker for replace, comment and insert actions on config file
    MARKER = "# IML_EDITv1"
    PREFIX = "server"
    IBURST = "iburst"

    def __init__(self, config_file=DEFAULT_CONFIG_FILE, logger=None):
        """
        Init configures instance variables

        :param config_file: destination directory for resultant config file
        :param logger: external logger to write messages to
        """
        self.logger = logger
        self.config_path = config_file
        self.lines = []  # lines to be read in from config file

    def get_configured_server(self, markers):
        """
        Return the IML-configured server found in the ntp conf file

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
            with open(self.config_path, "r") as f:
                lines = f.readlines()
        except IOError as e:
            self._log(e.message, level="error")
            return None

        found = None
        # verify this config file has IML custom edits
        for line in lines:
            try:
                found = next(mark for mark in markers if line.find(mark) >= 0)
                # we have found an IML edit in configurations file
                break
            except StopIteration:
                pass
        if not found:
            # no IML edits found
            return None

        # find first server directive in IML-modified file
        try:
            server = next(line.split()[1] for line in lines if line.startswith("server "))
        except StopIteration:
            self._log("no configured server found in IML-modified ntp config file", level="debug")
            return None
        if server == "127.127.1.0":
            # ntp configured to use local clock
            return "localhost"
        return server

    def _log(self, msg, level="info"):
        """ utility function for using reference to an external logger """
        if self.logger and hasattr(self.logger, level):
            getattr(self.logger, level)("{0}: {1}".format(self.__class__.__name__, msg))

    def _reset_and_read_conf(self):
        """
        Read the contents of the config file into list of strings/lines, because we are using a
        pre-configured file there should be no IML changes and only standard ntp (v4) formatting
        """
        # read in file content
        with open(self.config_path, "r") as f:
            original_lines = f.readlines()

        self.lines = []

        for line in original_lines:
            if self.MARKER in line:
                # retrieve commented out directive from line
                line = line[line.find(self.MARKER) + len(self.MARKER) + 1 :]
                # don't append edited lines not replacing an old directive
                if line.strip() != "":
                    self.lines.append(line)
            else:
                self.lines.append(line)

    def _write_conf(self):
        """
        Create and open temporary file and write new config content, rename to config
        destination file. Close any open files and file descriptors
        """
        with PreserveFileAttributes(self.config_path):
            tmp_fd, tmp_name = tempfile.mkstemp(dir="/etc")
            os.write(tmp_fd, "".join(self.lines))
            os.close(tmp_fd)
            shutil.move(tmp_name, self.config_path)

    def _get_prefix_index(self):
        """ Helper method to return first index of string starting with prefix in list """
        try:
            return next(idx for idx, value in enumerate(self.lines) if value.startswith(self.PREFIX + " "))
        except StopIteration:
            return None

    def _add(self, server):
        """
        Replace server directive in ntp config file data, new server at the same index as the
        first server directive found.
        Appends directive to file if no active server is found in config file.

        Note: we don't make any assumptions as to the location of directives within the file

        :input: server    replacement server to add in config file directive
        """
        prefix_index = self._get_prefix_index()
        first_prefix_index = None
        line_to_replace = "\n"

        if prefix_index is not None:
            # Mark the index of the first directive we find, this is where we want add the server
            first_prefix_index = prefix_index

            # remove this server directive and comment subsequent ones
            line_to_replace = self.lines.pop(prefix_index)
            prefix_index = self._get_prefix_index()

            # while server directive found in lines, comment out line with marker
            while prefix_index is not None:
                self.lines[prefix_index] = " ".join([self.MARKER, self.lines[prefix_index]])
                prefix_index = self._get_prefix_index()

        # now we have stored the first server directive and commented out others, add the new content
        if server == "localhost":
            # add local clock to config
            content = [
                "server  127.127.1.0 %s\n" % self.MARKER,
                "fudge   127.127.1.0 stratum 10 %s %s" % (self.MARKER, line_to_replace),
            ]
        else:
            content = [" ".join([self.PREFIX, server, self.IBURST, self.MARKER, line_to_replace])]

        for line in content:
            # if no server directives found in file, append content to the end of the file
            # otherwise, once all server directives have been commented out, add content where the first server was
            if first_prefix_index is None:
                self.lines.append(line)
            else:
                self.lines.insert(first_prefix_index, line)
                # increment indexed to preserve order of content list in config file
                first_prefix_index += 1

    def add(self, server):
        """
        Add server directive to the ntp config file, if no server in config then append given hostname in directive
        at end of file, otherwise, replace existing server directive with that provided

        Comment out any additional server directives

        If server parameter is empty/None, reinstate saved backup file to reset any IML changes

        :return: None on success, error string otherwise
        """
        try:
            self._reset_and_read_conf()

            # proceed if we have no error and server name has been provided
            if server:
                self._add(server)

            self._write_conf()
        except (IOError, OSError) as e:
            self._log(e.message, level="error")

            return e.message

        return None
