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
    if (name === Object(name))
      this.mocks[name.name] = name;
    else
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
        if (angular.isFunction(name)) {
          var ret = name();

          if (_.isPlainObject(ret)) {
            $provide.value(ret.name, ret.value);
          } else {
            ret.forEach(function (obj) {
              $provide.value(obj.name, obj.value);
            });
          }

          return;
        }

        var setup = self.mocks[name];

        if (!setup) throw new Error('no mock found matching %s!'.sprintf(name));

        if (typeof setup === 'function')
          $provide.factory(name, setup);
        else if (setup === Object(setup))
          $provide[setup.type](setup.name, setup.setup);
        else
          $provide.value(name, setup);
      });
    }));
  };

  // Go around the injector and set this globally for tests.
  window.mock = new Mock();
}());
