describe('replay', function () {
  'use strict';

  var replay, $httpBackend, $rootScope, config, anyPromise, anyDeferred, spy;

  beforeEach(module('exception', function ($httpProvider) {
    //Not interested in testing any interceptors here.
    $httpProvider.interceptors.splice(0, $httpProvider.interceptors.length);
  }));

  beforeEach(inject(function (_replay_, _$httpBackend_, _$rootScope_) {
    replay = _replay_;
    $httpBackend = _$httpBackend_;
    $rootScope = _$rootScope_;

    spy = jasmine.createSpy('spy');

    config = {
      method: 'GET',
      url: '/accept'
    };

    anyPromise = {
      then: jasmine.any(Function),
      catch: jasmine.any(Function),
      finally: jasmine.any(Function)
    };

    anyDeferred = {
      resolve: jasmine.any(Function),
      reject: jasmine.any(Function),
      notify: jasmine.any(Function),
      promise: anyPromise
    };

    $httpBackend.whenGET('/accept').respond(200, {});
    $httpBackend.whenPUT('/accept').respond(204, {});
    $httpBackend.whenDELETE('/accept').respond(204, {});

    $httpBackend.whenGET('/reject').respond(0);
    $httpBackend.whenPUT('/reject').respond(0);
    $httpBackend.whenDELETE('/reject').respond(0);
    $httpBackend.whenDELETE('/reject_with_server_error').respond(500);
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should have a property that indicates if there are pending replays', function () {
    expect(replay.hasPending).toBe(false);
  });

  it('should have a method to tell if a verb is idempotent', function () {
    expect(replay.isIdempotent(config)).toBe(true);
  });

  it('should return false if a method is not idempotent', function () {
    expect(replay.isIdempotent({method: 'POST'})).toBe(false);
  });

  it('should throw in isIdempotent if the config is not structured as expected', function () {
    var shouldThrow = replay.isIdempotent.bind(replay, {});

    expect(shouldThrow).toThrow();
  });

  it('should accurately show if there are pending requests', function () {
    replay.add(config);

    expect(replay.hasPending).toBe(true);
  });

  it('should throw in add if a non-idempotent verb is passed', function () {
    var shouldThrow = replay.add.bind(replay, {method: 'POST', url: '/doesntmatter'});

    expect(shouldThrow).toThrow();
  });

  describe('adding a response', function () {
    var result;

    beforeEach(function () {
      result = replay.add(config);
    });

    it('should store it', function () {
      expect(replay._pending[0]).toEqual({
        config: config,
        deferred: anyDeferred
      });
    });

    it('should return a promise', function () {
      expect(result).toEqual(anyPromise);
    });
  });

  describe('replaying a response', function () {
    var promise;

    beforeEach(function () {
      promise = replay.add(config);
    });

    it('should resolve the returned promise', function () {
      replay.go();

      $httpBackend.flush();

      promise.then(spy);

      $rootScope.$digest();

      expect(spy).toHaveBeenCalled();
    });

    it('should return a promise that resolves after replay completes', function () {
      var goPromise = replay.go();

      $httpBackend.flush();

      goPromise.then(spy);

      $rootScope.$digest();

      expect(spy).toHaveBeenCalled();
    });
  });

  describe('replaying responses', function () {
    var spy, goPromise,
      promises = [];

    beforeEach(function () {
      spy = jasmine.createSpy('spy');

      promises.push(replay.add({method: 'GET', url: '/accept'}));
      promises.push(replay.add({method: 'DELETE', url: '/reject_with_server_error'}));
      promises.push(replay.add({method: 'DELETE', url: '/reject'}));
      promises.push(replay.add({method: 'PUT', url: '/accept'}));

      goPromise = replay.go();

      $httpBackend.flush();
    });

    it('should stop on a rejected request with a 0 status', function () {
      promises[1].then(spy);

      $rootScope.$digest();

      expect(spy).not.toHaveBeenCalled();
    });

    it('should not remove pending promises', function () {
      $rootScope.$digest();

      expect(replay._pending).toEqual([
        {
          config: {method: 'DELETE', url: '/reject', UI_REPLAY: true},
          deferred: anyDeferred
        },
        {
          config: {method: 'PUT', url: '/accept', UI_REPLAY: true},
          deferred: anyDeferred
        }
      ]);
    });

    it('should reject the promise returned from go when a 0 status is returned', function () {
      goPromise.catch(spy);

      $rootScope.$digest();

      expect(spy).toHaveBeenCalled();
    });
  });
});
