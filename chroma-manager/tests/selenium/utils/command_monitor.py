from selenium.webdriver.support.wait import WebDriverWait


def wait_for_commands_to_finish(driver, wait):
    return WebDriverWait(driver, wait).until_not(
        lambda driver: driver.find_element_by_css_selector('.command-in-progress'),
        'Timeout after %s seconds waiting for commands to complete' % wait)
