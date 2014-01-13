'use strict';

var sinon = require('sinon'),
  channelFactory = require('../../channel');

require('jasmine-sinon');

describe('channel', function () {
  var logger, Stream, Resource, primus, setup, channelInstance, spark, log;

  beforeEach(function () {
    log = {
      info: sinon.spy(),
      error: sinon.spy()
    };

    logger = {
      child: sinon.stub().returns(log)
    };

    Resource = function Resource() {};
    Resource.prototype.getHttpMethods = sinon.stub();

    Stream = function Stream() {};
    Stream.prototype.start = sinon.spy();
    Stream.prototype.stop = sinon.spy();

    spark = {
      on: sinon.spy(),
      send: sinon.spy(),
      removeAllListeners: sinon.spy()
    };

    channelInstance = {
      on: sinon.spy()
    };

    primus = {
      channel: sinon.stub().returns(channelInstance)
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
      expect(logger.child).toHaveBeenAlwaysCalledWith({channelName: channelName});
    });

    it('should create a channel', function () {
      expect(primus.channel).toHaveBeenAlwaysCalledWith(channelName);
    });

    it('should register a connection listener to the channel', function () {
      expect(channelInstance.on).toHaveBeenAlwaysCalledWith('connection', sinon.match.func);
    });

    describe('connection', function () {
      var connectionHandler;

      beforeEach(function () {
        connectionHandler = channelInstance.on.getCall(0).args[1];

        Resource.prototype.getHttpMethods.returns([]);

        connectionHandler(spark);
      });

      it('should log the connection', function () {
        expect(log.info).toHaveBeenCalledWith('connected');
      });

      it('should register a listener on startStreaming', function () {
        expect(spark.on).toHaveBeenCalledWith('startStreaming', sinon.match.func);
      });

      it('should register a listener on stopStreaming', function () {
        expect(spark.on).toHaveBeenCalledWith('stopStreaming', sinon.match.func);
      });

      it('should register a listener on end', function () {
        expect(spark.on).toHaveBeenCalledWith('end', sinon.match.func);
      });

      describe('start streaming', function () {
        var startStreamingHandler;

        beforeEach(function () {
          startStreamingHandler = spark.on.getCall(0).args[1];
        });

        it('should start the stream', function () {
          startStreamingHandler();

          expect(Stream.prototype.start).toHaveBeenAlwaysCalledWith(sinon.match.func);
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
            streamStartHandler = Stream.prototype.start.getCall(0).args[0];
          });

          it('should send beforeStreaming from the spark', function () {
            streamStartHandler();

            expect(spark.send).toHaveBeenCalledWith('beforeStreaming', sinon.match.func);
          });

          it('should log an error if one occurs', function () {
            var err = new Error('boom!');

            streamStartHandler(err);

            expect(log.error).toHaveBeenCalledWith({err: err});
          });

          it('should send a streamingError if one occurs', function () {
            var err = new Error('boom!');

            streamStartHandler(err);

            expect(spark.send).toHaveBeenCalledWith('streamingError', sinon.match.object);
          });

          describe('beforeStreaming', function () {
            var beforeStreamingHandler;

            beforeEach(function () {
              streamStartHandler();
              beforeStreamingHandler = spark.send.getCall(0).args[1];

              Resource.prototype.foo = sinon.stub();

              beforeStreamingHandler('foo', {});
            });

            it('should log the request params', function () {
              expect(log.info).toHaveBeenCalledWith('sending request', {});
            });

            it('should log an error if one occurs from the resource method', function () {
              var err = new Error('boom!');

              Resource.prototype.foo.callArgWith(1, err);

              expect(log.error).toHaveBeenCalledWith({err: err});
            });

            it('should send a streamingError from the spark', function () {
              var err = new Error('boom!');

              Resource.prototype.foo.callArgWith(1, err);

              expect(spark.send).toHaveBeenCalledWith('streamingError', sinon.match.object);
            });

            it('should send stream of data', function () {
              var resp = {headers: {}, statusCode: 200},
                body = [],
                reqParams = {param: 'value'};

              Resource.prototype.foo.callArgWith(1, null, resp, body, reqParams);

              expect(spark.send).toHaveBeenCalledWith('stream', {
                headers: {},
                statusCode: 200,
                body: [],
                params: reqParams
              });
            });
          });

        });

      });

      describe('stop streaming', function () {
        var stopStreamingHandler, fn;

        beforeEach(function () {
          fn = sinon.spy();
          stopStreamingHandler = spark.on.getCall(1).args[1];
          stopStreamingHandler(fn);
        });

        it('should stop the stream', function () {
          expect(Stream.prototype.stop).toHaveBeenCalledOnce();
        });

        it('should call the ack function', function () {
          expect(fn).toHaveBeenCalledOnce();
        });
      });

      describe('end', function () {
        var endHandler;

        beforeEach(function () {
          endHandler = spark.on.getCall(2).args[1];

          endHandler();
        });

        it('should remove all listeners from the spark', function () {
          expect(spark.removeAllListeners).toHaveBeenCalledOnce();
        });

        it('should log the stream has ended', function () {
          expect(log.info).toHaveBeenCalledWith('ended');
        });

        it('should stop the stream', function () {
          expect(Stream.prototype.stop).toHaveBeenCalledOnce();
        });
      });
    });
  });
});