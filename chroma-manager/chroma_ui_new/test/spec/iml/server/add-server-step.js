describe('Add server step', function () {
  'use strict';

  beforeEach(module('server'));

  var $stepInstance, addServerStepCtrl;

  [
    {},
    {
      servers: {
        auth_type: 'existing_keys_choice',
        addresses: ['foo2.localdomain']
      }
    },
    {
      servers: {
        auth_type: 'existing_keys_choice',
        addresses: ['foo1.localdomain']
      }
    }
  ].forEach(function run (data) {
    describe('controller', function () {
      var $scope;

      beforeEach(inject(function ($controller, $rootScope) {
        $scope = $rootScope.$new();

        $stepInstance = {
          getState: jasmine.createSpy('getState'),
          transition: jasmine.createSpy('transition')
        };

        addServerStepCtrl = $controller('AddServerStepCtrl', {
          $scope: $scope,
          $stepInstance: $stepInstance,
          data: _.clone(data)
        });
      }));

      it('should setup the controller', function () {
        var expected = {
          fields: {
            auth_type: getDataInstallMethod(data),
            pdsh: getPdshExpression(data)
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

        expect(addServerStepCtrl).toEqual(expected);
      });

      it('should update the fields on pdsh change', function () {
        addServerStepCtrl.pdshUpdate('foo[01-02].com', ['foo01.com', 'foo02.com'],
          {'foo01.com': 1, 'foo02.com': 1});

        expect(addServerStepCtrl.fields).toEqual({
          auth_type: 'existing_keys_choice',
          pdsh: 'foo[01-02].com',
          addresses: [ 'foo01.com', 'foo02.com' ]
        });
      });

      describe('calling transition', function () {
        beforeEach(function () {
          addServerStepCtrl.transition();
        });

        it('should set add server to disabled', function () {
          expect(addServerStepCtrl.disabled).toEqual(true);
        });

        it('should call transition on the step instance', function () {
          var expected = {
            data: {
              servers: {
                auth_type: getDataInstallMethod(data)
              },
              pdsh: getPdshExpression(data)
            }
          };

          expect($stepInstance.transition)
            .toHaveBeenCalledOnceWith('next', expected);
        });
      });
    });

    function getDataInstallMethod (data) {
      return (data.servers) ? data.servers.auth_type : 'existing_keys_choice';
    }

    function getPdshExpression (data) {
      return data.pdsh;
    }
  });

  describe('add servers step', function () {
    var addServersStep, $q, throwIfError, $rootScope;

    beforeEach(inject(function (_addServersStep_, _$q_, _throwIfError_, _$rootScope_) {
      addServersStep = _addServersStep_;
      $q = _$q_;
      throwIfError = _throwIfError_;
      $rootScope = _$rootScope_;
    }));

    it('should create the step with the expected interface', function () {
      expect(addServersStep).toEqual({
        templateUrl: 'iml/server/assets/html/add-server-step.html',
        controller: 'AddServerStepCtrl as addServer',
        transition: jasmine.any(Function)
      });
    });

    describe('transition', function () {
      var steps, result;

      beforeEach(function () {
        steps = {
          serverStatusStep: jasmine.createSpy('serverStatusStep')
        };

        result = addServersStep.transition(steps);
      });

      it('should return the next step and data', function () {
        expect(result).toEqual(steps.serverStatusStep);
      });
    });
  });
});
