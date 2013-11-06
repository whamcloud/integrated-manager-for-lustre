var loginView = require('../views/login'),
  manager = require('../util/manager');

describe('login', function () {
  'use strict';

  it('should show an error tooltip if username is blank', function () {
    loginView.login('', 'bar');
    loginView.usernameErrorTooltip;
  });

  it('should show an error tooltip if password is blank', function () {
    loginView.login('foo', '');
    loginView.passwordErrorTooltip;
  });

  it('should show an overall error if username and password are incorrect', function () {
    loginView.login('foo', 'bar');
    loginView.authFailed;
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
