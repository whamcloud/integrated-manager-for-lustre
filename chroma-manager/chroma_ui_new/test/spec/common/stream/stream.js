describe('stream module', function () {
  'use strict';

  beforeEach(module('stream', 'mockPrimus', function ($provide) {
    $provide.factory('pageVisibility', function () {
      return {
        onChange: jasmine.createSpy('pageVisibility.onChange').andReturn(
          jasmine.createSpy('deregister')
        )
      };
    });
  }, {
    $document: [{cookie: 'csrftoken=F0bJQGBt7BmzAicFJiBnmTqbuywPjXUs; sessionid=42e56defe7d851d28b7175a3e17cc419'}],
    BASE: 'https://a.b.com'
  }));

  var $document, $scope, stream, primus, pageVisibility, expression;

  beforeEach(inject(function (_$document_, $rootScope, _stream_, _primus_, _pageVisibility_) {
    primus = _primus_;
    stream = _stream_;
    pageVisibility = _pageVisibility_;
    $document = _$document_;
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
      expect(primus.plan().channel).toHaveBeenCalledOnceWith('foo');
    });

    it('should expose the channel as a property', function () {
      expect(streamInstance.channel).toBe(primus.plan().channel.plan());
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

      expect(primus.plan().removeListener).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
    });

    it('should merge params with authHeaders', function () {
      streamInstance.startStreaming({
        headers: { 'X-Foo': 'bar' },
        qs: { param: 'value' }
      }, 'fakeStreamMethod');

      var beforeStreamingFunc = getChannelListener(primus, 'beforeStreaming');
      var cb = jasmine.createSpy('cb');

      beforeStreamingFunc(cb);

      expect(cb).toHaveBeenCalledOnceWith('fakeStreamMethod', {
        headers: {
          'X-Foo': 'bar',
          Cookie: $document[0].cookie
        },
        qs: { param: 'value' }
      });
    });

    describe('startStreaming', function () {
      beforeEach(function () {
        streamInstance.startStreaming({}, 'fakeStreamMethod');
      });

      it('should register a stream handler to the channel', function () {
        expect(primus.plan().channel.plan().on).toHaveBeenCalledWith('stream', jasmine.any(Function));
      });

      it('should register a beforeStreaming handler to the channel', function () {
        expect(primus.plan().channel.plan().on).toHaveBeenCalledWith('beforeStreaming', jasmine.any(Function));
      });

      it('should send a startStreaming messge', function () {
        expect(primus.plan().channel.plan().send).toHaveBeenCalledOnceWith('startStreaming');
      });

      it('should add a listener that restarts the stream on open', function () {
        expect(primus.plan().on).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
      });

      it('should add a listener that toggles the stream when page visibility changes', function () {
        expect(pageVisibility.onChange).toHaveBeenCalledOnceWith(jasmine.any(Function));
      });

      it('should stop the stream if the page is hidden', function () {
        var cb = pageVisibility.onChange.mostRecentCall.args[0];

        cb(true);

        expect(primus.plan().channel.plan().send).toHaveBeenCalledOnceWith('stopStreaming');
      });

      it('should start the stream if the page is not hidden', function () {
        var cb = pageVisibility.onChange.mostRecentCall.args[0];

        cb(false);

        expect(primus.plan().channel.plan().send).toHaveBeenCalledTwiceWith('startStreaming');
      });

      it('should call the callback with method and params beforeStreaming', function () {
        var beforeStreamingFunc = getChannelListener(primus, 'beforeStreaming');
        var cb = jasmine.createSpy('cb');

        beforeStreamingFunc(cb);

        expect(cb).toHaveBeenCalledOnceWith('fakeStreamMethod', {
          headers: {
            Cookie: $document[0].cookie
          }
        });
      });

      it('should run the transformers when new stream data comes in', function () {
        var streamFunc = getChannelListener(primus, 'stream');
        var resp = { body: [] };

        streamFunc(resp);

        expect(resp).toEqual({ body: 'Duck' });
      });

      describe('stop streaming', function () {
        var cb;

        beforeEach(function () {
          cb = jasmine.createSpy('cb');

          streamInstance.stopStreaming(cb);
        });

        it('should send stopStreaming', function () {
          expect(primus.plan().channel.plan().send).toHaveBeenCalledWith('stopStreaming', cb);
        });

        it('should remove the stream listener from the channel', function () {
          expect(primus.plan().channel.plan().removeAllListeners).toHaveBeenCalledWith('stream');
        });

        it('should remove the beforeStreaming listener from the channel', function () {
          expect(primus.plan().channel.plan().removeAllListeners).toHaveBeenCalledWith('beforeStreaming');
        });

        it('should remove the open listener from primus', function () {
          expect(primus.plan().removeListener).toHaveBeenCalledOnceWith('open', jasmine.any(Function));
        });

        it('should remove the page visibility listener from the page visibility service', function () {
          var deregister = pageVisibility.onChange.plan();

          expect(deregister).toHaveBeenCalledOnce();
        });
      });


      describe('restart', function () {
        beforeEach(function () {
          streamInstance.restart();
        });

        it('should stop the stream', function () {
          expect(primus.plan().channel.plan().send).toHaveBeenCalledOnceWith('stopStreaming', jasmine.any(Function));
        });

        it('should not start the stream until stop calls back', function () {
          expect(primus.plan().channel.plan().send).toHaveBeenCalledOnceWith('startStreaming');
        });

        it('should start the stream', function () {
          var stopStreamingFunc = getChannelListener(primus, 'stopStreaming', 'send');
          stopStreamingFunc();

          expect(primus.plan().channel.plan().send).toHaveBeenCalledTwiceWith('startStreaming');
        });
      });
    });

    describe('prependTransformers', function () {
      var response;

      beforeEach(function () {
        streamInstance.startStreaming({}, 'fakeStreamMethod', function (resp) {
          response = _.clone(resp);

          return resp;
        });
      });

      it('should call the prepend transformer', function () {
        var streamFunc = getChannelListener(primus, 'stream');
        streamFunc({ body: [] });

        expect(response).toEqual({ body: [] });
      });
    });

    describe('destroy', function () {
      beforeEach(function () {
        $scope.$destroy();
      });

      it('should end the channel', function () {
        expect(primus.plan().channel.plan().end).toHaveBeenCalledOnce();
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

describe('beforeStreamingDuration', function () {
  'use strict';

  beforeEach(module('stream', 'mockServerMoment'));

  var getServerMoment, beforeStreamingDuration, makeRequest;

  beforeEach(inject(function (_getServerMoment_, _beforeStreamingDuration_) {
    getServerMoment = _getServerMoment_;
    beforeStreamingDuration = _beforeStreamingDuration_;
    makeRequest = jasmine.createSpy('makeRequest');
  }));

  it('should not add begin and end if there is no querystring', function () {
    var makeRequest = jasmine.createSpy('makeRequest');

    beforeStreamingDuration('foo', {}, makeRequest);

    expect(makeRequest).toHaveBeenCalledOnceWith('foo', {});
  });

  it('should set the server moment milliseconds to zero', function () {
    beforeStreamingDuration('foo', {
      qs: {
        size: 10,
        unit: 'minutes'
      }
    }, makeRequest);

    expect(getServerMoment.plan().milliseconds).toHaveBeenCalledOnceWith(0);
  });

  it('should subtract size and unit', function () {
    beforeStreamingDuration('foo', {
      qs: {
        size: 10,
        unit: 'minutes'
      }
    }, makeRequest);

    expect(getServerMoment.plan().subtract).toHaveBeenCalledOnceWith(10, 'minutes');
  });

  it('should add begin and end to querystring', function () {
    var end = '2014-04-29T05:33:38.533Z';
    var begin = '2014-04-29T05:23:38.533Z';

    getServerMoment.plan().toISOString.andCallFake(function () {
      /*jshint validthis: true */
      switch (this.toISOString.callCount) {
        case 1:
          return end;
        case 2:
          return begin;
      }
    });

    beforeStreamingDuration('foo', {
      qs: {
        size: 10,
        unit: 'minutes'
      }
    }, makeRequest);

    expect(makeRequest).toHaveBeenCalledOnceWith('foo', {
      qs: {
        size: 10,
        unit: 'minutes',
        begin: begin,
        end: end
      }
    });
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

/**
 * Given a primus mock, returns the event listener registered to it's channel
 * @param {Object} primus
 * @param {String} eventName
 * @param {String} [type]
 * @returns {Function}
 */
function getChannelListener (primus, eventName, type) {
  'use strict';

  if (type == null)
    type = 'on';

  var match = primus.plan().channel.plan()[type].mostRecentCallThat(function findMatch(call) {
    return call.args[0] === eventName;
  });

  return match.args[1];
}
