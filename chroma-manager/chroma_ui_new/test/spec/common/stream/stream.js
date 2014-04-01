describe('stream module', function () {
  'use strict';

  var stream, $scope, primus, expression, pageVisibility;

  beforeEach(module('stream', function ($provide) {
    $provide.factory('pageVisibility', function () {
      return {
        onChange: jasmine.createSpy('pageVisibility.onChange').andReturn(
          jasmine.createSpy('deregister')
        )
      };
    });
  }));

  mock.beforeEach('BASE', 'primus');

  beforeEach(inject(function (_stream_, _primus_, _pageVisibility_, $rootScope) {
    primus = _primus_;
    stream = _stream_;
    pageVisibility = _pageVisibility_;
    $scope = $rootScope.$new();

    $scope.data = [];
    expression = 'data';

  }));

  describe('create', function () {
    var Stream, streamInstance;

    beforeEach(function () {
      Stream = stream('foo', 'bar', {
        transformers: [function transformBodyToDuck(resp) {
          resp.body = 'Duck';

          return resp;
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

    it('should expose the scope setter as a function', function () {
      var newData = ['foo', 'bar'];

      streamInstance.setter(newData);
      expect($scope.data).toBe(newData);
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

      it('should add a listener that toggles the stream when page visibility changes', function () {
        expect(pageVisibility.onChange).toHaveBeenCalledOnceWith(jasmine.any(Function));
      });

      it('should stop the stream if the page is hidden', function () {
        var cb = pageVisibility.onChange.mostRecentCall.args[0];

        cb(true);

        expect(primus._channelInstance_.send).toHaveBeenCalledOnceWith('stopStreaming');
      });

      it('should start the stream if the page is not hidden', function () {
        var cb = pageVisibility.onChange.mostRecentCall.args[0];

        cb(false);

        expect(primus._channelInstance_.send).toHaveBeenCalledTwiceWith('startStreaming');
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

        it('should remove the page visibility listener from the page visibility service', function () {
          var deregister = pageVisibility.onChange.plan();

          expect(deregister).toHaveBeenCalledOnce();
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

    describe('prependTransformers', function () {
      var transformer = jasmine.createSpy('transformer').andCallFake(_.identity);

      beforeEach(function () {
        streamInstance.startStreaming({}, 'fakeStreamMethod', transformer);
      });

      it('should call the prepend transformer', function () {
        var streamCall = primus._channelInstance_.on.mostRecentCallThat(function (call) {
            return call.args[0] === 'stream';
          }),
          streamFunc = streamCall.args[1],
          resp = {
            body: []
          };

        streamFunc(resp);

        expect(transformer).toHaveBeenCalledOnceWith(resp);
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

      it('should null the setter function', function () {
        expect(streamInstance.setter).toBeNull();
      });
    });
  });
});

describe('immutable stream', function () {
  'use strict';

  beforeEach(module('immutableStream'));

  var immutableStream, Stream, instance;

  beforeEach(inject(function (_immutableStream_) {
    immutableStream = _immutableStream_;

    Stream = {
      setup: jasmine.createSpy('setup').andReturn({
        startStreaming: jasmine.createSpy('startStreaming'),
        end: jasmine.createSpy('end')
      })
    };

    instance = immutableStream(Stream, 'foo', {});
  }));

  it('should return a simplified stream wrapper', function () {
    expect(instance).toContainObject({
      start: jasmine.any(Function),
      end: jasmine.any(Function)
    });
  });

  it('should start streaming', function () {
    var params = {foo: 'bar'};

    instance.start(params);

    expect(Stream.setup).toHaveBeenCalledOnceWith('foo', {});
    expect(Stream.setup.plan().startStreaming)
      .toHaveBeenCalledOnceWith(params, undefined, undefined);
  });

  it('should not end if not started', function () {
    instance.end();

    expect(Stream.setup.plan().end).not.toHaveBeenCalled();
  });

  it('should end once started', function () {
    var params = {foo: 'bar'};

    instance.start(params);

    instance.end();

    expect(Stream.setup.plan().end).toHaveBeenCalledOnce();
  });

  it('should accept a stream method and transformers', function () {
    var instance = immutableStream(Stream, 'foo', {}, 'method', transformer);
    var params = {foo: 'bar'};

    function transformer() {}

    instance.start(params);

    expect(Stream.setup.plan().startStreaming)
      .toHaveBeenCalledOnceWith(params, 'method', transformer);
  });
});

describe('streams', function () {
  'use strict';

  function HostStream () {}
  function TargetStream() {}
  function FileSystemStream() {}

  beforeEach(module('streams', function ($provide) {
    $provide.value('immutableStream', jasmine.createSpy('immutableStream'));
  }, {
    HostStream: HostStream,
    TargetStream: TargetStream,
    FileSystemStream: FileSystemStream
  }));

  var streams, immutableStream;

  beforeEach(inject(function (_streams_, _immutableStream_) {
    streams = _streams_;
    immutableStream = _immutableStream_;
  }));

  it('should create an immutable stream', function () {
    streams.hostStream('foo.bar', {});

    expect(immutableStream).toHaveBeenCalledOnceWith(HostStream, 'foo.bar', {});
  });
});