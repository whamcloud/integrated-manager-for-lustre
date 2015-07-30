beforeEach(module('fixtures', 'imlMocks'));

(function () {
  'use strict';

  window.flushD3Transitions = function flushD3Transitions () {
    var now = Date.now;
    Date.now = function mockNow () { return Infinity; };
    window.d3.timer.flush();
    Date.now = now;
  };

  // Go around the injector and set this globally for tests.
  window.mock = new window.Mock();

}());

