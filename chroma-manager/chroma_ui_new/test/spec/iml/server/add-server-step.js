(function () {
  'use strict';

  describe('Add servers step', function () {

    beforeEach(module('server'));

    var addServer, $stepInstance, buildTestHostData;

    [
      {},
      {
        server: {
          install_method: 'existing_keys_choice'
        }
      },
      {
        server: {
          install_method: 'existing_keys_choice',
          address: 'foo1.localdomain'
        }
      }
    ].forEach(function (data) {
        describe('controller', function () {

          var $scope;

          beforeEach(inject(function ($controller, $rootScope) {
            $scope = $rootScope.$new();

            $stepInstance = {
              setState: jasmine.createSpy('setState'),
              getState: jasmine.createSpy('getState'),
              transition: jasmine.createSpy('transition')
            };

            buildTestHostData = jasmine.createSpy('buildTestHostData').andReturn(generateServerFields(data));

            $controller('AddServerStepCtrl', {
              $scope: $scope,
              $stepInstance: $stepInstance,
              buildTestHostData: buildTestHostData,
              data: data
            });

            addServer = $scope.addServer;
          }));

          it('should setup the scope', function () {
            expect(addServer).toEqual({
              fields: {
                sshAuthChoice: getDataInstallMethod(data),
                pdsh: getDataAddress(data)
              },
              CHOICES: Object.freeze({
                EXISTING_KEYS: 'existing_keys_choice',
                ROOT_PASSWORD: 'id_password_root',
                ANOTHER_KEY: 'private_key_choice'
              }),
              pdshUpdate: jasmine.any(Function),
              transition: jasmine.any(Function)
            });
          });

          it('should update the fields on pdsh change', function () {
            addServer.pdshUpdate('foo[01-02].com', ['foo01.com', 'foo02.com']);

            expect(addServer.fields).toEqual({
              sshAuthChoice: 'existing_keys_choice',
              pdsh: 'foo[01-02].com',
              address: ['foo01.com', 'foo02.com']
            });
          });

          describe('calling transition', function () {
            beforeEach(function () {
              addServer.transition();
            });

            it('should set add server to disabled', function () {
              expect($scope.addServer.disabled).toEqual(true);
            });

            it('should set server data', function () {
              expect(data.serverData).toEqual(generateServerFields(data));
            });

            it('should set the state on the step instance', function () {
              expect($stepInstance.setState).toHaveBeenCalledOnceWith(generateServerFields(data));
            });

            it('should call transition on the step instance', function () {
              expect($stepInstance.transition).toHaveBeenCalledOnceWith('next', {data: data});
            });
          });
        });

        function generateServerFields (data) {
          return {
            sshAuthChoice: getDataInstallMethod(data),
            pdsh: getDataAddress(data)
          };
        }

        function getDataInstallMethod (data) {
          return (data.server) ? data.server.install_method : 'existing_keys_choice';
        }

        function getDataAddress (data) {
          return (data.server) ? data.server.address : null;
        }
      });
  });

  describe('building test host data', function () {
    var buildTestHostData;

    beforeEach(module('server'));

    beforeEach(inject(function (_buildTestHostData_) {
      buildTestHostData = _buildTestHostData_;
    }));

    [
      {
        type: 'existing keys',
        in: { address: 'foo.bar', sshAuthChoice: 'existing_keys_choice' },
        out: { address: 'foo.bar', auth_type: 'existing_keys_choice', commit: true }
      },
      {
        type: 'root password',
        in: { address: 'foo.bar', sshAuthChoice: 'id_password_root', rootPassword: 'foo' },
        out: { address: 'foo.bar', auth_type: 'id_password_root', commit: true, root_password: 'foo' }
      },
      {
        type: 'private key no password',
        in: { address: 'foo.bar', sshAuthChoice: 'private_key_choice', privateKey: 'foo' },
        out: { address: 'foo.bar', auth_type: 'private_key_choice', commit: true, private_key: 'foo' }
      },
      {
        type: 'private key password',
        in: { address: 'foo.bar', sshAuthChoice: 'private_key_choice', privateKey: 'foo',
          privateKeyPassphrase: 'bar' },
        out: { address: 'foo.bar', auth_type: 'private_key_choice',
          commit: true, private_key: 'foo', private_key_passphrase: 'bar' }
      }
    ].forEach(function (item) {
        it('should transform data for ' + item.type, function () {
          expect(buildTestHostData(item.in)).toEqual(item.out);
        });
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
      var $transition, data, testHost, createHosts, result, statusSpark, promise;
      beforeEach(function () {
        $transition = {
          steps: {
            selectServerProfileStep: jasmine.createSpy('selectServerProfileStep'),
            serverStatusStep: jasmine.createSpy('serverStatusStep')
          }
        };
        data = {
          flint: jasmine.createSpy('flint'),
          serverData: jasmine.createSpy('serverData')
        };
        statusSpark = {
          onValue: jasmine.createSpy('onValue')
        };
        testHost = jasmine.createSpy('testHost').andReturn(statusSpark);
        createHosts = jasmine.createSpy('createHosts').andReturn('hostProfileSpark');
        promise = {
          catch: jasmine.any(Function),
          finally: jasmine.any(Function),
          then: jasmine.any(Function)
        };

        result = addServersStep.transition[addServersStep.transition.length - 1]($q, $transition, data, testHost,
          createHosts, throwIfError);
      });

      it('should invoke testHost', function () {
        expect(testHost).toHaveBeenCalledOnceWith(data.flint, data.serverData);
      });

      it('should call statusSpark.onValue', function () {
        expect(statusSpark.onValue).toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
      });

      it('should set a promise on the statusSpark', function () {
        expect(data.statusSpark).toEqual(promise);
      });

      it('should return a promise', function () {
        expect(result).toEqual(promise);
      });

      describe('onValue pipeline', function () {
        var response;

        beforeEach(function () {
          statusSpark.off = jasmine.createSpy('off');
        });

        describe('successful valid pipeline', function () {
          beforeEach(function () {
            response = {
              body: {
                isValid: true
              }
            };
            statusSpark.onValue.mostRecentCall.args[1].call(statusSpark, response);
          });

          it('should call off', function () {
            expect(statusSpark.off).toHaveBeenCalledOnce();
          });

          it('should resolve the status spark', function () {
            data.statusSpark.then(function (resolvedStatusSpark) {
              expect(resolvedStatusSpark).toEqual(statusSpark);
            });

            $rootScope.$digest();
          });

          it('should call createHost with flint and server data', function () {
            expect(createHosts).toHaveBeenCalledOnceWith(data.flint, data.serverData);
          });

          it('should resolve with the selectServerProfileStep and hostProfileSpark', function () {
            result.then(function (resolvedData) {
              var expectedData = _.extend({}, data);
              expectedData.hostProfileSpark = 'hostProfileSpark';

              expect(resolvedData).toEqual({
                step: $transition.steps.selectServerProfileStep,
                resolve: {
                  data: expectedData
                }
              });
            });

            $rootScope.$digest();
          });
        });

        describe('successful invalid pipeline', function () {
          beforeEach(function () {
            response = {
              body: {
                isValid: false
              }
            };

            statusSpark.onValue.mostRecentCall.args[1].call(statusSpark, response);
          });

          it('should call off', function () {
            expect(statusSpark.off).toHaveBeenCalledOnce();
          });

          it('should resolve the status spark', function () {
            data.statusSpark.then(function (resolvedStatusSpark) {
              expect(resolvedStatusSpark).toEqual(statusSpark);
            });

            $rootScope.$digest();
          });

          it('should not call createHost', function () {
            expect(createHosts).not.toHaveBeenCalled();
          });

          it('should resolve with the selectServerProfileStep and hostProfileSpark', function () {
            result.then(function (resolvedData) {
              expect(resolvedData).toEqual({
                step: $transition.steps.serverStatusStep,
                resolve: {
                  data: data
                }
              });
            });

            $rootScope.$digest();
          });
        });

        describe('unsuccessful', function () {
          beforeEach(function () {
            response = {
              body: {
                errors: [
                  {msg: 'error'}
                ]
              }
            };
          });

          it('should call off', function () {
            try {
              statusSpark.onValue.mostRecentCall.args[1].call(statusSpark, response);
            } catch (e) {
              expect(e.message).toEqual('[{"msg":"error"}]');
            }

            expect(statusSpark.off).toHaveBeenCalledOnce();
          });
        });
      });
    });
  });
})();
