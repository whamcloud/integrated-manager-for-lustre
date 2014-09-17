describe('Add Modal Controller', function () {
  'use strict';

  var $scope, resultEndPromise;
  var steps = {};

  beforeEach(module('server'));

  beforeEach(inject(function ($rootScope, $controller, $q) {
    resultEndPromise = $q.defer();

    var stepsManager = jasmine.createSpy('stepsManager').andReturn({
      addStep: jasmine.createSpy('addStep'),
      start: jasmine.createSpy('start'),
      result: {
        end: resultEndPromise.promise
      },
      destroy: jasmine.createSpy('destroy')
    });

    Object.keys(stepsManager.plan()).forEach(function (key) {
      if (stepsManager.plan()[key].andReturn)
        stepsManager.plan()[key].andReturn(stepsManager.plan());
    });

    steps.flint = {
      destroy: jasmine.createSpy('destroy')
    };

    steps.$modalInstance = {
      close: jasmine.createSpy('$modalInstance')
    };
    steps.stepsManager = stepsManager;
    steps.addServersStep = jasmine.createSpy('addServersStep');
    steps.serverStatusStep = jasmine.createSpy('serverStatusStep');
    steps.selectServerProfileStep = jasmine.createSpy('selectServerProfileStep');
    steps.server = jasmine.createSpy('server');
    steps.regenerator = jasmine.createSpy('regenerator').andReturn(steps.flint);
    steps.requestSocket = jasmine.createSpy('requestSocket');

    $scope = $rootScope.$new();
    $scope.$on = jasmine.createSpy('$on');

    $controller('AddServerModalCtrl', {
      $scope: $scope,
      $modalInstance: steps.$modalInstance,
      stepsManager: steps.stepsManager,
      addServersStep: steps.addServersStep,
      serverStatusStep: steps.serverStatusStep,
      selectServerProfileStep: steps.selectServerProfileStep,
      server: steps.server,
      regenerator: steps.regenerator,
      requestSocket: steps.requestSocket
    });
  }));

  it('should invoke regenerator', function () {
    expect(steps.regenerator).toHaveBeenCalledOnceWith(jasmine.any(Function), jasmine.any(Function));
  });

  it('should invoke the steps manager', function () {
    expect(steps.stepsManager).toHaveBeenCalled();
  });

  [
    'addServersStep',
    'serverStatusStep',
    'selectServerProfileStep'
  ].forEach(function (step) {
      it('should add step ' + step, function () {
        expect(steps.stepsManager.plan().addStep).toHaveBeenCalledOnceWith(step, steps[step]);
      });
    });

  it('should start the steps manager', function () {
    expect(steps.stepsManager.plan().start).toHaveBeenCalledOnceWith('addServersStep', {
      data: {
        server: steps.server,
        flint: steps.flint
      }
    });
  });

  it('should close the modal instance when the manager result ends', function () {
    resultEndPromise.resolve('test');

    $scope.$digest();
    expect(steps.$modalInstance.close).toHaveBeenCalledOnce();
  });

  it('should contain the manager', function () {
    expect($scope.addServer.manager).toEqual(steps.stepsManager.plan());
  });

  it('should set an on destroy event listener', function () {
    expect($scope.$on).toHaveBeenCalledWith('$destroy', jasmine.any(Function));
  });

  describe('on destroy', function () {
    beforeEach(function () {
      $scope.$on.mostRecentCall.args[1]();
    });

    it('should destroy the manager', function () {
      expect(steps.stepsManager.plan().destroy).toHaveBeenCalledOnce();
    });

    it('should destroy flint', function () {
      expect(steps.flint.destroy).toHaveBeenCalledOnce();
    });
  });
});

describe('openAddServerModal', function () {
  'use strict';

  var openAddServerModal, $modal, server, response, $q, $rootScope;
  beforeEach(module('server', function ($provide) {
    $modal = {
      open: jasmine.createSpy('$modal')
    };

    $provide.value('$modal', $modal);
  }));

  beforeEach(inject(function (_openAddServerModal_, _$q_, _$rootScope_) {
    server = 'hostname1';
    openAddServerModal = _openAddServerModal_;
    $q = _$q_;
    $rootScope = _$rootScope_;
    response = openAddServerModal(server);
  }));

  it('should open the modal', function () {
    expect($modal.open).toHaveBeenCalledWith({
      templateUrl: 'iml/server/assets/html/add-server-modal.html',
      controller: 'AddServerModalCtrl',
      windowClass: 'add-server-modal',
      resolve: {
        server: jasmine.any(Function)
      }
    });
  });

  describe('handling resolve', function () {
    var resolve;
    beforeEach(function () {
      resolve = $modal.open.mostRecentCall.args[0].resolve;
    });

    it('should return server', function () {
      expect(resolve.server()).toEqual(server);
    });
  });
});

