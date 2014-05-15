angular.module('$windowMock', []).factory('$window', function $windowFactory () {
  'use strict';

  var hrefSpy = jasmine.createSpy('hrefSpy');

  return {
    location: Object.create(null, {
      __hrefSpy__: {
        value: hrefSpy
      },
      href: {
        set: function setter(newLocation) {
          hrefSpy(newLocation);
        },
        get: function getter() {
          return hrefSpy.mostRecentCall.args[0];
        }
      }
    }),
    addEventListener: jasmine.createSpy('$window.addEventListener')
  };
});