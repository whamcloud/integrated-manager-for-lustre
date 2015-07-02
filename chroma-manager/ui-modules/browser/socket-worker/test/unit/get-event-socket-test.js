'use strict';

var getEventSocket = require('../../get-event-socket');

describe('event connection', function () {
  var eventSocket, socket, id;

  beforeEach(function () {
    socket = {
      emit: jasmine.createSpy('emit'),
      on: jasmine.createSpy('on'),
      off: jasmine.createSpy('off'),
      once: jasmine.createSpy('once'),
      removeAllListeners: jasmine.createSpy('removeAllListeners')
    };

    id = 'foo';

    eventSocket = getEventSocket(socket, id);
  });

  it('should be a function', function () {
    expect(getEventSocket).toEqual(jasmine.any(Function));
  });

  it('should return an Object extending socket', function () {
    expect(Object.getPrototypeOf(eventSocket)).toBe(socket);
  });

  it('should return a socket with a sendMessage method', function () {
    eventSocket.sendMessage({});

    expect(socket.emit).toHaveBeenCalledOnceWith('messagefoo', {}, undefined);
  });

  it('should take an ack for sendMessage', function () {
    var spy = jasmine.createSpy('spy');

    eventSocket.sendMessage({}, spy);

    expect(socket.emit).toHaveBeenCalledOnceWith('messagefoo', {}, spy);
  });

  it('should register a reconnect listener on socket', function () {
    expect(socket.on).toHaveBeenCalledOnceWith('reconnect', jasmine.any(Function));
  });

  describe('reconnecting', function () {
    var handler;

    beforeEach(function () {
      handler = socket.on.calls.mostRecent().args[1];
    });

    it('should re-call emit on reconnect', function () {
      eventSocket.sendMessage({ path: '/host' });

      handler();

      expect(socket.emit).toHaveBeenCalledTwiceWith('messagefoo', {
        path: '/host'
      }, undefined);
    });
  });

  describe('ending', function () {
    beforeEach(function () {
      eventSocket.end();
    });

    it('should remove message listeners on end', function () {
      expect(socket.removeAllListeners).toHaveBeenCalledOnceWith('messagefoo');
    });

    it('should return a socket with an end method', function () {
      expect(socket.emit).toHaveBeenCalledOnceWith('endfoo');
    });

    it('should remove reconnect listener on disconnect', function () {
      expect(socket.off).toHaveBeenCalledOnceWith('reconnect', jasmine.any(Function));
    });
  });

  describe('disconnecting', function () {
    beforeEach(function () {
      var handler = socket.once.calls.mostRecent().args[1];
      handler();
    });

    it('should register a listener', function () {
      expect(socket.once).toHaveBeenCalledOnceWith('destroy', jasmine.any(Function));
    });

    it('should remove message listeners on destroy', function () {
      expect(socket.removeAllListeners).toHaveBeenCalledOnceWith('messagefoo');
    });

    it('should remove reconnect listener on destroy', function () {
      expect(socket.off).toHaveBeenCalledOnceWith('reconnect', jasmine.any(Function));
    });
  });

  it('should register an onMessage handler', function () {
    var spy = jasmine.createSpy('spy');

    eventSocket.onMessage(spy);

    expect(socket.on).toHaveBeenCalledOnceWith('messagefoo', spy);
  });
});
