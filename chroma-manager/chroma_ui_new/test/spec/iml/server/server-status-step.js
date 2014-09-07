describe('Server Status Step', function () {
  'use strict';

  beforeEach(module('server'));

  describe('controller', function () {
    var $stepInstance, data, serverStatus;

    beforeEach(inject(function ($rootScope, $controller) {
      var $scope = $rootScope.$new();

      $stepInstance = {
        transition: jasmine.createSpy('transition')
      };

      data = {
        statusSpark: {
          onValue: jasmine.createSpy('onValue').andReturn(jasmine.createSpy('off')
          )
        }
      };

      $controller('ServerStatusStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data
      });

      serverStatus = $scope.serverStatus;
    }));

    it('should get the host path', function () {
      expect(serverStatus.getHostPath({ address: 'foo' })).toEqual('foo');
    });

    it('should set hostnames', function () {
      serverStatus.pdshUpdate('foo,bar', ['foo', 'bar']);

      expect(serverStatus.hostnames).toEqual(['foo', 'bar']);
    });

    it('should set warning flag on the scope', function () {
      serverStatus.showWarning();

      expect(serverStatus.warning).toBe(true);
    });

    describe('transitioning', function () {
      beforeEach(function () {
        serverStatus.transition('next');
      });

      it('should set the disabled flag', function () {
        expect(serverStatus.disabled).toBe(true);
      });

      it('should delegate to $stepInstance', function () {
        expect($stepInstance.transition).toHaveBeenCalledOnceWith('next', {
          data: data
        });
      });

      it('should remove the pipeline listener', function () {
        expect(data.statusSpark.onValue.plan()).toHaveBeenCalledOnce();
      });
    });

    it('should listen on the pipeline', function () {
      expect(data.statusSpark.onValue)
        .toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    it('should set the status on pipeline value', function () {
      var handler = data.statusSpark.onValue.mostRecentCall.args[1];

      handler({
        body: {
          objects: [{ foo: 'bar' }]
        }
      });

      expect(serverStatus.status).toEqual([{ foo: 'bar' }]);
    });
  });

  describe('the step', function () {
    var serverStatusStep;

    beforeEach(inject(function (_serverStatusStep_) {
      serverStatusStep = _serverStatusStep_;
    }));

    it('should be created as expected', function () {
      expect(serverStatusStep).toEqual({
        templateUrl: 'iml/server/assets/html/server-status-step.html',
        controller: 'ServerStatusStepCtrl',
        transition: ['$transition', 'data', 'createHosts', jasmine.any(Function)]
      });
    });

    describe('transitions', function () {
      var $transition, data, createHosts, transition;

      beforeEach(function () {
        $transition = {
          steps: {
            addServersStep: {},
            selectServerProfileStep: {}
          }
        };

        data = {
          flint: {},
          serverData: {}
        };

        createHosts = jasmine.createSpy('createHosts').andReturn({});

        transition = serverStatusStep.transition[3];
      });

      describe('previous action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'previous';

          result = transition($transition, data, createHosts);
        });

        it('should go to add servers step', function () {
          expect(result).toEqual({
            step: $transition.steps.addServersStep,
            resolve: {
              data: {
                flint: data.flint,
                serverData: data.serverData
              }
            }
          });
        });
      });

      describe('next action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'next';

          result = transition($transition, data, createHosts);
        });

        it('should get a hostProfileSpark', function () {
          expect(createHosts)
            .toHaveBeenCalledOnceWith(data.flint, data.serverData);
        });

        it('should go to select server profile step', function () {
          expect(result).toEqual({
            step: $transition.steps.selectServerProfileStep,
            resolve: {
              data: {
                flint: data.flint,
                serverData: data.serverData,
                hostProfileSpark: createHosts.plan()
              }
            }
          });
        });
      });
    });
  });
});
