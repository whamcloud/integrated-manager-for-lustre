(function () {
  'use strict';

  var BaseView = require('./base.js').BaseView,
    eulaLocators = require('../selectors/eula').locators,
    eulaSelectors = require('../selectors/eula').selectors;

  BaseView.extend(EulaView);

  function EulaView () {
    this.one = {
      well: eulaLocators.WELL,
      acceptButton: eulaLocators.ACCEPT,
      rejectButton: eulaLocators.REJECT
    };

    BaseView.call(this);
    this.path = 'login';
  }


  EulaView.prototype.accept = function accept() {
    this.ptor.waitForAngular();

    this.ptor.executeScript(function (wellSelector) {
      var well = document.querySelector(wellSelector);

      well.scrollTop = well.scrollHeight;
    }, eulaSelectors.WELL);

    this.ptor.wait(function () {
    }, 5000);
  };


  module.exports = new EulaView();
}());
