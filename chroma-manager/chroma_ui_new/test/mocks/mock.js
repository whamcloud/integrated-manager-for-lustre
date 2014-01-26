(function () {
  'use strict';

  function Mock() {
    this.mocks = {};
  }

  /**
   * Takes an instance, "copies" it's properties, and spies on all it's methods.
   * This recursively iterates an object, spying on it's methods.
   * This iterates on all properties of an object (even prototype ones) and should therefore
   * be considered a resemblance of the original object, and not a clone with prototypal inheritance.
   * You will need to spy on returns from method calls yourself.
   * @static
   * @param {Object} instance A fully instantiated object
   * @returns {Object} The copied object.
   */
  Mock.spyInstance = function spyInstance (instance, obj, visited, refs) {
    var name;

    var out = obj || {};

    visited = visited || [];
    refs = refs || [];

    // jshint forin: false
    for (name in instance)
      _mockValue(instance[name], name, out, refs, visited);

    return out;
  };

  function _mockValue(value, name, out, refs, visited) {
    var visitedIndex;

    if (_.isFunction(value)) {
      out[name] = value;

      spyOn(out, name);

    } else if (_.isPlainObject(value)) {
      visitedIndex = visited.indexOf(value);

      if (visitedIndex !== -1) {
        out[name] = refs[visitedIndex];
      } else {
        out[name] = {};
        refs.push(out[name]);
        visited.push(value);
        Mock.spyInstance(value, out[name], visited, refs);
      }
    } else {
      out[name] = value;
    }
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

  Mock.prototype.decorator = function (func) {
    var name = getFunctionName(func);

    this.register({
      type: 'decorator',
      name: name,
      setup: func
    });
  };

  Mock.prototype.factory = function (func) {
    var name = getFunctionName(func);

    this.register({
      type: 'factory',
      name: name,
      setup: func
    });
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

  window.Mock = Mock;

  function getFunctionName(func) {
    var name = func.toString().match(/^\s*function\s*([$\w]*)\s*\(/)[1];

    if (name === '')
      throw new Error('Function cannot be anonymous!');

    return name;
  }
}());
