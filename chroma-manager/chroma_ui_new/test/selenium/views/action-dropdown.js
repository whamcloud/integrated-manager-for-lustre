'use strict';

var format = require('util').format;
var modalView = require('./modal');
var confirmActionModal = modalView.confirmActionModal;
var commandModal = modalView.commandModal;
var commandMonitor = require('../util/command-monitor');
var config = require('../config');
var msToSec = require('../util/time').msToSec;

/**
 * Gets an instance of an Actions Dropdown, tied to a specific server row.
 * @param {Object} dropdownContainer A server table row.
 * @returns {Object}
 */
function actionDropdownFactory (dropdownContainer) {

  var instance = {
    DROPDOWN: '.action-dropdown',
    get DROPDOWN_BUTTON () {
      return format('%s button', instance.DROPDOWN);
    },
    get DROPDOWN_MENU () {
      return format('%s .dropdown-menu', instance.DROPDOWN);
    },
    get dropdownButton () {
      return dropdownContainer.$(instance.DROPDOWN_BUTTON);
    },
    get dropdownMenu () {
      return dropdownContainer.$(instance.DROPDOWN_MENU);
    },
    /**
     * Click on action links a server row's Actions dropdown.
     * @param {String} actionName Name of the action (link) in the actions dropdown that we want
     * to invoke.
     */
    clickAction: function clickAction (actionName) {
      commandMonitor.waitForCommandsToFinish(config.wait_time.long);

      instance.waitForDropdownEnabled();

      instance.dropdownButton.click();

      instance.dropdownMenu.all(by.tagName('a'))
        .filter(function findItemsThatMatchAction (item) {
          return item.getInnerHtml()
            .then(function testForMatch (text) {
              return text === actionName;
            });
        })
        .then(function clickFiltered (filtered) {
          filtered[0].click();
        })
        .then(function checkForConfirm () {
          // If the action name was remove or shutdown, wait for it to complete.
          if ((actionName.indexOf('Remove') !== -1) || (actionName.indexOf('Shutdown') !== -1))
            confirmActionModal.waitForModal();

        })
        .then(function finish () {
          browser.isElementPresent(confirmActionModal.modal)
            .then(function isConfirmActionModalPresentThen (isPresent) {

              if (isPresent)
                confirmActionModal.confirmButton.click();

            })
            .then(function processCommandModal () {
              commandModal.waitForModal();
              commandModal.waitForCloseButtonToBeClickable();
              commandModal.closeButton.click();
              commandModal.waitForModalRemove(config.wait_time.medium);
            })
            .then(function processConfirmation () {

              browser.isElementPresent(confirmActionModal.modal)
                .then(function isConfirmActionModalPresentThen (isPresent) {

                  if (isPresent)
                    confirmActionModal.waitForModalRemove(config.wait_time.medium);

                });

            })
            .then(function waitForCommands () {
              commandMonitor.waitForCommandsToFinish(config.wait_time.long);
            });
        });

    },
    /**
     * Wait for this object's dropdown to be enabled.
     */
    waitForDropdownEnabled: function waitForDropdownEnabled () {

      browser.wait(
        instance.dropdownButton.isEnabled,
        config.wait_time.long,
        format('Timeout after %d seconds waiting for dropdown to be enabled', msToSec(config.wait_time.long))
      );

    }
  };

  return instance;
}

module.exports = actionDropdownFactory;
