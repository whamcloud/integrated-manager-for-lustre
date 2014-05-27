describe('wait for command', function () {
  'use strict';

  var deferreds;

  beforeEach(module('configureLnet', function ($provide) {
    deferreds = [];

    $provide.factory('commandModel', function ($q) {
      return {
        get: jasmine.createSpy('get').andCallFake(function () {
          var deferred = $q.defer();

          deferreds.push(deferred);

          return {$promise: deferred.promise};
        })
      };
    });
  }));

  var $rootScope, waitForCommand, commandModel, startingCommand;

  beforeEach(inject(function (_waitForCommand_, _commandModel_, _$rootScope_) {
    waitForCommand = _waitForCommand_;
    commandModel = _commandModel_;
    $rootScope = _$rootScope_;

    startingCommand = {
      cancelled: false,
      complete: false,
      created_at: '2014-05-27T15:28:19.313508+00:00',
      dismissed: false,
      errored: false,
      id: 12,
      jobs: [
        '/api/job/52/',
        '/api/job/53/',
        '/api/job/54/'
      ],
      logs: '',
      message: 'Configuring NIDS for hosts',
      resource_uri: '/api/command/12/'
    };
  }));

  it('should be a function', function () {
    expect(waitForCommand).toEqual(jasmine.any(Function));
  });

  it('should pass through if command is already completed', function () {
    startingCommand.complete = true;

    waitForCommand(startingCommand);

    expect(commandModel.get).not.toHaveBeenCalled();
  });

  it('should pass through if command is canceled', function () {
    startingCommand.cancelled = true;

    waitForCommand(startingCommand);

    expect(commandModel.get).not.toHaveBeenCalled();
  });

  it('should pass through if command is errored', function () {
    startingCommand.errored = true;

    waitForCommand(startingCommand);

    expect(commandModel.get).not.toHaveBeenCalled();
  });

  it('should get the command', function () {
    waitForCommand(startingCommand);

    expect(commandModel.get).toHaveBeenCalledWith({ commandId: 12 });
  });

  it('should return a promise', function () {
    var promise = waitForCommand(startingCommand);

    expect(promise).toEqual({
      then: jasmine.any(Function),
      catch: jasmine.any(Function),
      finally: jasmine.any(Function)
    });
  });

  it('should resolve with the response', function () {
    var promise = waitForCommand(startingCommand);

    deferreds[0].resolve({
      command: { complete: true }
    });

    promise.then(function (response) {
      expect(response).toEqual({
        command: { complete: true }
      });
    });
    $rootScope.$apply();
  });

  it('should turn twice if the first call does not finish', function () {
    var promise = waitForCommand(startingCommand);

    deferreds[0].resolve({
      command: {
        id: 12,
        complete: false,
        cancelled: false,
        errored: false
      }
    });

    $rootScope.$apply();

    deferreds[1].resolve({
      command: { complete: true }
    });

    promise.then(function (response) {
      expect(response).toEqual({
        command: { complete: true }
      });
    });
    $rootScope.$apply();
  });
});
