'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('get event socket handler test', function () {
  var getEventSocketHandler, getEventSocket, eventSocket, socket, workerContext, handler;

  beforeEach(function () {
    eventSocket = {
      onMessage: jasmine.createSpy('onMessage'),
      sendMessage: jasmine.createSpy('sendMessage'),
      end: jasmine.createSpy('end')
    };

    getEventSocket = jasmine.createSpy('getEventSocket')
      .and.returnValue(eventSocket);

    getEventSocketHandler = proxyquire('../../get-event-socket-handler', {
        './get-event-socket': getEventSocket
    });

    socket = {};

    workerContext = {
      addEventListener: jasmine.createSpy('addEventListener'),
      postMessage: jasmine.createSpy('postMessage')
    };

    getEventSocketHandler(socket, workerContext);

    handler = workerContext.addEventListener.calls.allArgs()[0][1];
  });



  it('should be a factory function', function () {
    expect(getEventSocketHandler).toEqual(jasmine.any(Function));
  });

  it('should add a message listener', function () {
    expect(workerContext.addEventListener)
      .toHaveBeenCalledOnceWith('message', jasmine.any(Function), false);
  });

  describe('connect', function () {
    var args;

    beforeEach(function () {
      args = {
        data: {
          id: '1',
          type: 'connect'
        }
      };

      handler(args);
    });

    it('should get an event socket', function () {
      expect(getEventSocket).toHaveBeenCalledOnceWith(socket, '1', undefined);
    });

    it('should not recreate an existing socket', function () {
      handler(args);

      expect(getEventSocket).toHaveBeenCalledOnce();
    });
  });


  describe('send', function () {
    var args;

    beforeEach(function () {
      args = {
        data: {
          id: '1',
          payload: { path: '/foo/bar' },
          type: 'send'
        }
      };
    });

    it('should not send a message if we haven\'t connected yet', function () {
      handler(args);

      expect(eventSocket.sendMessage).not.toHaveBeenCalled();
    });

    describe('with a connected socket', function () {
      beforeEach(function () {
        handler({
          data: {
            id: '1',
            type: 'connect'
          }
        });
      });

      it('should register an onMessage handler', function () {
        handler(args);
        expect(eventSocket.onMessage).toHaveBeenCalledOnceWith(jasmine.any(Function));
      });

      it('should send the payload as a message', function () {
        handler(args);
        expect(eventSocket.sendMessage).toHaveBeenCalledOnceWith({ path: '/foo/bar' }, undefined);
      });

      it('should send an ack if requested', function () {
        args.data.ack = true;

        handler(args);

        expect(eventSocket.sendMessage)
          .toHaveBeenCalledOnceWith({ path: '/foo/bar'}, jasmine.any(Function));
      });

      it('should not listen if sending an ack', function () {
        args.data.ack = true;

        handler(args);

        expect(eventSocket.onMessage).not.toHaveBeenCalled();
      });

    });
  });

  describe('end', function () {
    var args;

    beforeEach(function () {
      args = {
        data: {
          id: '1',
          type: 'end'
        }
      };
    });

    it('should not end a non-existent socket', function () {
      handler(args);

      expect(eventSocket.end).not.toHaveBeenCalled();
    });

    describe('with a connected socket', function () {
      beforeEach(function () {
        handler({
          data: {
            id: '1',
            type: 'connect'
          }
        });

        handler(args);
      });

      it('should end a connected socket', function () {
        expect(eventSocket.end).toHaveBeenCalledOnce();
      });

      it('should not end a socket twice', function () {
        handler(args);

        expect(eventSocket.end).toHaveBeenCalledOnce();
      });
    });
  });
});
