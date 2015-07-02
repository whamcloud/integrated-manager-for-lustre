'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('get event socket handler test', function () {
  var getEventSocketHandler, getEventSocket,
    eventSocket, socket, workerContext, handler, router;

  beforeEach(function () {
    eventSocket = {
      onMessage: jasmine.createSpy('onMessage'),
      sendMessage: jasmine.createSpy('sendMessage'),
      end: jasmine.createSpy('end')
    };

    router = {
      go: jasmine.createSpy('go'),
      verbs: {
        get: 'get'
      }
    };

    getEventSocket = jasmine.createSpy('getEventSocket')
      .and.returnValue(eventSocket);

    getEventSocketHandler = proxyquire('../../get-event-socket-handler', {
      './get-event-socket': getEventSocket,
      './router': router
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
          path: '/foo/bar',
          id: '1',
          payload: { path: '/foo/bar' },
          type: 'send'
        }
      };
    });

    it('should not route a message if we haven\'t connected yet', function () {
      handler(args);

      expect(router.go).not.toHaveBeenCalled();
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

      it('should route the data', function () {
        expect(router.go).toHaveBeenCalledOnceWith('/foo/bar',
          { verb: 'get', data: args.data },
          { socket: eventSocket, write: jasmine.any(Function)}
        );
      });

      it('should send a postMessage when writing', function () {
        var write = router.go.calls.mostRecent().args[2].write;

        write('foo');

        expect(workerContext.postMessage).toHaveBeenCalledOnceWith({
          type: 'message',
          id: '1',
          payload: 'foo'
        });
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
