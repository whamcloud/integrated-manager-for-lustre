describe('add server modal ctrl', function () {
  'use strict';

  beforeEach(module('server'));

  describe('Add Modal Controller', function () {
    var addServerModalCtrl, $scope, resultEndPromise, invokeController;
    var deps = {};

    beforeEach(inject(function ($rootScope, $controller, $q) {
      resultEndPromise = $q.defer();

      var stepsManager = {
        start: jasmine.createSpy('start'),
        result: {
          end: resultEndPromise.promise
        },
        SERVER_STEPS: {
          ADD: 'addServersStep'
        },
        destroy: jasmine.createSpy('destroy')
      };

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
        getAddServerManager: jasmine.createSpy('getAddServerManager').andReturn(stepsManager),
        servers: {
          addresses: ['host001.localdomain'],
          auth_type: 'existing key'
        },
        step: undefined,
        serverSpark: jasmine.createSpy('serverSpark')
      });

      invokeController = function invokeController (moreDeps) {
        addServerModalCtrl = $controller('AddServerModalCtrl', _.extend(deps, moreDeps));
      };
    }));

    describe('no step provided', function () {
      beforeEach(function () {
        invokeController();
      });

      it('should invoke the steps manager', function () {
        expect(deps.getAddServerManager).toHaveBeenCalledOnce();
      });

      it('should start the steps manager', function () {
        expect(deps.getAddServerManager.plan().start).toHaveBeenCalledOnceWith('addServersStep', {
          showCommand: false,
          data: {
            pdsh: deps.servers.addresses[0],
            servers: deps.servers,
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
        expect(addServerModalCtrl.manager).toEqual(deps.getAddServerManager.plan());
      });

      it('should set an on destroy event listener', function () {
        expect($scope.$on).toHaveBeenCalledOnceWith('$destroy', jasmine.any(Function));
      });

      describe('on close and destroy', function () {
        beforeEach(function () {
          // Invoke the $destroy and closeModal functions
          $scope.$on.calls.forEach(function (call) {
            call.args[1]();
          });
        });

        it('should destroy the manager', function () {
          expect(deps.getAddServerManager.plan().destroy).toHaveBeenCalledOnce();
        });

        it('should destroy flint', function () {
          expect(deps.getFlint.plan().destroy).toHaveBeenCalledOnce();
        });

        it('should close the modal', function () {
          expect(deps.$modalInstance.close).toHaveBeenCalledOnce();
        });
      });
    });
  });

  describe('openAddServerModal', function () {
    var openAddServerModal, $modal, serverSpark, server, step, response;
    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('$modal')
      };

      $provide.value('$modal', $modal);
    }));

    beforeEach(inject(function (_openAddServerModal_) {
      server = { address: 'hostname1' };
      serverSpark = jasmine.createSpy('serverSpark');
      step = 'addServersStep';
      openAddServerModal = _openAddServerModal_;
      response = openAddServerModal(serverSpark, server, step);
    }));

    it('should open the modal', function () {
      expect($modal.open).toHaveBeenCalledWith({
        templateUrl: 'iml/server/assets/html/add-server-modal.html',
        controller: 'AddServerModalCtrl as addServer',
        backdropClass : 'add-server-modal-backdrop',
        backdrop: 'static',
        keyboard: 'false',
        windowClass: 'add-server-modal',
        resolve: {
          serverSpark: jasmine.any(Function),
          servers: jasmine.any(Function),
          step: jasmine.any(Function)
        }
      });
    });

    describe('checking resolve', function () {
      var resolve;
      beforeEach(function () {
        resolve = $modal.open.mostRecentCall.args[0].resolve;
      });

      it('should return servers', function () {
        expect(resolve.servers()).toEqual({
          auth_type: undefined,
          addresses: ['hostname1']
        });
      });

      it('should return server spark', function () {
        expect(resolve.serverSpark()).toEqual(serverSpark);
      });

      it('should return a step', function () {
        expect(resolve.step()).toEqual(step);
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
