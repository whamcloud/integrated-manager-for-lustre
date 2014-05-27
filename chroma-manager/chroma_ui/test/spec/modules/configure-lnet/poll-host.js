describe('poll host', function () {
  'use strict';

  var hostModelDeferred;

  beforeEach(module('configureLnet', function ($provide) {
    hostModelDeferred = null;

    $provide.factory('hostModel', function ($q) {
      return {
        get: jasmine.createSpy('get').andCallFake(function () {
          var deferred = $q.defer();

          hostModelDeferred = deferred;

          return {$promise: deferred.promise};
        })
      };
    });
  }));

  var $timeout, $rootScope, pollHost, hostModel;

  beforeEach(inject(function (_$timeout_, _$rootScope_, _pollHost_, _hostModel_) {
    $timeout = _$timeout_;
    $rootScope = _$rootScope_;
    pollHost = _pollHost_;
    hostModel = _hostModel_;
  }));

  it('should return a function', function () {
    expect(pollHost).toEqual(jasmine.any(Function));
  });

  it('should return an object to work with the poll', function () {
    var poller = pollHost({});

    expect(poller).toEqual({
      promise: jasmine.any(Object),
      cancel: jasmine.any(Function)
    });
  });

  it('should get the host', function () {
    pollHost({});



    expect(hostModel.get).toHaveBeenCalledOnceWith({});
  });

  it('should notify with the host response', function () {
    var poller = pollHost({});

    $timeout.flush(5000);

    hostModelDeferred.resolve({
      id: 5
    });

    poller.promise.then(null, null, function notifier (response) {
      expect(response).toEqual({id : 5});
    });

    $rootScope.$apply();
  });

  it('should not check again when cancelled', function () {
    var poller = pollHost({});

    $rootScope.$apply(function () {
      hostModelDeferred.resolve({
        id: 6
      });
    });

    poller.cancel();

    $timeout.flush(5000);

    $timeout.verifyNoPendingTasks();
  });
});
