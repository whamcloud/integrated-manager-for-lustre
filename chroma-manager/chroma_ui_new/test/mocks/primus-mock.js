mock.register('primus', function () {
  'use strict';

  var channelInstance = {
    send: jasmine.createSpy('send'),
    on: jasmine.createSpy('on'),
    end: jasmine.createSpy('end'),
    removeAllListeners: jasmine.createSpy('removeAllListeners').andCallFake(function () {
      return channelInstance;
    })
  };

  var channel = jasmine.createSpy('channel').andCallFake(function () {
    return channelInstance;
  });

  var primusInstance = {
    removeListener: jasmine.createSpy('removeListener'),
    on: jasmine.createSpy('on'),
    channel: channel
  };

  var primus = jasmine.createSpy('primus').andCallFake(function () {
    return primusInstance;
  });

  primus._channel_ = channel;
  primus._primusInstance_ = primusInstance;
  primus._channelInstance_ = channelInstance;

  return primus;
});
