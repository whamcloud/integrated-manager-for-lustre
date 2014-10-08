describe('Add server step', function () {
  'use strict';

  beforeEach(module('server'));

  describe('Add servers step', function () {

    var addServer, $stepInstance;

    [
      {},
      {
        server: {
          auth_type: 'existing_keys_choice',
          address: ['foo2.localdomain']
        }
      },
      {
        server: {
          auth_type: 'existing_keys_choice',
          address: ['foo1.localdomain']
        }
      }
    ].forEach(function (data) {
      describe('controller', function () {

        var $scope;

        beforeEach(inject(function ($controller, $rootScope) {
          $scope = $rootScope.$new();

          $stepInstance = {
            getState: jasmine.createSpy('getState'),
            transition: jasmine.createSpy('transition')
          };

          $controller('AddServerStepCtrl', {
            $scope: $scope,
            $stepInstance: $stepInstance,
            data: _.clone(data)
          });

          addServer = $scope.addServer;
        }));

        it('should setup the scope', function () {
          var expected = {
            fields: {
              auth_type: getDataInstallMethod(data),
              pdsh: getDataAddress(data)
            },
            CHOICES: Object.freeze({
              EXISTING_KEYS: 'existing_keys_choice',
              ROOT_PASSWORD: 'id_password_root',
              ANOTHER_KEY: 'private_key_choice'
            }),
            pdshUpdate: jasmine.any(Function),
            transition: jasmine.any(Function),
            close: jasmine.any(Function)
          };

          if (data.server && data.server.address)
            expected.fields.address = data.server.address;

          expect(addServer).toEqual(expected);
        });

        it('should update the fields on pdsh change', function () {
          addServer.pdshUpdate('foo[01-02].com', ['foo01.com', 'foo02.com'],
            {'foo01.com': 1, 'foo02.com': 1});

          expect(addServer.fields).toEqual(
            {
              auth_type: 'existing_keys_choice',
              pdsh: 'foo[01-02].com',
              address: [ 'foo01.com', 'foo02.com' ],
              addressHash: { 'foo01.com': 1, 'foo02.com': 1}
            });
        });

        describe('calling transition', function () {
          beforeEach(function () {
            addServer.transition();
          });

          it('should set add server to disabled', function () {
            expect($scope.addServer.disabled).toEqual(true);
          });

          it('should call transition on the step instance', function () {
            var expected = {
              data: {
                server: {
                  auth_type: getDataInstallMethod(data),
                  pdsh: getDataAddress(data)
                }
              }
            };

            if (data.server && data.server.address)
              expected.data.server.address = data.server.address;

            expect($stepInstance.transition)
              .toHaveBeenCalledOnceWith('next', expected);
          });
        });
      });

      function getDataInstallMethod (data) {
        return (data.server) ? data.server.auth_type : 'existing_keys_choice';
      }

      function getDataAddress (data) {
        return (data.server) ? data.server.address[0] : null;
      }
    });
  });

  describe('add servers step', function () {

    var addServersStep, $q, throwIfError, $rootScope;
    beforeEach(module('server', 'socket-module'));
    beforeEach(inject(function (_addServersStep_, _$q_, _throwIfError_, _$rootScope_) {
      addServersStep = _addServersStep_;
      $q = _$q_;
      throwIfError = _throwIfError_;
      $rootScope = _$rootScope_;
    }));

    it('should create the step with the expected interface', function () {
      expect(addServersStep).toEqual({
        templateUrl: 'iml/server/assets/html/add-server-step.html',
        controller: 'AddServerStepCtrl',
        transition: jasmine.any(Array)
      });
    });

    describe('transition', function () {
      var $transition, data, getTestHostSparkThen, result, promise;
      beforeEach(function () {
        $transition = {
          steps: {
            serverStatusStep: jasmine.createSpy('serverStatusStep')
          }
        };
        data = {
          flint: jasmine.createSpy('flint'),
          server: {}
        };
        promise = {
          catch: jasmine.any(Function),
          finally: jasmine.any(Function),
          then: jasmine.any(Function)
        };
        getTestHostSparkThen = jasmine.createSpy('getTestHostSparkThen').andReturn(promise);

        var handler = addServersStep.transition[addServersStep.transition.length - 1];
        result = handler($transition, data, getTestHostSparkThen);
      });

      it('should invoke getTestHostSparkThen', function () {
        expect(getTestHostSparkThen).toHaveBeenCalledOnceWith(data.flint, data.server);
      });

      it('should return the next step and data', function () {
        expect(result).toEqual({
          step: $transition.steps.serverStatusStep,
          resolve: {
            data: {
              flint: data.flint,
              server: data.server,
              statusSpark: promise
            }
          }
        });
      });
    });
  });
});
