'use strict';

/**
 * HOF. Returns a function that returns true if the element arg is
 * no longer on the page.
 * @param {Object} element
 * @returns {Function}
 */
module.exports = function isRemoved (element) {
  return function innerIsRemoved () {
    return browser.isElementPresent(element)
      .then(function isPresentThen (isPresent) {
        return !isPresent;
      });
  };
};
