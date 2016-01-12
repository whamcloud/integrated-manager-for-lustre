mock.register('help', function () {
  'use strict';

  return {
    get: jasmine.createSpy('help').and.callFake(function () {
      return 'foo';
    })
  };
});
