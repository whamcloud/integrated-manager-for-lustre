#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from utils.constants import wait_time
from base import wait_for_element
from base import wait_for_transition


class Filesystem:
    """
    Page Object for file system operations
    """
    def __init__(self, driver):
        self.driver = driver

        self.medium_wait = wait_time['medium']
        self.standard_wait = wait_time['standard']

        self.filesystem_name_td = 0
        self.filesystem_datatable = 'fs_list'

    def locate_filesystem(self, filesystem_name):
        filesystem_list = self.driver.find_elements_by_xpath("id('" + self.filesystem_datatable + "')/tbody/tr")
        for tr in filesystem_list:
            tds = tr.find_elements_by_tag_name("td")
            if tds[self.filesystem_name_td].text == filesystem_name:
                return tr

        raise RuntimeError("File system: " + filesystem_name + " not found in file system list")

    def transition(self, filesystem_name, transition_name, transition_confirm = True):
        """Perform given transition on target filesystem"""

        target_filesystem_row = self.locate_filesystem(filesystem_name)
        buttons = target_filesystem_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == transition_name:
                button.click()
                if transition_confirm:
                    wait_for_element(self.driver, '#transition_confirm_button', self.medium_wait)
                    self.driver.find_element_by_css_selector('#transition_confirm_button').click()
                wait_for_transition(self.driver, self.standard_wait)
                return

        raise RuntimeError("Cannot perform transition " + transition_name + " on filesystem " + filesystem_name)

    def check_action_available(self, fs_name, action_name):
        """Check whether the given transition(action) is present in all possible transitions available for the filesystem"""
        target_filesystem_row = self.locate_filesystem(fs_name)
        buttons = target_filesystem_row.find_elements_by_tag_name("button")
        for button in buttons:
            if button.text == action_name:
                raise RuntimeError("Error in File system while performing operation: " + action_name)

        return True

    def edit(self, fs_name):
        """Click filesystem name to be edited"""

        target_filesystem_row = self.locate_filesystem(fs_name)
        target_filesystem_row.find_element_by_xpath("td[1]/a").click()

    def get_filesystem_list(self):
        """Returns file system name list"""
        fs_list = self.driver.find_elements_by_xpath("id('fs_list')/tbody/tr/td[1]/a")
        filtered_filesystem_list = []

        # Get actual display text from list of webelement objects, append the names to a new list and sort the new list
        for count in range(len(fs_list)):
            filtered_filesystem_list.append(fs_list.__getitem__(count).text)
        filtered_filesystem_list.sort()
        return filtered_filesystem_list
