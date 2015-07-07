angular.module('mockServerMoment', []).factory('getServerMoment', function () {
  'use strict';

  var momentInstance = {
    milliseconds: jasmine.createSpy('milliseconds'),
    subtract: jasmine.createSpy('subtract'),
    toISOString: jasmine.createSpy('toISOString')
  };

  momentInstance.milliseconds.andReturn(momentInstance);
  momentInstance.subtract.andReturn(momentInstance);

  return jasmine.createSpy('getServerMoment').andReturn(momentInstance);
});
