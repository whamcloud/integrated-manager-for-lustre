#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from utils.constants import wait_time
from base import wait_for_element
from base import wait_for_transition
from base import wait_for_datatable


class Mgt:
    """
    Page Object for MGT operations
    """
    def __init__(self, driver):
        self.driver = driver

        self.standard_wait = wait_time['standard']
        self.medium_wait = wait_time['medium']
        self.long_wait = wait_time['long']

        # Initialise elements on this page
        self.create_mgt_button = self.driver.find_element_by_css_selector('#btnNewMGT')
        self.mgt_configuration_list = '#mgt_configuration'
        self.mgt_list_datatable = 'mgt_configuration_content'

    def select_mgt(self, host_name, device_node):
        """Click storage button and select an MGT from chooser"""

        volume_chooser_selected = self.driver.find_elements_by_class_name("volume_chooser_selected")
        mgtchooser = volume_chooser_selected.__getitem__(0)
        mgtchooser.click()
        mgt_rows = self.driver.find_elements_by_xpath("id('new_mgt_chooser_table')/tbody/tr")
        for tr in mgt_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[1]").text == device_node:
                tr.click()
                return

        raise RuntimeError("Cannot choose MGT with host name: " + host_name + " and device node: " + device_node)

    def check_action_available(self, host_name, device_node, action_name):
        """Check whether the given transition(action) is present in all possible transitions available for MGT"""

        is_compared = False
        target_mgt_row = self.locate_mgt(host_name, device_node)
        buttons = target_mgt_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == action_name:
                is_compared = True

        return is_compared

    def verify_added_mgt(self, host_name, device_node):
        """Verify whether newly added MGT appears in the displayed MGT list"""

        mgt_rows = self.driver.find_elements_by_xpath("id('" + self.mgt_list_datatable + "')/tr")
        for tr in mgt_rows:
            if tr.find_element_by_xpath("td[5]").text == host_name and tr.find_element_by_xpath("td[2]").text == device_node:
                return True

        raise RuntimeError("Newly added MGT with host name: " + host_name + " and device node: " + device_node + " not found in list")

    def locate_mgt(self, host_name, device_node):
        """Locate MGT by host_name and device_node"""

        mgt_list = self.driver.find_elements_by_xpath("id('" + self.mgt_list_datatable + "')/tr")
        for tr in mgt_list:
            tds = tr.find_elements_by_tag_name("td")
            if host_name != '' and device_node != '':
                if tds[4].text == host_name and tds[1].text == device_node:
                    return tr

        raise RuntimeError("MGT with host name: " + host_name + " and device node:" + device_node + " not found in list")

    def transition(self, host_name, device_node, transition_name, transition_confirm = True):
        """Perform given transition on target MGT"""

        target_mgt_row = self.locate_mgt(host_name, device_node)
        buttons = target_mgt_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == transition_name:
                button.click()
                if transition_confirm:
                    # Confirm decision and wait the transition
                    wait_for_element(self.driver, '#transition_confirm_button', self.medium_wait)
                    self.driver.find_element_by_id('transition_confirm_button').click()

                # Wait for the transition to complete
                wait_for_transition(self.driver, self.standard_wait)
                return

        raise RuntimeError("Cannot perform transition " + transition_name + " for MGT with host " + host_name + " and device node " + device_node)

    def create_mgt(self, mgt_host_name, mgt_device_node):
        self.select_mgt(mgt_host_name, mgt_device_node)
        self.create_mgt_button.click()
        wait_for_datatable(self.driver, '#mgt_configuration')
        wait_for_transition(self.driver, self.long_wait)

    def remove_mgt(self, mgt_host_name, mgt_device_node, transition_name):
        self.transition(self.mgt_host_name, self.mgt_device_node, transition_name)
