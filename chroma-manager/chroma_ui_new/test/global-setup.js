beforeEach(module('fixtures', 'imlMocks'));

(function () {
  'use strict';

  // Go around the injector and set this globally for tests.
  window.mock = new window.Mock();

}());

