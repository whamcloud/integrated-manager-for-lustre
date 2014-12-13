'use strict';

var format = require('util').format;
var config = require('../config');
var _ = require('lodash');
var fancySelect = require('./fancy-select');
var isRemoved = require('../util/is-removed');
var msToSec = require('../util/time').msToSec;

var modal = {
  get modal () {
    return $(this.MODAL);
  },
  get modalBackdrop () {
    return $(this.MODAL_BACKDROP);
  },
  modalIsDisplayed: function modalIsDisplayed () {
    return this.modal.isDisplayed();
  },
  /**
   * Wait for a modal to be present.
   * @param {Number} [waitTime]
   */
  waitForModal: function waitForModal (waitTime) {

    waitTime = waitTime || config.wait_time.medium;

    var that = this;

    browser.wait(
      waitOnModal,
      waitTime,
      format('Modal[%j] still present after %d seconds', that.MODAL, msToSec(waitTime))
    );

    /**
     * Wait for the modal.
     * @returns {Object}
     */
    function waitOnModal () {
      return browser.isElementPresent(that.modal);
    }

  },
  /**
   * Wait for the removal of any modal that has it's prototype
   * pointing to this object literal.
   * @param {Number} waitTime
   */
  waitForModalRemove: function waitForModalRemove (waitTime) {

    waitTime = waitTime || config.wait_time.medium;

    var modalIsRemoved = isRemoved(this.modal);

    browser.wait(
      modalIsRemoved,
      waitTime,
      format('Modal[%s] still present after %d seconds', this.MODAL, msToSec(waitTime))
    );
  }
};

var addServerModal = Object.create(modal);
_.extend(addServerModal, {
  get PDSH_EXPRESSION () {

    return config.lustre_servers.reduce(buildPdshExpression, '');

    /**
     * Combine all the nodenames into one expression.
     * @param {String} prev
     * @param {Object} curr
     * @param {Number} idx
     * @returns {String}
     */
    function buildPdshExpression (prev, curr, idx) {
      if (idx === 0)
        return curr.nodename;
      else
        return prev + ',' + curr.nodename;
    }
  },
  MODAL: '.add-server-modal',
  MODAL_BACKDROP: '.add-server-modal-backdrop',
  get MODAL_BODY () {
    return format('%s .modal-body', addServerModal.MODAL);
  },
  get SELECT_SERVER_PROFILE_ () {
    return format('%s .select-server-profile-step', addServerModal.MODAL);
  },
  get OVERRIDE_BUTTON () {
    return format('%s .override', addServerModal.MODAL);
  },
  get PROCEED_BUTTON () {
    return format('%s .proceed button i', addServerModal.MODAL);
  },
  get HOST_ADDRESS_TEXT () {
    return format('%s .pdsh-input input', addServerModal.MODAL);
  },
  get SUCCESS_BUTTON () {
    return format('%s .btn-success', addServerModal.MODAL);
  },
  get overrideButton () {
    return $(addServerModal.OVERRIDE_BUTTON);
  },
  get proceedButton () {
    return $(addServerModal.PROCEED_BUTTON);
  },
  get successButton () {
    return $(addServerModal.SUCCESS_BUTTON);
  },
  /**
   * Wait for the proceed button to be enabled.
   */
  waitForProceedEnabled: function waitForProceedEnabled () {
    function waitOnProceedButton () {
      return browser.isElementPresent(addServerModal.proceedButton)
        .then(function isProceedPresentThen (isProceedPresent) {
          return isProceedPresent;
        });
    }

    browser.wait(waitOnProceedButton, config.wait_time.medium);
  },
  get hostAddressText () {
    return element(by.css(addServerModal.HOST_ADDRESS_TEXT));
  },
  enterAddress: function enterAddress () {

    addServerModal.hostAddressText.sendKeys(addServerModal.PDSH_EXPRESSION);

    addServerModal.waitForAddress();

  },
  waitForAddress: function waitForAddress () {

    function waitOnAddressToBeFullyEntered () {
      return addServerModal.hostAddressText.getAttribute('value')
        .then(function checkInputValueMatchesPdshExpression (text) {
          if (text === addServerModal.PDSH_EXPRESSION)
            return true;
        });
    }

    browser.wait(
      waitOnAddressToBeFullyEntered,
      config.wait_time.medium,
      format('Still waiting for the host address input to be %s after %d seconds',
        addServerModal.PDSH_EXPRESSION, msToSec(config.wait_time.medium))
    );
  },
  submitAddress: function submitAddress () {
    return addServerModal.successButton.click();
  },
  selectProfile: function selectProfile () {
    fancySelect.selectOption();
  },
  submitProfile: function submitProfile () {
    addServerModal.overrideButton.click();
    addServerModal.proceedButton.click();
  }
});

var commandModal = Object.create(modal);
_.extend(commandModal, {
  MODAL: '.command-modal',
  MODAL_BACKDROP: '.command-modal-backdrop',
  get CLOSE_BUTTON () {
    return format('%s .btn-danger', commandModal.MODAL);
  },
  get closeButton () {
    return $(commandModal.CLOSE_BUTTON);
  },
  waitForCloseButtonToBeClickable: function waitForCloseButtonToBeClickable () {
    function waitOnCloseButton () {
      return browser.isElementPresent(commandModal.closeButton);
    }

    browser.wait(waitOnCloseButton, config.wait_time.medium);
  }
});

var confirmActionModal = Object.create(modal);
_.extend(confirmActionModal, {
  MODAL: '.confirm-action-modal',
  MODAL_BACKDROP: '.confirm-action-modal-backdrop',
  get CONFIRM_BUTTON () {
    return format('%s .btn-success i:not(dropdown-toggle)', confirmActionModal.MODAL);
  },
  get confirmButton () {
    return $(confirmActionModal.CONFIRM_BUTTON);
  }
});

var serverDetailModal = Object.create(modal);
_.extend(serverDetailModal, {
  MODAL: '.server-detail-modal'
});

module.exports = {
  commandModal: commandModal,
  addServerModal: addServerModal,
  confirmActionModal: confirmActionModal
};
