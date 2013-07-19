from selenium.webdriver.support.wait import WebDriverWait
from tests.selenium.base_view import BaseView


class Eula(BaseView):
    path = BaseView.path + "login/"

    well_selector = ".well"

    @property
    def modal(self):
        return self.driver.find_element_by_class_name("eula-modal")

    @property
    def modal_background(self):
        return self.driver.find_element_by_class_name("modal-backdrop")

    @property
    def well(self):
        return self.modal.find_element_by_css_selector(self.well_selector)

    @property
    def accept_button(self):
        return self.modal.find_element_by_class_name("btn-success")

    @property
    def reject_button(self):
        return self.modal.find_element_by_class_name("btn-danger")

    @property
    def access_denied(self):
        return self.driver.find_element_by_class_name("access-denied-modal")

    def accept(self, must_accept=False):
        """
        Scrolls the eula div and accepts.
        @param must_accept: should this method fail if the eula does not appear in time or we change pages?
        """
        self.log.debug("Accepting eula if presented.")
        self.wait_for_angular()

        # Wait for the page to change or the modal to appear.
        WebDriverWait(self, self.short_wait).until(
            lambda eula: not self.on_page() or eula.modal,
            "The eula modal was not found!"
        )

        # If we reach here and must accept then the page has changed when we did not want it to.
        if must_accept:
            raise RuntimeError("Page navigated without displaying eula!")

        if not self.on_page():
            return

        script = "document.querySelector('%s').scrollTop = document.querySelector('%s').scrollHeight;" % (
            self.well_selector, self.well_selector
        )

        self.driver.execute_script(script)
        self.accept_button.click()

        # Wait for calls to finish
        self.wait_for_angular()

    def reject(self):
        """
        Rejects the eula.
        """
        self.log.debug("Rejecting Eula")
        self.wait_for_angular()

        WebDriverWait(self, self.short_wait).until(lambda eula: eula.modal, "The eula modal was not found!")

        self.reject_button.click()

        # Wait for calls to finish
        self.wait_for_angular()

    def denied(self):
        """
        Waits for the denied modal to appear then refreshes the page.
        """
        self.log.debug("User Denied")
        self.wait_for_angular()

        WebDriverWait(self, self.short_wait).until(lambda eula: eula.access_denied,
                                                   "The access denied modal was not found!")

        from tests.selenium.utils.navigation import Navigation
        Navigation(self.driver, False).refresh(True)
