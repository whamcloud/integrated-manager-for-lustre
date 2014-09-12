'use strict';

var format = require('util').format;
var manager = require('../util/manager');
var msToSec = require('../util/time').msToSec;

var fancySelect;

module.exports = fancySelect = {
  DROP_DOWN: 'button i.fa.fa-caret-up',
  OPTION_CLASS: '.fancy-select-option',
  TEXT_CLASS: '.fancy-select-text',
  PROFILE_NAME: 'Managed Storage Server',
  get dropdown () {
    return $(fancySelect.DROP_DOWN);
  },
  get options () {
    return element.all(by.css(fancySelect.OPTION_CLASS));
  },
  /**
   * Open the dropdown, and click on desired option.
   * @param {String} [optionText]
   */
  selectOption: function selectOption (optionText) {

    optionText = optionText || fancySelect.PROFILE_NAME;

    browser.wait(waitForDropdown,
      manager.waitTimes.short,
      format('Server table[%j] not present after %d seconds', fancySelect.DROP_DOWN, msToSec(manager.waitTimes.short)));

    /**
     * Wait for the dropdown.
     * @returns {Object}
     */
    function waitForDropdown () {
      return browser.isElementPresent(fancySelect.dropdown);
    }

    fancySelect.dropdown
      .then(function openFancySelectDropdown (fancySelectArrow) {
        fancySelectArrow.click();
      })
      .then(function filterOutOptionsNonMatches () {

        fancySelect.options
          .filter(function findRequestedOptionByText (optionElement) {

            return optionElement.getText()
              .then(function getMatchedOption (text) {

                return text.indexOf(optionText) !== -1;

              });

          })
          .then(function clickTheMatchedElement (matchedOptions) {
            matchedOptions[0].click();
          });

      });

  }
};
