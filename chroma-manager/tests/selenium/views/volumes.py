from tests.selenium.utils.select_box_it import SelectBoxIt
from tests.selenium.base_view import DatatableView
from tests.selenium.utils.element import (
    wait_for_element_by_css_selector, find_visible_element_by_css_selector
)


class Volumes(DatatableView):
    """
    Page Object for volume configuration
    """
    def __init__(self, driver):
        super(Volumes, self).__init__(driver)
        # Initialise elements on this page
        self.datatable_id = 'volume_configuration'
        self.volume_error_dialog = '#volume_error_dialog'
        self.error_ok_button = '#error_ok_button'

    def check_volume_config_validation(self):
        """
        Checks validation on selecting same primary and failover server and
        verifies whether error message is displayed
        """
        # Iterating through the rows of volume configuration table
        for tr in self.rows:
            selects = tr.find_elements_by_css_selector(SelectBoxIt.CONTAINER_SELECTOR)

            # Get primary and failover 'select' dropdown elements
            primary_select = SelectBoxIt(self.driver, selects[0])
            failover_select = SelectBoxIt(self.driver, selects[1])

            if not primary_select.is_disabled():
                current_primary_text = primary_select.get_selected()

                # Select another option different from its original value for primary select dropdown
                for primary_text in primary_select.get_options_text():
                    if primary_text != SelectBoxIt.BLANK_OPTION_TEXT and primary_text != current_primary_text:
                        primary_select.select_option(primary_text)
                        break

                new_primary_text = primary_select.get_selected()
                new_failover_text = failover_select.get_selected()

                # Click Apply button
                self.driver.find_element_by_css_selector('#btnApplyConfig').click()
                wait_for_element_by_css_selector(self.driver, self.volume_error_dialog, 10)

                # If selected text for primary and failover dropdowns are same then return display status of error dialog
                if new_primary_text == new_failover_text:
                    return find_visible_element_by_css_selector(self.driver, self.volume_error_dialog)

        raise RuntimeError("Primary and failover servers cannot be same for a particular volume")

    def set_primary_server(self, volume_name, primary_server_hostname):
        # Iterate through rows until find one with the right name and with that
        # server available
        for tr in self.rows:
            row_volume_name = tr.find_elements_by_tag_name('td')[0].text
            selects = tr.find_elements_by_css_selector(SelectBoxIt.CONTAINER_SELECTOR)
            primary_select = SelectBoxIt(self.driver, selects[0])
            failover_select = SelectBoxIt(self.driver, selects[1])

            if row_volume_name == unicode(volume_name):
                if primary_select.has_option(primary_server_hostname):
                    if not primary_select.is_selected(primary_server_hostname):
                        primary_select.select_option(primary_server_hostname)

                        # Pick another server for failover, if one is available, else set it blank (-1)
                        failover_options = failover_select.get_options_text()
                        failover_server_hostname = None
                        for option in failover_options:
                            if option != SelectBoxIt.BLANK_OPTION_TEXT and option != primary_server_hostname:
                                failover_server_hostname = option
                        if failover_server_hostname is None:
                            failover_select.select_option(SelectBoxIt.BLANK_OPTION_TEXT)
                        else:
                            failover_select.select_option(failover_server_hostname)

                        self.driver.find_element_by_css_selector('#btnApplyConfig').click()
                        wait_for_element_by_css_selector(self.driver, '#transition_confirm_button', 10)
                        self.driver.find_element_by_css_selector('#transition_confirm_button').click()
                        self.quiesce()

                    return

        debug_info = []
        for tr in self.rows:
            row_volume_name = tr.find_elements_by_tag_name('td')[0].text
            primary_select = SelectBoxIt(self.driver, tr.find_elements_by_css_selector(SelectBoxIt.CONTAINER_SELECTOR)[0])
            options_text = primary_select.get_options_text()
            debug_info.append((row_volume_name, options_text))

        raise RuntimeError("No row found with volume name '%s' that had server '%s' available to be selected as a primary server. Debug info: '%s'" % (volume_name, primary_server_hostname, debug_info))

    def change_volume_config(self):
        """Changing volume configuration"""
        # TODO: Lots of this needs refactored into the test_volumes module, where we can do proper asserts, etc.
        for tr in self.rows:
            selects = tr.find_elements_by_css_selector(SelectBoxIt.CONTAINER_SELECTOR)
            assert len(selects) == 2, selects
            primary_select = SelectBoxIt(self.driver, selects[0])
            primary_select_id = selects[0].get_attribute('id')
            failover_select = SelectBoxIt(self.driver, selects[1])
            failover_select_id = selects[1].get_attribute('id')

            if not primary_select.is_disabled() and not failover_select.is_disabled():
                # Get primary and failover 'select' dropdown elements
                original_primary_text = primary_select.get_selected()
                original_failover_text = failover_select.get_selected()

                # Select another option different from its original value for primary select dropdown
                for primary_text in primary_select.get_options_text():
                    if primary_text != SelectBoxIt.BLANK_OPTION_TEXT and primary_text != original_primary_text:
                        primary_select.select_option(primary_text)
                        break

                # Select another option different from its original value for failover select dropdown
                for failover_text in failover_select.get_options_text():
                    if failover_text != SelectBoxIt.BLANK_OPTION_TEXT and failover_text != original_failover_text:
                        failover_select.select_option(failover_text)

                new_primary_text = primary_select.get_selected()
                new_failover_text = failover_select.get_selected()

                # Click Apply button
                self.driver.find_element_by_css_selector('#btnApplyConfig').click()

                # If texts are different then volume configuration setting should be successful and returns a success message
                if new_primary_text == new_failover_text:
                    self.driver.find_element_by_css_selector(self.error_ok_button).click()
                    primary_select.select_option(original_primary_text)
                    failover_select.select_option(original_failover_text)
                else:
                    self.driver.find_element_by_css_selector('#transition_confirm_button').click()
                    self.quiesce()

                    # Verify values persist through a refresh
                    self.driver.refresh()
                    self.quiesce()

                    stored_primary_text = SelectBoxIt(self.driver, self.driver.find_element_by_id(primary_select_id)).get_selected()
                    stored_failover_text = SelectBoxIt(self.driver, self.driver.find_element_by_id(failover_select_id)).get_selected()

                    assert stored_primary_text == new_primary_text, "%s != %s" % (
                        stored_primary_text, new_primary_text)
                    assert stored_failover_text == new_failover_text, "%s != %s" % (
                        stored_failover_text, new_failover_text)
                    return True

        raise RuntimeError("No primary / failover servers available for changing volume configuration")

    def check_primary_volumes(self, server_name):
        """Checks whether primary volumes for given server appear or not"""
        # Iterating through the rows of volume configuration table
        for tr in self.rows:
            selects = tr.find_elements_by_css_selector(SelectBoxIt.CONTAINER_SELECTOR)
            if len(selects) > 0:
                primary_select = SelectBoxIt(self.driver, selects[0])

                # Check whether the given server is listed in primary server list for current volume
                if not primary_select.is_disabled():
                    for primary_text in primary_select.get_options_text():
                        if primary_text == server_name:
                            return True

        return False
