(function () {
  'use strict';

  var BaseView = require('./base.js').BaseView,
  navBarLocators = require('../selectors/nav-bar.js').locators;

  BaseView.extend(NavBarView);

  /**
   * Represents the nav bar in the ui.
   * @constructor
   */
  function NavBarView () {
    this.one = {
      navBar: navBarLocators.NAV_BAR,
      loginToggle: navBarLocators.LOGIN_TOGGLE,
      logoutButton: navBarLocators.LOGOUT_BUTTON,
      loginButton: navBarLocators.LOGIN_BUTTON
    };

    BaseView.call(this);
    this.path = '';
  }

  module.exports = new NavBarView();
}());
