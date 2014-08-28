describe('request socket', function () {
  'use strict';

  var socket;

  beforeEach(module('socket-module', function ($provide) {
    socket = jasmine.createSpy('socket').andReturn({
      send: jasmine.createSpy('send')
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
          path : '/command',
          options : {
            method : verb
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
