describe('stream module', function () {
  'use strict';

  var stream, $scope, primus, expression;

  beforeEach(module('stream'));

  mock.beforeEach('BASE', 'primus');

  beforeEach(inject(function (_stream_, _primus_, $rootScope) {
    primus = _primus_;

    stream = _stream_;

    $scope = $rootScope.$new();

    $scope.data = [];
    expression = 'data';

  }));

  describe('create', function () {
    var Stream, streamInstance;

    beforeEach(function () {
      Stream = stream('foo', 'bar', {
        transformers: [function transformBodyToDuck(resp, deferred) {
          resp.body = 'Duck';

          deferred.resolve(resp);
        }]
      });

      streamInstance = new Stream(expression, $scope);
    });

    it('should have a setup method that returns a stream', function () {
      streamInstance = Stream.setup(expression, $scope);

      expect(streamInstance instanceof Stream).toBe(true);
    });

    it('should setup a channel when the stream is created', function () {
      expect(primus._channel_).toHaveBeenCalledOnceWith('foo');
    });

    it('should expose the channel as a property', function () {
      expect(streamInstance.channel).toBe(primus._channelInstance_);
    });

    it('should expose the scope as a property', function () {
      expect(streamInstance.scope).toBe($scope);
    });

    it('should expose the scope getter as a function', function () {
      expect(streamInstance.getter()).toBe($scope.data);
    });

    it('should expose the default params used to create the instance', function () {
      expect(streamInstance.defaultParams).toEqual({});
    });

    it('should remove the open listener if startStreaming was called on destroy', function () {
      streamInstance.startStreaming({}, 'fakeMethod');

      $scope.$destroy();

      expect(primus._primusInstance_.removeListener).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
    });

    describe('startStreaming', function () {
      beforeEach(function () {
        streamInstance.startStreaming({}, 'fakeStreamMethod');
      });

      it('should register a stream handler to the channel', function () {
        expect(primus._channelInstance_.on).toHaveBeenCalledWith('stream', jasmine.any(Function));
      });

      it('should register a beforeStreaming handler to the channel', function () {
        expect(primus._channelInstance_.on).toHaveBeenCalledWith('beforeStreaming', jasmine.any(Function));
      });

      it('should send a startStreaming messge', function () {
        expect(primus._channelInstance_.send).toHaveBeenCalledOnceWith('startStreaming');
      });

      it('should add a listener that restarts the stream on open', function () {
        expect(primus._primusInstance_.on).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
      });

      it('should call the callback with method and params beforeStreaming', function () {
        var beforeStreamingCall = primus._channelInstance_.on.mostRecentCallThat(function(call) {
          return call.args[0] === 'beforeStreaming';
        }),
          beforeStreamingFunc = beforeStreamingCall.args[1],
          cb = jasmine.createSpy('cb');

        beforeStreamingFunc(cb);

        expect(cb).toHaveBeenCalledOnceWith('fakeStreamMethod', {});
      });

      it('should run the transformers when new stream data comes in', function () {
        var streamCall = primus._channelInstance_.on.mostRecentCallThat(function (call) {
          return call.args[0] === 'stream';
        }),
          streamFunc = streamCall.args[1],
          resp = {
            body: []
          };

        streamFunc(resp);

        expect(resp.body).toBe('Duck');
      });

      describe('stop streaming', function () {
        var cb;

        beforeEach(function () {
          cb = jasmine.createSpy('cb');

          streamInstance.stopStreaming(cb);
        });

        it('should send stopStreaming', function () {
          expect(primus._channelInstance_.send).toHaveBeenCalledWith('stopStreaming', cb);
        });

        it('should remove the stream listener from the channel', function () {
          expect(primus._channelInstance_.removeAllListeners).toHaveBeenCalledWith('stream');
        });

        it('should remove the beforeStreaming listener from the channel', function () {
          expect(primus._channelInstance_.removeAllListeners).toHaveBeenCalledWith('beforeStreaming');
        });

        it('should remove the open listener from primus', function () {
          expect(primus._primusInstance_.removeListener).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
        });
      });


      describe('restart', function () {
        var stopStreamingCall;

        beforeEach(function () {
          streamInstance.restart();

          stopStreamingCall = primus._channelInstance_.send.mostRecentCallThat(function (call) {
            return call.args[0] === 'stopStreaming';
          });
        });

        it('should stop the stream', function () {
          expect(primus._channelInstance_.send).toHaveBeenCalledOnceWith('stopStreaming', jasmine.any(Function));
        });

        it('should not start the stream until stop calls back', function () {
          expect(primus._channelInstance_.send).toHaveBeenCalledOnceWith('startStreaming');
        });

        it('should start the stream', function () {
          stopStreamingCall.args[1]();

          expect(primus._channelInstance_.send).toHaveBeenCalledTwiceWith('startStreaming');
        });
      });
    });

    describe('destroy', function () {
      beforeEach(function () {
        $scope.$destroy();
      });

      it('should end the channel', function () {
        expect(primus._channelInstance_.end).toHaveBeenCalledOnce();
      });

      it('should null the channel', function () {
        expect(streamInstance.channel).toBeNull();
      });

      it('should null the scope', function () {
        expect(streamInstance.scope).toBeNull();
      });

      it('should null the getter function', function () {
        expect(streamInstance.getter).toBeNull();
      });

    });
  });
});