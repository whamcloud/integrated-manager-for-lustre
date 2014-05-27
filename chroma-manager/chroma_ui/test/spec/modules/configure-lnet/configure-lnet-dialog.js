describe('configure lnet dialog', function () {
  'use strict';

  beforeEach(module('configureLnet'));

  var $scope, deferreds, lnetScope, dialog, hostInfo, NetworkInterface, LNET_OPTIONS, pollHost, poller;

  beforeEach(inject(function ($controller, $rootScope, $q) {
    $scope = $rootScope.$new();

    deferreds = {};

    NetworkInterface = {
      query: jasmine.createSpy('query').andCallFake(function () {
        var deferred = $q.defer();

        deferreds.query = deferred;

        return { $promise: deferred.promise };
      }),
      updateInterfaces: jasmine.createSpy('updateInterfaces').andCallFake(function () {
        var deferred = $q.defer();

        deferreds.updateInterfaces = deferred;

        return deferred.promise;
      })
    };

    var waitForCommand = jasmine.createSpy('waitForCommand').andCallFake(function () {
      var deferred = $q.defer();

      deferreds.waitForCommand = deferred;

      return deferred.promise;
    });

    LNET_OPTIONS = {};

    pollHost = jasmine.createSpy('pollHost').andCallFake(function () {
      var deferred = $q.defer();

      deferreds.pollHost = deferred;

      poller = {
        promise: deferred.promise,
        cancel: jasmine.createSpy('cancel')
      };

      return poller;
    });

    dialog = {
      close: jasmine.createSpy('close'),
      deferred: $q.defer()
    };

    hostInfo = {
      memberOfActiveFilesystem: false,
      hostId: 3,
      hostName: 'foo'
    };

    $controller('ConfigureLnetCtrl', {
      $scope: $scope,
      dialog: dialog,
      NetworkInterface: NetworkInterface,
      waitForCommand: waitForCommand,
      pollHost: pollHost,
      LNET_OPTIONS: LNET_OPTIONS,
      hostInfo: hostInfo
    });

    lnetScope = $scope.configureLnetCtrl;
  }));

  it('should close the dialog', function () {
    lnetScope.close();

    expect(dialog.close).toHaveBeenCalledOnce();
  });

  it('should cancel polling when the dialog closes', function () {
    dialog.deferred.resolve();

    $scope.$apply();

    expect(poller.cancel).toHaveBeenCalledOnce();
  });

  it('should poll the host', function () {
    expect(pollHost).toHaveBeenCalledOnceWith({ hostId: hostInfo.hostId });
  });

  describe('when saving', function () {
    beforeEach(function () {
      lnetScope.save();
    });

    it('should save the nids', function () {
      expect(NetworkInterface.updateInterfaces).toHaveBeenCalledOnce();
    });

    it('should close the dialog on success', function () {
      deferreds.updateInterfaces.resolve({
        command: {}
      });

      $scope.$apply();

      deferreds.waitForCommand.resolve();

      $scope.$apply();

      expect(dialog.close).toHaveBeenCalledOnce();
    });

    it('should set the message to Saving', function () {
      expect(lnetScope.message).toBe('Saving');
    });
  });

  describe('data fetched', function () {
    var resp;

    beforeEach(function () {
      resp = { resp: 'my resp' };

      deferreds.query.resolve(resp);

      $scope.$apply();
    });

    it('should set the resp on the scope', function () {
      expect(lnetScope.networkInterfaces).toEqual(resp);
    });

    it('should set resolved to true when data has resolved and host has notified', function () {
      deferreds.pollHost.notify({});

      $scope.$apply();

      expect(lnetScope.resolved).toBe(true);
    });
  });

  it('should fetch for a host', function () {
    expect(NetworkInterface.query).toHaveBeenCalledOnceWith({ host__id: hostInfo.hostId });
  });

  it('should assign LNET_OPTIONS to the scope', function () {
    expect(lnetScope.options).toBe(LNET_OPTIONS);
  });

  it('should assign hostName to the scope', function () {
    expect(lnetScope.hostName).toBe('foo');
  });
});
