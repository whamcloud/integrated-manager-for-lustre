(function () {
  'use strict';

  var BaseView = require('./base.js').BaseView,
    eulaView = require('../views/eula'),
    loginLocators = require('../selectors/login.js').locators;

  BaseView.extend(LoginView);

  /**
   * Represents the Login Screen of the ui.
   * @constructor
   */
  function LoginView() {
    this.one = {
      username: loginLocators.USERNAME,
      usernameErrorTooltip: loginLocators.USERNAME_ERROR_TOOLTIP,
      password: loginLocators.PASSWORD,
      passwordErrorTooltip: loginLocators.PASSWORD_ERROR_TOOLTIP,
      loginButton: loginLocators.LOGIN_BUTTON,
      authFailed: loginLocators.AUTH_FAILED
    };

    BaseView.call(this);
    this.path = 'login';
  }

  /**
   * Logs the user in by filling fields and clicking the login button.
   * @param {string} username
   * @param {string} password
   */
  LoginView.prototype.login = function (username, password) {
    this.username.sendKeys(username);
    this.password.sendKeys(password);

    this.loginButton.click();
  };

  /**
   * Logs the user in. If the eula is presented, accepts it otherwise continues on.
   * @param {string} username
   * @param {string} password
   */
  LoginView.prototype.loginAndAcceptEulaIfPresented = function(username, password) {
    this.login(username, password);

    eulaView.accept();
  };

  module.exports = new LoginView();
}());

