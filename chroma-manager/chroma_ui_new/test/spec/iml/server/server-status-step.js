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

    describe('transitioning', function () {
      beforeEach(function () {
        serverStatus.transition('next');
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
        transition: ['$transition', '$q', 'data', 'createHosts', 'hostProfile', 'openCommandModal',
          jasmine.any(Function)]
      });
    });

    describe('transitions', function () {
      var $q, $rootScope, $transition, data, createHosts, hostProfile, createHostsDeferred,
        openCommandModal, openCommandModalDeferred, transition;

      beforeEach(inject(function (_$q_, _$rootScope_) {
        $q = _$q_;
        $rootScope = _$rootScope_;

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

        createHostsDeferred = $q.defer();
        createHosts = jasmine.createSpy('createHosts').andReturn(createHostsDeferred.promise);

        openCommandModalDeferred = $q.defer();
        openCommandModal = jasmine.createSpy('openCommandModal').andReturn(openCommandModalDeferred.promise);

        hostProfile = jasmine.createSpy('hostProfile').andReturn({
          onValue: jasmine.createSpy('onValue')
        });

        transition = _.last(serverStatusStep.transition);
      }));

      describe('previous action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'previous';

          result = transition($transition, $q, data, createHosts, hostProfile, openCommandModal);
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

      describe('proceed and skip', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'proceed and skip';

          result = transition($transition, $q, data, createHosts, hostProfile, openCommandModal);

          createHostsDeferred.resolve({
            body: {
              objects: [{command: {id: 1}, host: {id: 2}}]
            }
          });
          $rootScope.$digest();
        });

        it('should not open the command modal', function () {
          expect(openCommandModal).not.toHaveBeenCalled();
        });
      });

      describe('proceed', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'proceed';

          result = transition($transition, $q, data, createHosts, hostProfile, openCommandModal);

          createHostsDeferred.resolve({
            body: {
              objects: [{command: {id: 1}, host: {id: 2}}]
            }
          });
          $rootScope.$digest();
        });

        it('should get a hostProfileSpark', function () {
          expect(createHosts)
            .toHaveBeenCalledOnceWith(data.serverData);
        });

        it('should open the command modal', function () {
          expect(openCommandModal).toHaveBeenCalledOnceWith({
            body: {
              objects: [{id: 1}]
            }
          });
        });

        it('should create a host profile spark', function () {
          expect(hostProfile).toHaveBeenCalledOnceWith(data.flint, [{id: 2}]);
        });

        it('should register an onValue listener', function () {
          expect(hostProfile.plan().onValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
        });

        it('should call the listener once', function () {
          var off = jasmine.createSpy('off');
          _.last(hostProfile.plan().onValue.mostRecentCall.args).call({
            off: off
          });
          expect(off).toHaveBeenCalledOnce();
        });

        it('should go to select server profile step', function () {
          expect(result).toEqual({
            step: $transition.steps.selectServerProfileStep,
            resolve: {
              data: {
                flint: data.flint,
                serverData: data.serverData,
                hostProfileSpark: {
                  then: jasmine.any(Function),
                  catch: jasmine.any(Function),
                  finally: jasmine.any(Function)
                }
              }
            }
          });
        });
      });
    });
  });
});
