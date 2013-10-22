(function () {
  'use strict';

  var BaseView = require('./base.js').BaseView;
  var loginLocators = require('../selectors/login.js').locators;

  BaseView.extend(LoginView);

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

  LoginView.prototype.login = function (username, password) {
    this.navigate();

    this.username.sendKeys(username);
    this.password.sendKeys(password);

    this.loginButton.click();
  };

  LoginView.prototype.logout = function () {

  };


  LoginView.prototype.loginAndAcceptEulaIfPresented = function(username, password) {
    this.login(username, password);

  };

//  LoginView.prototype.loginAndRejectEula = function(username, password) {
//
//  };

  module.exports = new LoginView();
}());

