#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from testconfig import config
import os
import json


class Testdata:
    """
    This class reads and returns data from config file and test data file that is used by the test cases
    """

    def __init__(self):
        cluster_data_file_path = os.environ['CLUSTER_DATA']
        self.cluster_json_data = open(cluster_data_file_path)
        self.cluster_data = json.load(self.cluster_json_data)

    def get_test_data_for_server_configuration(self):
        # read and return host related data from config file
        host_list = config["hosts"]
        return host_list

    def get_test_data_for_filesystem_configuration(self):
        # read and return file system related data from config file
        fs_list = self.cluster_data["filesystems"]
        return fs_list

    def get_test_data_for_conf_params(self):
        # read and return data from test data file for conf params
        return self.cluster_data['conf_params']

    def get_test_data_for_user(self):
        # read and return data from test data file for user
        return self.cluster_data['user']
