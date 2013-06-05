import os
import json

from testconfig import config
from nose.tools import nottest


class Testdata:
    """
    This class reads and returns data from config file and test data file that is used by the test cases
    """

    def __init__(self):
        cluster_data_file_path = os.environ['CLUSTER_DATA']
        self.cluster_json_data = open(cluster_data_file_path)
        self.cluster_data = json.load(self.cluster_json_data)

    @nottest
    def get_test_data_for_server_configuration(self):
        # read and return host related data from config file
        host_list = config['lustre_servers']
        return host_list

    @nottest
    def get_test_data_for_filesystem_configuration(self):
        # read and return file system related data from config file
        fs_list = self.cluster_data["filesystems"]
        return fs_list

    @nottest
    def get_test_data_for_conf_params(self):
        # read and return data from test data file for conf params
        return self.cluster_data['conf_params']

    @nottest
    def get_test_data_for_user(self, username=None):
        # read and return data from test data file for user.
        # If a username is passed returns the cooresponding user.
        # If username is not passed, returns the full list.
        users = self.cluster_data['user']

        if username:
            return next(user for user in users if user['username'] == username)
        else:
            return users
