var loginView = require('../views/login'),
  eulaView = require('../views/eula'),
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

  it('might show the eula', function () {
    var user = manager.getSuperuser();

    loginView.login(user.username, user.password);

    eulaView.accept();
  });
});