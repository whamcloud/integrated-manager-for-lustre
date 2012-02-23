"""Page Object for server operations"""
from utils.constants import Constants
from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException


class Servers:
    """ Page Object for server operations
    """
    def __init__(self, driver):
        self.driver = driver
        #Initialise the constants class
        constants = Constants()
        self.WAIT_TIME = constants.wait_time['standard']
        # Initialise all elements on that view.
        self.new_add_server_button = self.driver.find_element_by_id('btnAddNewHost')
        self.host_continue_button = self.driver.find_element_by_class_name('add_host_submit_button')
        self.add_host_confirm_button = self.driver.find_element_by_class_name('add_host_confirm_button')
        self.add_host_close_button = self.driver.find_element_by_class_name('add_host_close_button')

        self.add_dialog_div = self.driver.find_element_by_id('add_host_dialog')
        self.prompt_dialog_div = self.driver.find_element_by_id('add_host_prompt')
        self.loading_dialog_div = self.driver.find_element_by_id('add_host_loading')
        self.confirm_dialog_div = self.driver.find_element_by_id('add_host_confirm')
        self.complete_dialog_div = self.driver.find_element_by_id('add_host_complete')
        self.error_dialog_div = self.driver.find_element_by_id('add_host_error')

        self.host_address_text = self.driver.find_element_by_id('add_host_address')

    def click_new_server_add_button(self):
        #Click add server button
        self.new_add_server_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(2)

    def enter_hostname(self, host_name):
        """Enter hostname"""
        self.host_address_text.clear()
        self.host_address_text.send_keys(host_name)

    def click_continue_button(self):
        #Click continue button
        self.host_continue_button.click()
        # FIXME: need to add a generic function to wait for an action

        loading_div = self.driver.find_element_by_class_name('loading_placeholder')
        for i in xrange(self.WAIT_TIME):
            if self.loading_dialog_div.is_displayed() and loading_div.text == 'Checking connectivity...':
                print "Checking connectivity"
                sleep(2)
            else:
                break

    def loading_div_displayed(self):
        """Returns whether loading div is displayed or not"""
        self.loading_dialog_div.is_displayed()
        sleep(2)

    def confirm_div_displayed(self):
        """Returns whether confirm div is displayed or not"""
        return self.confirm_dialog_div.is_displayed()

    def click_confirm_button(self):
        #Click add server button
        self.add_host_confirm_button.click()
        # FIXME: need to add a generic function to wait for an action
        sleep(5)
        self.test_loading_image()

    def complete_div_displayed(self):
        """Returns whether complete div is displayed or not"""
        return self.complete_dialog_div.is_displayed()

    def click_close_button(self):
        #Click close button
        self.add_host_close_button.click()
        sleep(2)

    def verify_added_server(self, host_name):
        """Returns whether newly created server is listed or not"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    return True
        return False

    def get_server_list_length(self):
        """Returns whether newly created server is listed or not"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        return len(server_list)

    def stop_lnet(self, host_name):
        """Stops LNet on the server"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    stop_lnet_button = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[3]/span/button[3]")
                    stop_lnet_button.click()
                    self.test_loading_image()

    def start_lnet(self, host_name):
        """Stops LNet on the server"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    start_lnet_button = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[3]/span/button[1]")
                    start_lnet_button.click()
                    self.test_loading_image()

    def unload_lnet(self, host_name):
        """Unloads LNet on the server"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    unload_lnet_button = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[3]/span/button[2]")
                    unload_lnet_button.click()
                    self.test_loading_image()

    def load_lnet(self, host_name):
        """Loads LNet on the server"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    load_lnet_button = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[3]/span/button[3]")
                    load_lnet_button.click()
                    self.test_loading_image()

    def remove_lnet(self, host_name):
        """Removes server"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    remove_lnet_button = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[3]/span/button[2]")
                    remove_lnet_button.click()
                    sleep(5)
                    self.driver.find_element_by_id('transition_confirm_button').click()
                    self.test_loading_image()

    def get_lnet_state(self, host_name):
        """Returns LNet state"""
        server_list = self.driver.find_elements_by_xpath("id('server_configuration_content')/tr/td[1]")
        lnet_state_text = ''
        if len(server_list) > 0:
            for i in range(len(server_list)):
                if server_list.__getitem__(i).text == host_name:
                    lnet_state = self.driver.find_element_by_xpath("id('server_configuration_content')/tr[" + str(i + 1) + "]/td[2]/span")
                    lnet_state_text = lnet_state.text

        return lnet_state_text

    def test_loading_image(self):
        from time import sleep
        for i in xrange(10):
            print "Retrying attempt: " + str(i)
            try:
                loading_div = self.driver.find_element_by_css_selector("span.notification_object_icon.busy_icon")
                try:
                    if loading_div.is_displayed():
                        print "Waiting for process to get complete"
                        sleep(2)
                        continue
                except StaleElementReferenceException:
                    sleep(2)
                    return
            except NoSuchElementException:
                sleep(2)
                return
