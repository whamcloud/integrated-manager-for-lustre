'use strict';

var Q = require('q'),
  channelFactory = require('../../channel');

describe('channel', function () {
  var logger, Stream, Resource, primus, setup, channelInstance, spark, log;

  beforeEach(function () {
    log = {
      info: jasmine.createSpy('log.info'),
      error: jasmine.createSpy('log.error')
    };

    logger = {
      child: jasmine.createSpy('logger').andReturn(log)
    };

    Resource = function Resource() {};
    Resource.prototype.getHttpMethods = jasmine.createSpy('resource.getHttpMethods');

    Stream = function Stream() {};
    Stream.prototype.start = jasmine.createSpy('stream.start');
    Stream.prototype.stop = jasmine.createSpy('stream.end');

    spark = {
      on: jasmine.createSpy('spark.on'),
      send: jasmine.createSpy('spark.send'),
      removeAllListeners: jasmine.createSpy('spark.removeAllListeners')
    };

    channelInstance = {
      on: jasmine.createSpy('channelInstance.on')
    };

    primus = {
      channel: jasmine.createSpy('primus.channel').andReturn(channelInstance)
    };

    setup = channelFactory(primus, logger, Stream);
  });

  describe('setup', function () {
    var channelName;

    beforeEach(function () {
      channelName = 'foo';

      setup('foo', Resource);
    });

    it('should create a child log', function () {
      expect(logger.child).toHaveBeenCalledOnceWith({channelName: channelName});
    });

    it('should create a channel', function () {
      expect(primus.channel).toHaveBeenCalledOnceWith(channelName);
    });

    it('should register a connection listener to the channel', function () {
      expect(channelInstance.on).toHaveBeenCalledOnceWith('connection', jasmine.any(Function));
    });

    describe('connection', function () {
      var connectionHandler;

      beforeEach(function () {
        connectionHandler = channelInstance.on.mostRecentCall.args[1];

        Resource.prototype.getHttpMethods.andReturn([]);

        connectionHandler(spark);
      });

      it('should log the connection', function () {
        expect(log.info).toHaveBeenCalledOnceWith('connected');
      });

      it('should register a listener on startStreaming', function () {
        expect(spark.on).toHaveBeenCalledOnceWith('startStreaming', jasmine.any(Function));
      });

      it('should register a listener on stopStreaming', function () {
        expect(spark.on).toHaveBeenCalledWith('stopStreaming', jasmine.any(Function));
      });

      it('should register a listener on end', function () {
        expect(spark.on).toHaveBeenCalledWith('end', jasmine.any(Function));
      });

      describe('start streaming', function () {
        var startStreamingHandler;

        beforeEach(function () {
          startStreamingHandler = spark.on.calls[0].args[1];
        });

        it('should start the stream', function () {
          startStreamingHandler();

          expect(Stream.prototype.start).toHaveBeenCalledOnceWith(jasmine.any(Function));
        });

        it('should return if stream already has a timer', function () {
          Stream.prototype.timer = '2012o3123';

          startStreamingHandler();

          expect(Stream.prototype.start).not.toHaveBeenCalled();
        });

        describe('stream start', function () {
          var streamStartHandler;

          beforeEach(function () {
            startStreamingHandler();
            streamStartHandler = Stream.prototype.start.mostRecentCall.args[0];
          });

          it('should send beforeStreaming from the spark', function () {
            streamStartHandler();

            expect(spark.send).toHaveBeenCalledWith('beforeStreaming', jasmine.any(Function));
          });

          it('should log an error if one occurs', function () {
            var err = new Error('boom!');

            streamStartHandler(err);

            expect(log.error).toHaveBeenCalledWith({err: err});
          });

          it('should send a streamingError if one occurs', function () {
            var err = new Error('boom!');

            streamStartHandler(err);

            expect(spark.send).toHaveBeenCalledWith('streamingError', jasmine.any(Object));
          });

          describe('beforeStreaming', function () {
            var beforeStreamingHandler, done, defer;

            beforeEach(function () {
              defer = Q.defer();

              done = jasmine.createSpy('done');
              streamStartHandler(null, done);
              beforeStreamingHandler = spark.send.mostRecentCall.args[1];

              spyOn(Q.makePromise.prototype, 'finally').andCallThrough();

              Resource.prototype.foo = jasmine.createSpy('resource.foo').andReturn(defer.promise);

              beforeStreamingHandler('foo', {});
            });

            it('should log an error if one occurs from the resource method', function (done) {
              var err = new Error('boom!');

              defer.reject(err);

              defer.promise.finally(function () {
                expect(log.error).toHaveBeenCalledWith({err: err});
                done();
              });
            });

            it('should send a streamingError from the spark', function (done) {
              var err = new Error('boom!');

              defer.reject(err);

              defer.promise.finally(function () {
                expect(spark.send).toHaveBeenCalledWith('streamingError', jasmine.any(Object));
                done();
              });
            });

            describe('sending data', function () {
              beforeEach(function () {
                var resp = {
                  headers: {},
                  statusCode: 200,
                  body: []
                };

                defer.resolve(resp);
              });

              it('should send stream of data', function (done) {
                defer.promise.then(function () {
                  expect(spark.send).toHaveBeenCalledOnceWith('stream', {
                    headers: {},
                    statusCode: 200,
                    body: [],
                    params: {}
                  });

                  done();
                });
              });

              it('should call done', function () {
                expect(Q.makePromise.prototype.finally).toHaveBeenCalledOnceWith(done);
              });
            });
          });
        });
      });

      describe('stop streaming', function () {
        var stopStreamingHandler, fn;

        beforeEach(function () {
          fn = jasmine.createSpy('fn');
          stopStreamingHandler = spark.on.calls[1].args[1];
          stopStreamingHandler(fn);
        });

        it('should stop the stream', function () {
          expect(Stream.prototype.stop).toHaveBeenCalled();
        });

        it('should call the ack function', function () {
          expect(fn).toHaveBeenCalled();
        });
      });

      describe('end', function () {
        var endHandler;

        beforeEach(function () {
          endHandler = spark.on.calls[2].args[1];

          endHandler();
        });

        it('should remove all listeners from the spark', function () {
          expect(spark.removeAllListeners).toHaveBeenCalled();
        });

        it('should log the stream has ended', function () {
          expect(log.info).toHaveBeenCalledWith('ended');
        });

        it('should stop the stream', function () {
          expect(Stream.prototype.stop).toHaveBeenCalled();
        });
      });
    });
  });
});