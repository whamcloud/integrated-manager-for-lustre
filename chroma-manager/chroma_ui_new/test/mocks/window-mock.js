mock.register('$window', function () {
  'use strict';

  var hrefSpy = jasmine.createSpy('hrefSpy');

  return {
    location: Object.create(null, {
      __hrefSpy__: {
        value: hrefSpy
      },
      href: {
        set: function (newLocation) {
          hrefSpy(newLocation);
        },
        get: function () {
          return hrefSpy.mostRecentCall.args[0];
        }
      }
    })
  };
});
