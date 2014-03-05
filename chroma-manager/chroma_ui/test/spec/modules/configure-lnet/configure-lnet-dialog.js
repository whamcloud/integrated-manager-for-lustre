describe('configure lnet dialog', function () {
  'use strict';

  var lnetScope, dialog, NetworkInterface, hostId, queryThen, save, LNET_OPTIONS;

  beforeEach(module('configureLnet'));

  mock.beforeEach('$dialog');

  beforeEach(inject(function ($controller, $dialog, $rootScope) {
    var $scope = $rootScope.$new();

    queryThen = jasmine.createSpy('promise.then');
    save = jasmine.createSpy('save').andReturn({
      then: jasmine.createSpy('then')
    });

    NetworkInterface = {
      query: jasmine.createSpy('NetworkInterface.get').andReturn({
        $promise: {
          then: queryThen
        }
      }),
      updateInterfaces: save
    };

    LNET_OPTIONS = {};

    hostId = 3;

    $controller('ConfigureLnetCtrl', {
      $scope: $scope,
      dialog: $dialog.dialog({}),
      NetworkInterface: NetworkInterface,
      hostId: hostId,
      hostName: 'foo',
      LNET_OPTIONS: LNET_OPTIONS
    });

    dialog = $dialog.dialog;
    lnetScope = $scope.configureLnetCtrl;
  }));

  it('should close the dialog', function () {
    lnetScope.close();

    expect(dialog.spy.close).toHaveBeenCalledOnce();
  });

  describe('when saving', function () {
    beforeEach(function () {
      lnetScope.save();
    });

    it('should save the nids', function () {
      expect(save).toHaveBeenCalledOnce();
    });

    it('should close the dialog on success', function () {
      var close = save.plan().then.mostRecentCall.args[0];

      close();

      expect(dialog.spy.close).toHaveBeenCalledOnce();
    });

    it('should set the saving flag to true', function () {
      lnetScope.save();

      expect(lnetScope.saving).toBe(true);
    });
  });

  describe('data fetched', function () {
    var resp;

    beforeEach(function () {
      var thenCallback = queryThen.mostRecentCall.args[0];

      resp = {
        resp: 'my resp'
      };

      thenCallback(resp);
    });

    it('should set the resp on the scope', function () {
      expect(lnetScope.networkInterfaces).toEqual(resp);
    });

    it('should set resolved to true', function () {
      expect(lnetScope.resolved).toBe(true);
    });
  });

  it('should have a saving flag', function () {
    expect(lnetScope.saving).toBe(false);
  });

  it('should have a resolved flag', function () {
    expect(lnetScope.resolved).toBe(false);
  });

  it('should fetch for a host', function () {
    expect(NetworkInterface.query).toHaveBeenCalledOnceWith({
      host__id: hostId
    });
  });

  it('should assign LNET_OPTIONS to the scope', function () {
    expect(lnetScope.options).toBe(LNET_OPTIONS);
  });

  it('should assign hostName to the scope', function () {
    expect(lnetScope.hostName).toBe('foo');
  });
});
