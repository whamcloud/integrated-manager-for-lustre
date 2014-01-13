mock.register('$routeSegment', function () {
  'use strict';

  return {
    $routeParams: {},
    chain: [],
    contains: jasmine.createSpy('contains'),
    name: '',
    startsWith: jasmine.createSpy('startsWith')
  };
});
