from tests.selenium.base_view import BaseView
from tests.selenium.utils.navigation import Navigation
from tests.selenium.views.login import Login
from tests.selenium.utils.element import wait_for_element_by_css_selector


class Eula(BaseView):
    def __init__(self, driver):
        super(Eula, self).__init__(driver)

        self.modal_selector = '.eula-modal'
        self.modal_well_selector = '%s .well' % self.modal_selector
        self.accept_button_selector = '%s .btn-success' % self.modal_selector
        self.reject_button_selector = '%s .btn-danger' % self.modal_selector

        self.access_denied_modal_selector = '.access-denied-modal'

    def _work_with_eula(self, selector_to_click):
        eula_modal = wait_for_element_by_css_selector(self.driver, self.modal_selector, self.medium_wait)
        wait_for_selector = Login.login_selector

        if selector_to_click == self.accept_button_selector:
            script = "document.querySelector('%s').scrollTop = document.querySelector('%s').scrollHeight;" % (
                self.modal_well_selector, self.modal_well_selector
            )

            self.driver.execute_script(script)

            wait_for_selector = Login.logged_in_selector

        eula_modal.find_element_by_css_selector(selector_to_click).click()

        wait_for_element_by_css_selector(self.driver, wait_for_selector, self.long_wait)
        Navigation(self.driver)._patch_api()
        self.quiesce()

    def accept_eula(self):
        self.log.debug("Accepting Eula")
        self._work_with_eula(self.accept_button_selector)

    def reject_eula(self):
        self.log.debug("Rejecting Eula")
        self._work_with_eula(self.reject_button_selector)

    def is_eula_visible(self):
        try:
            wait_for_element_by_css_selector(self.driver, self.modal_selector, self.standard_wait)
            return True
        except RuntimeError:
            return False

    def is_access_denied_visible(self):
        try:
            wait_for_element_by_css_selector(self.driver, self.access_denied_modal_selector, self.short_wait)
            return True
        except RuntimeError:
            return False
