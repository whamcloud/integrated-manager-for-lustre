mock.register('help', function () {
  'use strict';

  return {
    get: jasmine.createSpy('help').andCallFake(function () {
      return 'foo';
    })
  };
});
