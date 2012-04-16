#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from selenium.webdriver.support.ui import Select
from base import wait_for_element
import logging
from base import wait_for_datatable
from base import element_visible


class Volumes:
    """
    Page Object for volume configuration
    """
    def __init__(self, driver):
        self.driver = driver

        # Initialise elements on this page
        self.volume_configuration_datatable = 'volume_configuration_content'
        self.volume_error_dialog = '#volume_error_dialog'
        self.error_ok_button = '#error_ok_button'

        self.test_logger = logging.getLogger(__name__)
        self.test_logger.addHandler(logging.StreamHandler())
        self.test_logger.setLevel(logging.INFO)

    def check_volume_config_validation(self):
        """
        Checks validation on selecting same primary and failover server and
        verifies whether error message is displayed
        """

        volume_rows = self.driver.find_elements_by_xpath("id('" + self.volume_configuration_datatable + "')/tr")

        # Iterating through the rows of volume configuration table
        for i in range(len(volume_rows)):
            tr = volume_rows.__getitem__(i)
            select_tags = tr.find_elements_by_tag_name("select")

            # Get primary and failover 'select' dropdown elements
            primary_select = select_tags.__getitem__(0)
            failover_select = select_tags.__getitem__(1)

            if primary_select.is_enabled():
                primary_select_id = primary_select.get_attribute("id")
                secondary_select_id = failover_select.get_attribute("id")

                # Get all options of primary select box
                primary_options = primary_select.find_elements_by_tag_name('option')
                primary_option_values = [option.get_attribute('value') for option in primary_options]

                current_primary_value = Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).first_selected_option.get_attribute("value")

                # Select another option different from its original value from primary select dropdown
                for x in primary_option_values:
                    if int(x) != -1 and int(x) != int(current_primary_value):
                        Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).select_by_value(str(x))
                        break

                # Click Apply button
                self.driver.find_element_by_css_selector('#btnApplyConfig').click()
                wait_for_element(self.driver, self.volume_error_dialog, 10)

                primary_text = Select(self.driver.find_element_by_id(primary_select_id)).first_selected_option.text
                secondary_text = ''

                if secondary_select_id != '':
                    secondary_text = Select(self.driver.find_element_by_id(secondary_select_id)).first_selected_option.text

                # If selected text for primary and failover dropdowns are same then return display status of error dialog
                if primary_text == secondary_text:
                    return element_visible(self.driver, self.volume_error_dialog)

        raise RuntimeError("Primary and failover servers cannot be same for a particular volume")

    def change_volume_config(self):
        """Changing volume configuration"""

        volume_rows = self.driver.find_elements_by_xpath("id('" + self.volume_configuration_datatable + "')/tr")

        # Iterating through the rows of volume configuration table
        for i in range(len(volume_rows)):
            tr = volume_rows.__getitem__(i)
            select_tags = tr.find_elements_by_tag_name("select")
            primary_select = select_tags.__getitem__(0)
            failover_select = select_tags.__getitem__(1)

            # Get primary and failover 'select' dropdown elements
            original_primary_value = Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).first_selected_option.text
            original_secondary_value = ''
            if failover_select.get_attribute("id") != '':
                original_secondary_value = Select(self.driver.find_element_by_id(failover_select.get_attribute("id"))).first_selected_option.text

            if primary_select.is_enabled() and failover_select.is_enabled():
                primary_select_id = primary_select.get_attribute("id")
                secondary_select_id = failover_select.get_attribute("id")

                primary_options = primary_select.find_elements_by_tag_name('option')
                primary_option_values = [option.get_attribute('value') for option in primary_options]

                current_primary_value = Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).first_selected_option.get_attribute("value")

                # Select another option different from its original value for primary select dropdown
                for x in primary_option_values:
                    if int(x) != -1 and int(x) != int(current_primary_value):
                        Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).select_by_value(str(x))
                        break

                secondary_options = failover_select.find_elements_by_tag_name('option')
                secondary_option_values = [option.get_attribute('value') for option in secondary_options]

                current_secondary_value = Select(self.driver.find_element_by_id(failover_select.get_attribute("id"))).first_selected_option.get_attribute("value")

                # Select another option different from its original value for failover select dropdown
                for y in secondary_option_values:
                    if int(y) != -1 and int(y) != int(current_secondary_value):
                        Select(self.driver.find_element_by_id(failover_select.get_attribute("id"))).select_by_value(str(y))
                        break

                # Click Apply button
                self.driver.find_element_by_css_selector('#btnApplyConfig').click()

                # Get new values for primary and failover dropdowns
                primary_text = Select(self.driver.find_element_by_id(primary_select_id)).first_selected_option.text
                secondary_text = Select(self.driver.find_element_by_id(secondary_select_id)).first_selected_option.text

                # If texts are different then volume configuration setting should be successful and returns a success message
                if primary_text == secondary_text:
                    self.driver.find_element_by_css_selector(self.error_ok_button).click()
                    Select(self.driver.find_element_by_id(primary_select.get_attribute("id"))).select_by_visible_text(original_primary_value)
                    Select(self.driver.find_element_by_id(failover_select.get_attribute("id"))).select_by_visible_text(original_secondary_value)
                elif original_primary_value == current_primary_value and original_secondary_value == current_secondary_value:
                    pass
                else:
                    self.driver.find_element_by_css_selector('#transition_confirm_button').click()
                    wait_for_element(self.driver, "#popup_container", 10)
                    return self.driver.find_element_by_id('popup_message').text

        raise RuntimeError("No primary / failover servers available for changing volume configuration")

    def check_primary_volumes(self, server_name):
        """Checks whether primary volumes for given server appear or not"""
        wait_for_datatable(self.driver, '#volume_configuration')

        for i in xrange(10):
            volume_rows = self.driver.find_elements_by_xpath("id('" + self.volume_configuration_datatable + "')/tr")
            self.test_logger.info('Attempt ' + str(i + 1) + ' for checking volumes for server ' + server_name)

            # Iterating through the rows of volume configuration table
            for i in range(len(volume_rows)):
                tr = volume_rows.__getitem__(i)
                select_tags = tr.find_elements_by_tag_name("select")
                if len(select_tags) > 0:
                    primary_select = select_tags.__getitem__(0)
                    if primary_select.get_attribute("id") != '':
                        primary_options = primary_select.find_elements_by_tag_name('option')
                        primary_option_names = [option.text for option in primary_options]

                        # Check whether the given server is listed in primary server list for current volume
                        for option_value in primary_option_names:
                            if option_value == server_name:
                                return True

            self.driver.refresh()
            wait_for_datatable(self.driver, '#volume_configuration')

        return False
