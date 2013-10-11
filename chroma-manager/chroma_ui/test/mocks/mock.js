(function () {
  'use strict';

  function Mock() {
    this.mocks = {};
  }

  /**
   * Add a new mock to the list.
   * @param {string} name
   * @param {function} setup
   */
  Mock.prototype.register = function(name, setup) {
    this.mocks[name] = setup;
  };

  /**
   * Looks up the provided argument names and loads them as factories in a beforeEach block.
   * Call this after loading modules.
   */
  Mock.prototype.beforeEach = function() {
    var self = this;
    var args = Array.prototype.slice.call(arguments, 0);

    if (!args.length) throw new Error('no mocks passed to Mock::setupMocks!');

    beforeEach(module(function ($provide) {
      args.forEach(function (name) {
        var setup = self.mocks[name];

        if (!setup) throw new Error('no mock found matching %s!'.sprintf(name));

        $provide.factory(name, setup);
      });
    }));
  };

  // Go around the injector and set this globally for tests.
  window.mock = new Mock();
}());
