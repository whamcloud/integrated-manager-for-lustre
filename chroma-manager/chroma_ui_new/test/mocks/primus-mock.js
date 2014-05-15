angular.module('mockPrimus', []).factory('primus', function primusFactory() {
  'use strict';

  var channelInstance = {
    send: jasmine.createSpy('send'),
    on: jasmine.createSpy('on'),
    end: jasmine.createSpy('end'),
    removeAllListeners: jasmine.createSpy('removeAllListeners').andCallFake(function () {
      return channelInstance;
    })
  };

  var primusInstance = {
    removeListener: jasmine.createSpy('removeListener'),
    on: jasmine.createSpy('on'),
    channel: jasmine.createSpy('channel').andReturn(channelInstance)
  };

  return jasmine.createSpy('primus').andReturn(primusInstance);
});