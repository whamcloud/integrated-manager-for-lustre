import time

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from tests.selenium.utils.constants import wait_time


def element_visible(element):
    try:
        if element.is_displayed():
            return True
        else:
            return False
    except StaleElementReferenceException:
        return False


def _find_visible_element(driver, by, selector):
    elements = driver.find_elements(by=by, value=selector)

    visible_elements = [e for e in elements if element_visible(e)]

    if not len(visible_elements):
        return None
    elif len(visible_elements) > 1:
        raise RuntimeError(
            "Selector %s matches %s visible elements! %s" % (
                selector,
                len(visible_elements),
                [get_xpath_for_element(driver, e) for e in visible_elements]
            )
        )
    else:
        return visible_elements[0]


def find_visible_element_by_css_selector(driver, selector):
    return _find_visible_element(driver, By.CSS_SELECTOR, selector)


def find_visible_element_by_xpath(driver, selector):
    return _find_visible_element(driver, By.XPATH, selector)


def _wait_for_element(driver, by, selector, timeout):
    for i in xrange(timeout):
        element = _find_visible_element(driver, by, selector)
        if element:
            return element

        time.sleep(1)
    raise RuntimeError("Timed out after %s seconds waiting for %s" % (timeout, selector))


def wait_for_element_by_css_selector(driver, selector, timeout):
    return _wait_for_element(driver, By.CSS_SELECTOR, selector, timeout)


def wait_for_element_by_xpath(driver, selector, timeout):
    return _wait_for_element(driver, By.XPATH, selector, timeout)


def _wait_for_any_element(driver, by, selectors, timeout):
    if isinstance(selectors, str) or isinstance(selectors, unicode):
        selectors = [selectors]

    for i in xrange(timeout):
        for selector in selectors:
            elements = driver.find_elements(by=by, value=selector)
            for element in elements:
                if element_visible(element):
                    return element
        time.sleep(1)

    raise RuntimeError("Timeout after %s seconds waiting for any of %s" % (timeout, selectors))


def wait_for_any_element_by_css_selector(driver, selectors, timeout):
    _wait_for_any_element(driver, By.CSS_SELECTOR, selectors, timeout)


def wait_for_any_element_by_xpath(driver, by, selectors, timeout):
    _wait_for_any_element(driver, by.XPATH, selectors, timeout)


def enter_text_for_element(driver, selector_or_element, text_value):
    if isinstance(selector_or_element, str) or isinstance(selector_or_element, unicode):
        element = driver.find_element_by_css_selector(selector_or_element)
    else:
        element = selector_or_element
    element.clear()
    element.send_keys(text_value)
    WebDriverWait(driver, wait_time['medium']).until(
        lambda driver: element.get_attribute('value') == text_value,
        "Expected the text {0} to be entered into the element in under {1} seconds, but instead found the text {2}"
        .format(text_value, wait_time['medium'], element.get_attribute('value'))
    )


def select_element_option(driver, selector, index):
    element = driver.find_element_by_css_selector(selector)
    select = Select(element)
    select.select_by_index(index)


def select_element_by_visible_text(driver, selector, text):
    element = driver.find_element_by_css_selector(selector)
    select = Select(element)
    select.select_by_visible_text(text)


def get_selected_option_text(driver, dropdown_element_selector):
    selectbox_element = Select(driver.find_element_by_css_selector(dropdown_element_selector))
    return selectbox_element.first_selected_option.text


def get_xpath_for_element(driver, element):
    get_xpath_js = """
        node = arguments[0];
        var stack = [];
        while(node.parentNode !== null) {
            node_string = node.tagName;
            if(node.id !== '') {
                node_string = node_string + "[@id='" + node.id + "']";
            } else if(node.className !== '') {
                node_string = node_string + "[@class='" + node.className + "']";
            }
            stack.unshift(node_string);
            node = node.parentNode;
        }
        return '/' + stack.join('/');
    """
    return driver.execute_script(get_xpath_js, element)
