(function () {
  'use strict';


  function Selectors() {
    this.LOGIN = '.login';

    this.ERROR_TOOLTIP = '.error-tooltip';

    this.AUTH_FAILED = this.LOGIN + ' .auth-failed';

    this.USERNAME_GROUP = this.LOGIN + ' .username-group';
    this.USERNAME = this.USERNAME_GROUP + ' input';
    this.USERNAME_ERROR_TOOLTIP = this.USERNAME_GROUP + ' ' + this.ERROR_TOOLTIP;

    this.PASSWORD_GROUP = this.LOGIN + ' .password-group';
    this.PASSWORD = this.PASSWORD_GROUP + ' input';
    this.PASSWORD_ERROR_TOOLTIP = this.PASSWORD_GROUP + ' ' + this.ERROR_TOOLTIP;

    this.LOGIN_BUTTON = this.LOGIN + ' button.btn-success';
  }


  var selectors = Object.freeze(new Selectors());


  function Locators() {
    this.AUTH_FAILED = protractor.By.css(selectors.AUTH_FAILED);

    this.USERNAME = protractor.By.css(selectors.USERNAME);
    this.USERNAME_ERROR_TOOLTIP = protractor.By.css(selectors.USERNAME_ERROR_TOOLTIP);

    this.PASSWORD = protractor.By.css(selectors.PASSWORD);
    this.PASSWORD_ERROR_TOOLTIP = protractor.By.css(selectors.PASSWORD_ERROR_TOOLTIP);

    this.LOGIN_BUTTON = protractor.By.css(selectors.LOGIN_BUTTON);
  }

  exports.selectors = selectors;
  exports.locators = Object.freeze(new Locators());
}());
