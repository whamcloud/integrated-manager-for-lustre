from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import element_to_be_clickable
from selenium.webdriver.common.by import By

from tests.selenium.base_view import BaseView

from tests.selenium.utils.constants import wait_time
from tests.selenium.utils.element import enter_text_for_element
from tests.selenium.utils.fancy_select import FancySelect


class Modal(BaseView):
    @property
    def modal(self):
        return self.driver.find_element_by_css_selector(self.MODAL)

    @property
    def modal_backdrop(self):
        return self.driver.find_element_by_css_selector(self.MODAL_BACKDROP)

    def wait_for_modal(self, wait=wait_time['medium']):
        return WebDriverWait(self, wait).until(lambda modal: modal.modal)

    def wait_for_modal_remove(self):
        def is_removed(obj, prop_name):
            try:
                getattr(obj, prop_name)
            except NoSuchElementException:
                return True

        return WebDriverWait(self, self.medium_wait).until(
            lambda modal: is_removed(modal, 'modal') and is_removed(modal, 'modal_backdrop'),
            "Modal still present after %s seconds." % self.medium_wait)

    def modal_is_displayed(self):
        return self.modal.is_displayed()


class CommandModal(Modal):
    MODAL = '.command-modal'
    MODAL_BACKDROP = '.command-modal-backdrop'
    CLOSE_BUTTON = '%s .btn-danger' % MODAL

    @property
    def close_button(self):
        return self.driver.find_element_by_css_selector(self.CLOSE_BUTTON)

    def wait_for_close_button_to_be_clickable(self):
        return WebDriverWait(self.driver, self.medium_wait).until(
            element_to_be_clickable((By.CSS_SELECTOR, self.CLOSE_BUTTON)), 'Close button not clickable.')


class ConfirmActionModal(Modal):
    MODAL = '.confirm-action-modal'
    MODAL_BACKDROP = '.confirm-action-modal-backdrop'
    CONFIRM_BUTTON = '%s .btn-success' % MODAL

    @property
    def confirm_button(self):
        return self.driver.find_element_by_css_selector(self.CONFIRM_BUTTON)


class AddServerModal(Modal):
    MODAL = '.add-server-modal'
    MODAL_BACKDROP = '.add-server-modal-backdrop'
    MODAL_BODY = '%s .modal-body' % MODAL
    SELECT_SERVER_PROFILE_STEP = '%s .select-server-profile-step' % MODAL
    OVERRIDE_BUTTON = '%s .override' % MODAL
    PROCEED_BUTTON = '%s .proceed button' % MODAL
    HOST_ADDRESS_TEXT = '%s .pdsh-input input' % MODAL
    SUCCESS_BUTTON = '%s .btn-success' % MODAL

    @property
    def override_button(self):
        return self.driver.find_element_by_css_selector(self.OVERRIDE_BUTTON)

    @property
    def proceed_button(self):
        return self.driver.find_element_by_css_selector(self.PROCEED_BUTTON)

    def wait_for_proceed_enabled(self):
        def wait_for_enabled(add_server_modal):
            try:
                return add_server_modal.proceed_button.is_enabled()
            except StaleElementReferenceException:
                return False

        return WebDriverWait(self, self.medium_wait).until(wait_for_enabled)

    def submit_address(self):
        self.driver.find_element_by_css_selector(self.SUCCESS_BUTTON).click()
        self.wait_for_angular()

    def select_profile(self, profile_text='Managed storage server'):
        self.wait_for_angular()
        profile_select = FancySelect(self.driver, self.SELECT_SERVER_PROFILE_STEP)
        profile_select.select_option(profile_text)

    def submit_profile(self):
        try:
            self.override_button.click()
        except NoSuchElementException:
            pass

        self.proceed_button.click()
        self.wait_for_angular()

    def enter_address(self, host_name):
        self.wait_for_angular()
        enter_text_for_element(self.driver, self.HOST_ADDRESS_TEXT, host_name)

        script = """
            var callback = arguments[arguments.length - 1];

            if (hasScopeUpdated())
              callback(true);
            else
              retry(30);

            function retry (n) {
                if (hasScopeUpdated())
                  callback(true);
                else if (n < 1)
                   callback(false);
                else
                  window.setTimeout(function () { retry(n - 1); }, 1000);
            };

            function hasScopeUpdated () {
              return $('%s').scope().addServer.fields.pdsh === '%s';
            }
        """ % (self.MODAL_BODY, host_name)

        return self.driver.execute_async_script(script)
