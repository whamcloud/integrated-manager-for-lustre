(function () {
  'use strict';

  var BaseView = require('./base.js').BaseView,
    eulaLocators = require('../selectors/eula').locators,
    eulaSelectors = require('../selectors/eula').selectors;

  BaseView.extend(EulaView);

  /**
   * Represents the eula dialog in the ui.
   * @constructor
   */
  function EulaView () {
    this.one = {
      well: eulaLocators.WELL,
      acceptButton: eulaLocators.ACCEPT,
      rejectButton: eulaLocators.REJECT
    };

    BaseView.call(this);
    this.path = 'login';
  }

  /**
   * Accepts the eula if it appears, otherwise continues on.
   */
  EulaView.prototype.accept = function accept() {
    var self = this;

    this.ptor.waitForAngular();

    this.ptor.wait(function detectNextStep() {
      return !self.onPage() || self.well.isDisplayed();
    }, 30000);

    if (!this.onPage()) return;

    this.ptor.executeScript(function (wellSelector) {
      var well = document.querySelector(wellSelector);

      well.scrollTop = well.scrollHeight;
    }, eulaSelectors.WELL);

    this.acceptButton.click();
  };


  module.exports = new EulaView();
}());
