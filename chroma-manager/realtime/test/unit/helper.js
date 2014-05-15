require('jasmine-n-matchers');
require('jasmine-stealth');

var toContainObject = require('jasmine-object-containing').toContainObject;

beforeEach(function addMatchers() {
  /*jshint validthis: true */
  this.addMatchers(toContainObject);
});