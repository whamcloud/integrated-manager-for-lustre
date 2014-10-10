describe('add server modal ctrl', function () {
  'use strict';

  beforeEach(module('server'));

  describe('Add server steps constants', function () {
    var ADD_SERVER_STEPS;

    beforeEach(inject(function (_ADD_SERVER_STEPS_) {
      ADD_SERVER_STEPS = _ADD_SERVER_STEPS_;
    }));

    it('should contain the expected steps', function () {
      expect(ADD_SERVER_STEPS).toEqual(Object.freeze({
        ADD: 'addServersStep',
        STATUS: 'serverStatusStep',
        SELECT_PROFILE: 'selectServerProfileStep'
      }));
    });
  });

  describe('Add Modal Controller', function () {
    var $scope, resultEndPromise, invokeController;
    var deps = {};
    var steps = [
      'addServersStep',
      'serverStatusStep',
      'selectServerProfileStep'
    ];

    beforeEach(inject(function ($rootScope, $controller, $q) {
      resultEndPromise = $q.defer();

      var stepsManager = jasmine.createSpy('stepsManager').andReturn({
        addWaitingStep: jasmine.createSpy('addWaitingStep'),
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

      $scope = $rootScope.$new();
      $scope.$on = jasmine.createSpy('$on');

      _.extend(deps, {
        $scope: $scope,
        getFlint: jasmine.createSpy('getFlint').andReturn({
          destroy: jasmine.createSpy('destroy')
        }),
        $modalInstance: {
          close: jasmine.createSpy('$modalInstance')
        },
        stepsManager: stepsManager,
        waitUntilLoadedStep: jasmine.createSpy('waitUntilLoadedStep'),
        addServerSteps: {
          addServersStep: {},
          serverStatusStep: {},
          selectServerProfileStep: {}
        },
        server: {
          address: 'host001.localdomain',
          install_method: 'existing key'
        },
        step: undefined,
        requestSocket: jasmine.createSpy('requestSocket'),
        serverSpark: jasmine.createSpy('serverSpark'),
        createOrUpdateHostsThen: jasmine.createSpy('createOrUpdateHostsThen'),
        getTestHostSparkThen: jasmine.createSpy('getTestHostSparkThen').andReturn($q.defer().promise)
      });

      invokeController = function invokeController (moreDeps) {
        $controller('AddServerModalCtrl', _.extend(deps, moreDeps));
      };
    }));

    describe('no step provided', function () {
      beforeEach(function () {
        invokeController();
      });

      it('should call addWaitingStep', function () {
        expect(deps.stepsManager.plan().addWaitingStep).toHaveBeenCalledOnce(deps.waitUntilLoadedStep);
      });

      it('should invoke the steps manager', function () {
        expect(deps.stepsManager).toHaveBeenCalled();
      });

      steps.forEach(function (step) {
        it('should add step ' + step, function () {
          expect(deps.stepsManager.plan().addStep).toHaveBeenCalledOnceWith(step, deps.addServerSteps[step]);
        });
      });

      it('should start the steps manager', function () {
        expect(deps.stepsManager.plan().start).toHaveBeenCalledOnceWith('addServersStep', {
          data: {
            server: _.extend({}, deps.server, {
              address: [deps.server.address],
              auth_type: deps.server.install_method
            }),
            serverSpark: deps.serverSpark,
            flint: deps.getFlint.plan()
          }
        });
      });

      it('should close the modal instance when the manager result ends', function () {
        resultEndPromise.resolve('test');

        $scope.$digest();
        expect(deps.$modalInstance.close).toHaveBeenCalledOnce();
      });

      it('should contain the manager', function () {
        expect($scope.addServer.manager).toEqual(deps.stepsManager.plan());
      });

      it('should set an on destroy event listener', function () {
        expect($scope.$on).toHaveBeenCalledWith('$destroy', jasmine.any(Function));
      });

      describe('on close and destroy', function () {
        beforeEach(function () {
          // Invoke the $destroy and closeModal functions
          $scope.$on.calls.forEach(function (call) {
            call.args[1]();
          });
        });

        it('should destroy the manager', function () {
          expect(deps.stepsManager.plan().destroy).toHaveBeenCalledOnce();
        });

        it('should destroy flint', function () {
          expect(deps.getFlint.plan().destroy).toHaveBeenCalledOnce();
        });

        it('should close the modal', function () {
          expect(deps.$modalInstance.close).toHaveBeenCalledOnce();
        });
      });
    });

    describe('server status step', function () {
      beforeEach(function () {
        invokeController({
          step: 'serverStatusStep'
        });
      });

      it('should get the test host spark', function () {
        expect(deps.getTestHostSparkThen)
          .toHaveBeenCalledOnceWith(deps.getFlint.plan(), {
            address: ['host001.localdomain'],
            auth_type : 'existing key',
            install_method : 'existing key'
          });
      });

      it('should go to serverStatusStep', function () {
        expect(deps.stepsManager.plan().start).toHaveBeenCalledOnceWith('serverStatusStep', {
          data: {
            serverSpark: deps.serverSpark,
            server: _.extend({}, deps.server, {
              address: [deps.server.address],
              auth_type: deps.server.install_method
            }),
            flint: deps.getFlint.plan(),
            statusSpark: {
              then: jasmine.any(Function),
              catch: jasmine.any(Function),
              finally: jasmine.any(Function)
            }
          }
        });
      });
    });
  });

  describe('openAddServerModal', function () {
    var openAddServerModal, $modal, serverSpark, server, step, response, $q, $rootScope;
    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('$modal')
      };

      $provide.value('$modal', $modal);
    }));

    beforeEach(inject(function (_openAddServerModal_, _$q_, _$rootScope_) {
      server = { address: 'hostname1' };
      serverSpark = jasmine.createSpy('serverSpark');
      step = 'addServersStep';
      openAddServerModal = _openAddServerModal_;
      $q = _$q_;
      $rootScope = _$rootScope_;
      response = openAddServerModal(serverSpark, server, step);
    }));

    it('should open the modal', function () {
      expect($modal.open).toHaveBeenCalledWith({
        templateUrl: 'iml/server/assets/html/add-server-modal.html',
        controller: 'AddServerModalCtrl',
        windowClass: 'add-server-modal',
        backdropClass : 'add-server-modal-backdrop',
        resolve: {
          serverSpark: jasmine.any(Function),
          server: jasmine.any(Function),
          step: jasmine.any(Function)
        }
      });
    });

    describe('checking resolve', function () {
      var resolve;
      beforeEach(function () {
        resolve = $modal.open.mostRecentCall.args[0].resolve;
      });

      it('should return server', function () {
        expect(resolve.server()).toEqual(server);
      });

      it('should return servers', function () {
        expect(resolve.serverSpark()).toEqual(serverSpark);
      });

      it('should return a step', function () {
        expect(resolve.step()).toEqual(step);
      });
    });
  });

  describe('Host Profile', function () {
    var hostProfile, flint, hosts, spark, result;

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

  describe('getTestHostSparkThen', function () {
    var $rootScope, getTestHostSparkThen, flint, spark, deferred, promise, data;

    beforeEach(inject(function ($q, _$rootScope_, _getTestHostSparkThen_) {
      $rootScope = _$rootScope_;

      deferred = $q.defer();

      spark = {
        sendPost: jasmine.createSpy('sendPost'),
        addPipe: jasmine.createSpy('addPipe').andReturn({
          onceValueThen: jasmine.createSpy('onceValueThen')
            .andReturn(deferred.promise)
        })
      };

      flint = jasmine.createSpy('flint').andReturn(spark);

      data = {
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

      getTestHostSparkThen = _getTestHostSparkThen_;
      promise = getTestHostSparkThen(flint, {
        address: ['address1']
      });
    }));

    it('should be a function', function () {
      expect(getTestHostSparkThen).toEqual(jasmine.any(Function));
    });

    it('should return a promise', function () {
      expect(promise).toEqual({
        then: jasmine.any(Function),
        catch: jasmine.any(Function),
        finally: jasmine.any(Function)
      });
    });

    it('should call sendPost', function () {
      expect(spark.sendPost).toHaveBeenCalledWith('/test_host', { json: { address : [ 'address1' ] } });
    });

    it('should resolve with the spark', function () {
      var spy = jasmine.createSpy('spy');

      promise.then(spy);

      deferred.resolve({});

      $rootScope.$digest();

      expect(spy).toHaveBeenCalledOnceWith(spark);
    });

    describe('invoking the pipe', function () {
      var response;

      beforeEach(function () {
        response = spark.addPipe.mostRecentCall.args[0](data);
      });

      it('should indicate that the response is valid', function () {
        expect(response.body.isValid).toEqual(true);
      });

      it('should have an updated response value', function () {
        expect(response).toEqual({
          body: {
            objects: [{
              field1: 'value1',
              address: 'address1',
              key_with_underscore: 'underscore_value',
              fields: {
                Field1: 'value1',
                'Key with underscore': 'underscore_value'
              },
              invalid: false
            }],
            isValid: true
          }
        });
      });
    });
  });

  describe('Throw if server errors', function () {
    var throwIfServerErrors, handler;

    beforeEach(inject(function (_throwIfServerErrors_) {
      handler = jasmine.createSpy('handler');
      throwIfServerErrors = _throwIfServerErrors_(handler);
    }));

    it('should be a function', function () {
      expect(throwIfServerErrors).toEqual(jasmine.any(Function));
    });

    it('should return a function', function () {
      expect(handler).toEqual(jasmine.any(Function));
    });

    it('should throw if there are any errors', function () {
      expect(shouldThrow).toThrow(new Error('["fooz"]'));

      function shouldThrow () {
        throwIfServerErrors({
          body: {
            errors: ['fooz']
          }
        });
      }
    });

    it('should call the handler if there are not any errors', function () {
      var response = {
        body: {
          stuff: []
        }
      };

      throwIfServerErrors(response);

      expect(handler).toHaveBeenCalledOnceWith(response);
    });
  });
});
