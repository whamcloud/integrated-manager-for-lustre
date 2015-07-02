'use strict';

var proxyquire = require('proxyquire').noPreserveCache();
var fp = require('fp');

var getEventHandler = fp.curry(3, function getEventHandler (methodName, socket, event) {
  var args = socket[methodName].calls.allArgs();

  return args.filter(function (item) {
    return item[0] === event;
  })[0][1];
});

describe('create socket', function () {
  var result, socket, io, url, workerContext,
    getOnceHandler, getOnHandler, createSocket;

  beforeEach(function () {
    socket = {
      on: jasmine.createSpy('on'),
      once: jasmine.createSpy('once'),
      disconnect: jasmine.createSpy('disconnect')
    };

    io = jasmine.createSpy('io').and.returnValue(socket);

    createSocket = proxyquire('../../create-socket', {
      'socket.io-client': io
    });

    url = 'https://localhost:8000';
    workerContext = {
      postMessage: jasmine.createSpy('postMessage')
    };

    getOnceHandler = getEventHandler('once', socket);
    getOnHandler = getEventHandler('on', socket);

    result = createSocket(url, workerContext);
  });

  it('should be a function', function () {
    expect(createSocket).toEqual(jasmine.any(Function));
  });

  it('should return a socket', function () {
    expect(result).toBe(socket);
  });

  it('should register a reconnecting handler', function () {
    expect(socket.on).toHaveBeenCalledOnceWith('reconnecting', jasmine.any(Function));
  });

  it('should post a message on reconnecting', function () {
    var handler = getOnHandler('reconnecting');
    handler(2);

    expect(workerContext.postMessage)
      .toHaveBeenCalledOnceWith({ type: 'reconnecting', data: 2 });
  });

  it('should register a reconnect handler', function () {
    expect(socket.on).toHaveBeenCalledOnceWith('reconnect', jasmine.any(Function));
  });

  it('should post a message on reconnect', function () {
    var handler = getOnHandler('reconnect');
    handler(3);

    expect(workerContext.postMessage)
      .toHaveBeenCalledOnceWith({ type: 'reconnect', data: 3 });
  });

  it('should register an error handler', function () {
    expect(socket.once).toHaveBeenCalledOnceWith('error', jasmine.any(Function));
  });

  it('should post a message on error', function () {
    var err = new Error('boom!');

    var handler = getOnceHandler('error');
    handler(err);

    expect(workerContext.postMessage).toHaveBeenCalledOnceWith({ type: 'error', data: err });
  });

  it('should disconnect on error', function () {
    var err = new Error('boom!');

    var handler = getOnceHandler('error');
    handler(err);

    expect(socket.disconnect).toHaveBeenCalledOnce();
  });

  it('should post a message on disconnect', function () {
    var handler = getOnceHandler('disconnect');
    handler();

    expect(workerContext.postMessage).toHaveBeenCalledOnceWith({ type: 'disconnect' });
  });
});