describe('Create Hosts', function () {
  'use strict';

  var $q, createHosts, requestSocket, serverData, spark,
    sendPostDeferred, expandedServerData, $rootScope;

  beforeEach(module('server', function ($provide) {
    requestSocket = jasmine.createSpy('requestSocket');

    $provide.value('requestSocket', requestSocket);

    $provide.decorator('requestSocket', function ($q, $delegate) {
      sendPostDeferred = $q.defer();
      spark = {
        sendPost: jasmine.createSpy('sendPost').andReturn(sendPostDeferred.promise),
        end: jasmine.createSpy('end')
      };
      return $delegate.andReturn(spark);
    });
  }));

  beforeEach(inject(function (_$q_, _createHosts_, _$rootScope_) {
    $q = _$q_;
    $rootScope = _$rootScope_;
    createHosts = _createHosts_;

    serverData = {
      address: ['one', 'two', 'three'],
      extra: 'extra'
    };

    expandedServerData = [
      {
        address: 'one',
        extra: 'extra'
      },
      {
        address: 'two',
        extra: 'extra'
      },
      {
        address: 'three',
        extra: 'extra'
      }
    ];

    createHosts(serverData);
  }));

  it('should call request socket', function () {
    expect(requestSocket).toHaveBeenCalledOnce();
  });

  it('should send post to /host', function () {
    expect(spark.sendPost).toHaveBeenCalledWith('/host', { json: { objects: expandedServerData } }, true);
  });

  describe('no errors', function () {
    var response = {
      body: {
        objects: [
          {
            command: 'command1',
            host: 'host1'
          }
        ]
      }
    };

    beforeEach(function () {
      sendPostDeferred.resolve(response);
      $rootScope.$digest();
    });

    it('should call end on the spark', function () {
      expect(spark.end).toHaveBeenCalledOnce();
    });
  });

  describe('errors', function () {
    var response = {
      body: {
        errors: [
          { msg: 'error' }
        ]
      }
    };

    it('should throw exception', function () {
      try {
        sendPostDeferred.resolve(response);
        $rootScope.$digest();
      } catch (e) {
        expect(e.message).toEqual('[{"msg":"error"}]');
      }
    });
  });
});

describe('Host Profile', function () {
  'use strict';

  var hostProfile, flint, hosts, spark, result;
  beforeEach(module('server'));

  beforeEach(inject(function (_hostProfile_) {
    hostProfile = _hostProfile_;

    spark = {
      sendGet: jasmine.createSpy('sendGet')
    };
    flint = jasmine.createSpy('flint').andReturn(spark);

    hosts = [
      {id: '1'},
      {id: '2'}
    ];

    result = hostProfile(flint, hosts);
  }));

  it('should invoke flint', function () {
    expect(flint).toHaveBeenCalledOnceWith('hostProfile');
  });

  it('should call spark.sendGet', function () {
    expect(spark.sendGet).toHaveBeenCalledOnceWith('/host_profile', {
      qs: {
        id__in: ['1', '2']
      }
    });
  });

  it('should return the spark', function () {
    expect(result).toEqual(spark);
  });

});

describe('testHost', function () {
  'use strict';

  var flint, spark, testHost, data, result;
  beforeEach(module('server'));

  beforeEach(inject(function (_testHost_) {
    testHost = _testHost_;

    spark = {
      sendPost: jasmine.createSpy('sendPost'),
      addPipe: jasmine.createSpy('addPipe')
    };
    flint = jasmine.createSpy('flint').andReturn(spark);
    data = 'my data';
    result = testHost(flint, data);
  }));

  it('should call sendPost', function () {
    expect(spark.sendPost).toHaveBeenCalledWith('/test_host', {json: data});
  });

  it('should return a spark', function () {
    expect(result).toEqual(spark);
  });

  describe('invoking the pipe', function () {
    var response = {
      body: {
        objects: [
          {
            field1: 'value1',
            address: 'address1',
            key_with_underscore: 'underscore_value'
          }
        ]
      }
    };

    beforeEach(function () {
      response = spark.addPipe.mostRecentCall.args[0](response);
    });

    it('should indicate that the response is valid', function () {
      expect(response.body.isValid).toEqual(true);
    });

    it('should have an updated response value', function () {
      expect(response).toEqual({
        body: {
          objects: [
            {
              field1: 'value1',
              address: 'address1',
              key_with_underscore: 'underscore_value',
              fields: {
                Field1: 'value1',
                'Key with underscore': 'underscore_value',
                Fields: { Field1: 'value1',
                  'Key with underscore': 'underscore_value'
                },
                Invalid: false
              },
              invalid: true
            }
          ],
          isValid: false
        }
      });
    });
  });
});

describe('regenerator', function () {
  'use strict';

  var regenerator, setup, teardown, getter;
  beforeEach(module('server'));

  beforeEach(inject(function (_regenerator_) {
    regenerator = _regenerator_;

    setup = jasmine.createSpy('setup').andReturn('setup');
    teardown = jasmine.createSpy('teardown');
    getter = regenerator(setup, teardown);
  }));

  describe('getting an object from the cache', function () {
    var item;

    describe('item hasn\'t been created in the cache yet', function () {
      beforeEach(function () {
        item = getter('item');
      });

      it('should not call the tear down function', function () {
        expect(teardown).not.toHaveBeenCalled();
      });

      it('should call the setup function', function () {
        expect(setup).toHaveBeenCalledOnce();
      });
    });

    describe('item already in the cache', function () {
      beforeEach(function () {
        _.times(2, _.partial(getter, 'item'));
      });

      it('should call the teardown function once', function () {
        expect(teardown).toHaveBeenCalledOnceWith('setup');
      });

      it('should call setup twice', function () {
        expect(setup).toHaveBeenCalledTwice();
      });
    });
  });

  describe('destroying the objects in the cache', function () {
    beforeEach(function () {
      getter('item');
      getter.destroy();
    });

    it('should call tear down', function () {
      expect(teardown).toHaveBeenCalledOnce();
    });
  });
});
