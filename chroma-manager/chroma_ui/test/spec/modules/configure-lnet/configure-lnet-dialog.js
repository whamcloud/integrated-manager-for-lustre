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

describe('Remove used LNet options', function () {
  'use strict';

  beforeEach(module('configureLnet'));

  var removeUsedLnetOptions, LNET_OPTIONS;

  beforeEach(inject(function (_removeUsedLnetOptionsFilter_, _LNET_OPTIONS_) {
    removeUsedLnetOptions = _removeUsedLnetOptionsFilter_;
    LNET_OPTIONS = _LNET_OPTIONS_;
  }));

  it('should filter out used values', function () {
    var networkInterfaces = createNetworkInterfaces([5, 6, 7]);
    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterfaces[0]);

    expect(filtered).toEqual([
      { name: 'Not Lustre Network', value: -1 },
      { name: 'Lustre Network 0', value: 0 },
      { name: 'Lustre Network 1', value: 1 },
      { name: 'Lustre Network 2', value: 2 },
      { name: 'Lustre Network 3', value: 3 },
      { name: 'Lustre Network 4', value: 4 },
      { name: 'Lustre Network 5', value: 5 },
      { name: 'Lustre Network 8', value: 8 },
      { name: 'Lustre Network 9', value: 9 }
    ]);
  });

  it('should always have Not Lustre Network', function () {
    var networkInterface = createNetworkInterface(-1);
    var networkInterface0 = createNetworkInterface(0);
    var networkInterfaces = [networkInterface, networkInterface, networkInterface0];

    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterface0);

    expect(filtered).toEqual(_.toArray(LNET_OPTIONS));
  });

  it('should work when all options are used', function () {
    var values = _.pluck(LNET_OPTIONS, 'value');
    var networkInterfaces = createNetworkInterfaces(values);
    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterfaces[1]);

    expect(filtered).toEqual([ { name : 'Not Lustre Network', value : -1 }, { name : 'Lustre Network 0', value : 0 } ]);
  });

  /**
   * Creates an object representing a network interface
   * @param {Number} id
   * @returns {{nid: {lnd_network: Number}}}
   */
  function createNetworkInterface (id) {
    return { nid: {lnd_network: id} };
  }

  /**
   * Creates a list of objects representing network interfaces.
   * @param {Array} ids
   * @returns {Array<Object>}
   */
  function createNetworkInterfaces (ids) {
    return ids.map(function create (id) {
      return createNetworkInterface(id);
    });
  }
});
