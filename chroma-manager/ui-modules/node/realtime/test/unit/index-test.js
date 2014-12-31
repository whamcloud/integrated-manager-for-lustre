'use strict';

var rewire = require('rewire');
var start = rewire('../../index');

describe('realtime index test', function () {
  var createIo, io, conf, confData, revert, logger, socket, data, ack, requestValidator, socketRouter,
    serializeError, eventWildcard;

  describe('setup events', function () {
    beforeEach(function () {
      confData = {
        REALTIME_PORT: 8888
      };

      conf = {
        get: jasmine.createSpy('conf.get').and.callFake(function (key) {
          return confData[key];
        })
      };

      io = {
        attach: jasmine.createSpy('attach'),
        on: jasmine.createSpy('on'),
        close: jasmine.createSpy('close'),
        use: jasmine.createSpy('use')
      };

      createIo = jasmine.createSpy('createIo').and.returnValue(io);

      logger = {
        debug: jasmine.createSpy('logger.debug'),
        error: jasmine.createSpy('logger.error')
      };

      socket = {
        on: jasmine.createSpy('socket.on'),
        emit: jasmine.createSpy('emit'),
        write: jasmine.createSpy('write')
      };

      data = {
        options: {},
        path: '/api/alert/',
        method: 'get',
        eventName: 'message1'
      };

      ack = jasmine.createSpy('ack');

      socketRouter = {
        go: jasmine.createSpy('socketRouter')
      };

      requestValidator = jasmine.createSpy('requestValidator');

      serializeError = jasmine.createSpy('serializeError');

      eventWildcard = jasmine.createSpy('eventWildcard');

      revert = start.__set__({
        createIo: createIo,
        logger: logger,
        requestValidator: requestValidator,
        socketRouter: socketRouter,
        serializeError: serializeError,
        eventWildcard: eventWildcard
      });
    });

    afterEach(function () {
      revert();
    });

    it('should register the eventWildcard plugin', function () {
      start();
      expect(io.use).toHaveBeenCalledOnceWith(eventWildcard);
    });

    it('should call createIo', function () {
      start();
      expect(createIo).toHaveBeenCalledOnce();
    });

    it('should call io.attach with the realtime port', function () {
      start();
      expect(io.attach).toHaveBeenCalledOnceWith(confData.REALTIME_PORT);
    });

    it('should register a connection event handler on io', function () {
      start();
      expect(io.on).toHaveBeenCalledOnceWith('connection', jasmine.any(Function));
    });

    describe('on io', function () {
      beforeEach(function () {
        io.on.and.callFake(function (evt, fn) {
          if (evt === 'connection')
            fn(socket);
        });
      });

      describe('connection event', function () {
        it('should log that the socket was connected', function () {
          start();
          expect(logger.debug).toHaveBeenCalledOnceWith('socket connected');
        });

        it('should register the socket wildcard event', function () {
          start();
          expect(socket.on).toHaveBeenCalledOnceWith('*', jasmine.any(Function));
        });

        describe('on socket wildcard', function () {
          beforeEach(function () {
            socket.on.and.callFake(function (evt, fn) {
              if (evt === '*')
                fn(data, ack);
            });
          });

          describe('success', function () {
            beforeEach(function () {
              requestValidator.and.returnValue([]);
            });

            it('should call requestValidator', function () {
              start();
              expect(requestValidator).toHaveBeenCalledOnceWith(data);
            });

            it('should call socketRouter with the appropriate data', function () {
              start();
              expect(socketRouter.go).toHaveBeenCalledOnceWith(data.path, {
                  verb: data.method,
                  data: data.options,
                  messageName: 'message1',
                  endName: 'end1'
                },
                {
                  socket: socket,
                  ack: ack
                });
            });
          });

          describe('error', function () {
            var error, serializedError;
            beforeEach(function () {
              error = 'something bad happened';
              serializedError = 'serialized error';
              serializeError.and.returnValue(serializedError);
              requestValidator.and.returnValue(error);
            });

            describe('with ack', function () {
              it('should ack the error', function () {
                start();
                expect(ack).toHaveBeenCalledOnceWith(serializedError);
              });
            });

            describe('without ack', function () {
              it('should call socket.emit to the message with the error', function () {
                ack = null;
                start();
                expect(socket.emit).toHaveBeenCalledOnceWith('message1', serializedError);
              });
            });
          });
        });

        it('should register the socket error event', function () {
          start();
          expect(socket.on).toHaveBeenCalledOnceWith('error', jasmine.any(Function));
        });

        describe('on socket error', function () {
          var err;
          beforeEach(function () {
            err = new Error('something bad happend');
            socket.on.and.callFake(function (evt, fn) {
              if (evt === 'error')
                fn(err);
            });
          });

          it('should log the error', function () {
            start();
            expect(logger.error).toHaveBeenCalledOnceWith({err: err}, 'socket error');
          });
        });
      });
    });

    describe('shutdown', function () {
      it('should call io.close', function () {
        var shutdown = start();
        shutdown();

        expect(io.close).toHaveBeenCalledOnce();
      });
    });
  });
});
