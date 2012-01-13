"""Unit Testing code for the chroma UI
"""

# Import system modules
import unittest

# Import third-party modules
from selenium import webdriver

from utils.constants import Constants
from testparameters import CHROMA_URL
from testparameters import TEST_BROWSER


class BaseClass(unittest.TestCase):
    """This is the base class for the test classes.
    The setUp() method is called during the
    initialization process. The tearDown() method is called
    irrespective of the status of the application.
    """
    driver = None

    def setUp(cls):
        if not cls.driver:
            if TEST_BROWSER == "Chrome":
                cls.driver = webdriver.Chrome()
            elif TEST_BROWSER == "Firefox":
                cls.driver = webdriver.Firefox()

        constants = Constants()
        cls.wait_time = constants.get_wait_time('standard')
        cls.long_wait_time = constants.get_wait_time('long')
        cls.driver.get(CHROMA_URL)

    def tearDown(cls):
        cls.driver.close()
