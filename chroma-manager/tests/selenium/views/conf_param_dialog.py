

from selenium.common.exceptions import NoSuchElementException
from tests.selenium.base import enter_text_for_element, wait_for_element
from tests.selenium.base_view import BaseView


class ConfParamDialog(BaseView):
    def _get_conf_param_input(self, conf_param):
        return self.get_visible_element_by_css_selector("input[id='conf_param_" + conf_param + "']")

    def set_conf_params(self, target_conf_params):
        """Given that a conf param dialog is open, enter values from a dict"""
        for param in target_conf_params:
            self.log.info('Setting value for param name:' + param + " value:" + target_conf_params[param])
            enter_text_for_element(self.driver, self._get_conf_param_input(param), target_conf_params[param])

    def get_conf_param_error(self, conf_param):
        """Check for an error notification on the input for a particular parameter"""
        try:
            return self.get_input_error(self._get_conf_param_input(conf_param))
        except NoSuchElementException:
            return None

    def enter_conf_params(self, conf_params):
        for param in conf_params:
            self.log.info('Setting value for param name:' + param + " value:" + conf_params[param])
            param_element_id = 'conf_param_' + param
            wait_for_element(self.driver, "input[id='" + param_element_id + "']", self.medium_wait)
            enter_text_for_element(self.driver, "input[id='" + param_element_id + "']", conf_params[param])

    def check_conf_params(self, target_conf_params):
        for param, expected in target_conf_params.items():
            param_element_id = 'conf_param_' + param
            element = self.get_visible_element_by_css_selector("input[id='" + param_element_id + "']")
            actual = element.get_attribute("value")
            if expected != actual:
                raise RuntimeError("Conf param doesn't match ('%s' should be '%s')" % (actual, expected))
