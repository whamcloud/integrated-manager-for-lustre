#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from tests.selenium.base_view import DatatableView
from tests.selenium.base import wait_for_transition


class Mgt(DatatableView):
    """
    Page Object for MGT operations
    """
    label_column = 1

    def __init__(self, driver):
        super(Mgt, self).__init__(driver)

        # Initialise elements on this page
        self.create_mgt_button = self.driver.find_element_by_css_selector('#btnNewMGT')
        self.mgt_configuration_list = '#mgt_configuration'
        self.datatable_id = 'mgt_configuration_content'

    def select_mgt(self, server_address, volume_name):
        self.volume_chooser_open_and_select('new_mgt_chooser', server_address, volume_name)

    def transition(self, primary_server_address, state):
        self.transition_by_column_values({2: primary_server_address}, state)

    def find_mgt_row(self, server_address):
        table = self.driver.find_element_by_css_selector('#%s' % self.datatable_id)
        return self.find_row_by_column_text(table, {2: server_address})

    def create_mgt(self, mgt_host_name, mgt_device_node):
        self.select_mgt(mgt_host_name, mgt_device_node)
        self.create_mgt_button.click()
        self.quiesce()
        wait_for_transition(self.driver, self.long_wait)

    def remove_mgt(self, mgt_host_name, mgt_device_node, transition_name):
        self.transition(self.mgt_host_name, self.mgt_device_node, transition_name)
