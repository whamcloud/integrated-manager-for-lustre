(function () {
  'use strict';


  function Selectors() {
    this.NAV_BAR = '.navbar';

    this.LOGIN_TOGGLE = this.NAV_BAR + ' .login-toggle';

    this.LOGOUT_BUTTON = this.LOGIN_TOGGLE + '.logout';

    this.LOGIN_BUTTON = this.LOGIN_TOGGLE + '.login';
  }

  var selectors = Object.freeze(new Selectors());

  function Locators() {
    this.NAV_BAR = protractor.By.css(selectors.NAV_BAR);

    this.LOGIN_TOGGLE = protractor.By.css(selectors.LOGIN_TOGGLE);

    this.LOGOUT_BUTTON = protractor.By.css(selectors.LOGOUT_BUTTON);

    this.LOGIN_BUTTON = protractor.By.css(selectors.LOGIN_BUTTON);
  }

  exports.selectors = selectors;
  exports.locators = Object.freeze(new Locators());
}());
