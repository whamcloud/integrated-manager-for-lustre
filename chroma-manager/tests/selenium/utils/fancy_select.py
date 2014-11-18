from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.wait import WebDriverWait


class FancySelect(object):
    def __init__(self, driver, container_selector):
        self.driver = driver
        self.container_selector = container_selector

    SELECT_BUTTON = '.fancy-select-box button'
    OPTION_CLASS = 'fancy-select-option'
    TEXT_CLASS = 'fancy-select-text'

    @property
    def select_container(self):
        return self.driver.find_element_by_css_selector(self.container_selector)

    @property
    def select(self):
        return self.select_container.find_element_by_css_selector(self.SELECT_BUTTON)

    @property
    def options(self):
        return self.select_container.find_elements_by_class_name(self.OPTION_CLASS)

    def click_select(self):
        self.select.click()

    def select_option(self, option_text):
        self.click_select()

        option = next(option for option in self.options
                      if option.find_element_by_class_name(self.TEXT_CLASS).text == option_text)

        option.click()

    def wait_for_profiles(self, container):
        def wait_on_profiles(modal):
            try:
                return len(self.options) > 0
            except StaleElementReferenceException:
                return False

        return WebDriverWait(container, container.medium_wait).until(
            wait_on_profiles,
            "Select Server Profile options not available.")
