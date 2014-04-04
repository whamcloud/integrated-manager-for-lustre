'use strict';

var loginView = require('../views/login'),
  manager = require('../util/manager');

describe('login', function () {
  beforeEach(function () {
    loginView.navigate();
  });

  it('should show an error tooltip if username is blank', function () {
    loginView.login('', 'bar');
    expect(loginView.usernameErrorTooltip.isDisplayed()).toBe(true);
  });

  it('should show an error tooltip if password is blank', function () {
    loginView.login('foo', '');
    expect(loginView.passwordErrorTooltip.isDisplayed()).toBe(true);
  });

  it('should show an overall error if username and password are incorrect', function () {
    loginView.login('foo', 'bar');
    expect(loginView.authFailed.isDisplayed()).toBe(true);
  });

  describe('with correct credentials', function () {
    var user;

    beforeEach(function () {
      user = manager.getSuperuser();
    });

    it('might show the eula', function () {
      loginView.loginAndAcceptEulaIfPresented(user.username, user.password);
    });
  });
});
