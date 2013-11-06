(function () {
  'use strict';

  var navBarView = require('../views/nav-bar');

  beforeEach(function() {
    navBarView.navigate();
    navBarView.loginToggle.click();
  });
}());
