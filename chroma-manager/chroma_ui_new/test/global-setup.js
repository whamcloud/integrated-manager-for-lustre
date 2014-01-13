beforeEach(module('fixtures', 'imlMocks'));

(function () {
  'use strict';


  jasmine.createRecursiveStubObj = function createStubObj(baseName, stubbings, obj) {
    var name, stubbing;
    if (stubbings.constructor === Array) {
      return jasmine.createSpyObj(baseName, stubbings);
    } else {
      obj = obj || {};

      // jshint forin: false
      for (name in stubbings) {
        stubbing = stubbings[name];
        if (_.isFunction(stubbing)) {
          obj[name] = jasmine.createSpy(baseName + '.' + name);
          obj[name].andCallFake(stubbing);
        } else if (_.isObject(stubbing)) {
          obj[name] = {};

          createStubObj(baseName, stubbing, obj[name]);
        } else {
          obj[name] = stubbing;
        }
      }
      return obj;
    }
  };
}());

