describe('request socket', function () {
  'use strict';

  var socket;

  beforeEach(module('socket-module', function ($provide) {
    socket = jasmine.createSpy('socket').andReturn({
      send: jasmine.createSpy('send'),
      onceValue: jasmine.createSpy('onceValue')

    });

    $provide.value('socket', socket);
  }));

  var $rootScope, VERBS, requestSocket, spark;

  beforeEach(inject(function (_$rootScope_, _VERBS_, _requestSocket_) {
    $rootScope = _$rootScope_;
    VERBS = _VERBS_;
    requestSocket = _requestSocket_;
    spark = requestSocket();
  }));

  it('should have an object of verbs', function () {
    expect(VERBS).toEqual(Object.freeze({
      GET: 'get',
      PUT: 'put',
      POST: 'post',
      DELETE: 'delete',
      PATCH: 'patch'
    }));
  });

  it('should return a function', function () {
    expect(requestSocket).toEqual(jasmine.any(Function));
  });

  describe('onceValueThen', function () {
    var $rootScope, promise, off, spy, boundHandler;

    beforeEach(inject(function (_$rootScope_) {
      $rootScope = _$rootScope_;

      off = jasmine.createSpy('off');
      spark.onceValue.andCallFake(function (event, handler) {
        boundHandler = handler.bind({
          off: off
        });
      });

      promise = spark.onceValueThen('pipeline');

      spy = jasmine.createSpy('spy');
    }));

    it('should be exposed on the spark', function () {
      expect(spark.onceValueThen).toEqual(jasmine.any(Function));
    });

    it('should return a promise', function () {
      expect(promise).toEqual({
        then: jasmine.any(Function),
        catch: jasmine.any(Function),
        finally: jasmine.any(Function)
      });
    });

    it('should stop listening on response', function () {
      boundHandler({});

      expect(off).toHaveBeenCalledOnce();
    });

    it('should resolve on success', function () {
      promise.then(spy);

      boundHandler({});
      $rootScope.$digest();

      expect(spy).toHaveBeenCalledOnce();
    });

    it('should reject on error', function () {
      promise.catch(spy);

      boundHandler({
        error: {message: 'Oh NOES!'}
      });
      $rootScope.$digest();

      expect(spy).toHaveBeenCalledOnce();
    });
  });

  ['get', 'put', 'post', 'delete', 'patch'].forEach(function (verb) {
    describe('sending verbs', function () {
      var method;
      var methodName = 'send' + _.capitalize(verb);

      beforeEach(function () {
        method = spark[methodName];
      });

      it('should add a ' + verb + 'method to the spark', function () {
        expect(method).toEqual(jasmine.any(Function));
      });

      it('should send data as expected for ' + verb, function () {
        method('/api/command');

        expect(spark.send).toHaveBeenCalledOnceWith('req', {
          path: '/command',
          options: {
            method: verb
          }
        }, undefined);
      });

      describe('working with promises', function () {
        var promise, ack;

        beforeEach(function () {
          promise = method('/job', {}, true);
          ack = spark.send.mostRecentCall.args[2];
        });

        it('should resolve for ' + verb, function () {
          var response = {
            body: {
              foo: 'bar'
            }
          };

          ack(response);

          promise.then(function (resp) {
            expect(resp).toEqual(response);
          });

          $rootScope.$apply();
        });

        it('should reject for ' + verb, function () {
          var response = {
            error: {}
          };

          ack(response);

          promise.catch(function (resp) {
            expect(resp).toEqual(response);
          });
        });
      });
    });
  });
});

describe('throw if error', function () {
  'use strict';

  beforeEach(module('socket-module'));

  var throwIfError, spy, check;

  beforeEach(inject(function (_throwIfError_) {
    throwIfError = _throwIfError_;

    spy = jasmine.createSpy('spy');

    check = throwIfError(spy);
  }));

  it('should be a function', function () {
    expect(throwIfError).toEqual(jasmine.any(Function));
  });

  it('should return a function', function () {
    expect(check).toEqual(jasmine.any(Function));
  });

  it('should throw on error', function () {
    expect(shouldThrow).toThrow();

    function shouldThrow () {
      check({ error: {} });
    }
  });

  it('should call spy', function () {
    check({});

    expect(spy).toHaveBeenCalledOnceWith({});
  });

  it('should return the response', function () {
    spy.andReturn({ foo: 'bar' });

    var response = check({});

    expect(response).toEqual({ foo: 'bar' });
  });
});

describe('throw response error', function () {
  'use strict';

  beforeEach(module('socket-module'));

  var throwResponseError;

  beforeEach(inject(function (_throwResponseError_) {
    throwResponseError = _throwResponseError_;
  }));

  it('should throw an existing error', function () {
    var err = new Error('foo');

    expect(shouldThrow).toThrow(err);

    function shouldThrow () {
      throwResponseError({
        error: err
      });
    }
  });

  it('should turn an object into an error', function () {
    expect(shouldThrow).toThrow(new Error('uh-oh'));

    function shouldThrow () {
      throwResponseError({
        error: {
          message: 'uh-oh'
        }
      });
    }
  });

  it('should copy any object properties onto the error object', function () {
    try {
      throwResponseError({
        error: {
          message: 'err!',
          statusCode: 400
        }
      });
    } catch (err) {
      expect(err.statusCode).toBe(400);
    }
  });

  it('should turn a string into an error', function () {
    expect(shouldThrow).toThrow(new Error('boom!'));

    function shouldThrow () {
      throwResponseError({
        error: 'boom!'
      });
    }
  });
});

describe('get flint', function () {
  'use strict';

  var regenerator, requestSocket;

  beforeEach(module('socket-module', function ($provide) {
    regenerator = jasmine.createSpy('regenerator');
    $provide.value('regenerator', regenerator);

    requestSocket = jasmine.createSpy('requestSocket');
    $provide.value('requestSocket', requestSocket);
  }));

  var flint;

  beforeEach(inject(function (_getFlint_) {
    flint = _getFlint_();
  }));

  it('should call regenerator with setup and teardown', function () {
    expect(regenerator).toHaveBeenCalledOnceWith(jasmine.any(Function), jasmine.any(Function));
  });

  it('should get a new requestSocket on setup', function () {
    regenerator.mostRecentCall.args[0]();

    expect(requestSocket).toHaveBeenCalledOnce();
  });

  it('should end the provided spark on teardown', function () {
    var spark = {
      end: jasmine.createSpy('end')
    };

    regenerator.mostRecentCall.args[1](spark);

    expect(spark.end).toHaveBeenCalledOnce();
  });
});
