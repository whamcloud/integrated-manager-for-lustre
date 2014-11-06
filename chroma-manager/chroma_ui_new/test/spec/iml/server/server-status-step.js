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
        },
        server: {
          pdsh: 'storage0.localdomain'
        }
      };

      $controller('ServerStatusStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data
      });

      serverStatus = $scope.serverStatus;
    }));

    it('should convert a readable name to a help property', function () {
      expect(serverStatus.convertToHelp('Hostname valid')).toEqual('hostname_valid');
    });

    it('should set the pdsh expression on the scope', function () {
      expect(serverStatus.pdsh).toEqual(data.server.pdsh);
    });

    describe('hostnames and has', function () {
      beforeEach(function () {
        serverStatus.pdshUpdate('foo,bar', ['foo', 'bar'], {'foo': 1, 'bar': 1});
      });

      it('should set hostnames', function () {
        expect(serverStatus.hostnames).toEqual(['foo', 'bar']);
      });

      it('should set hostnamesHash', function () {
        expect(serverStatus.hostnamesHash).toEqual({foo: 1, bar: 1});
      });
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

      serverStatus.pdshUpdate(
        'test[001-0011].localdomain',
        [
          { address: 'test001.localdomain'},
          { address: 'test0011.localdomain'},
          { address: 'test003.localdomain' },
          { address: 'test005.localdomain' }
        ],
        { 'test001.localdomain': 1,
          'test0011.localdomain': 1,
          'test003.localdomain': 1,
          'test005.localdomain': 1
        }
      );

      handler({
        body: {
          objects: [
            { address: 'test001.localdomain'},
            { address: 'test0011.localdomain'},
            { address: 'test003.localdomain' },
            { address: 'test0015.localdomain' },
            { address: 'test005.localdomain' }
          ]
        }
      });

      expect(serverStatus.status).toEqual([
        { address: 'test001.localdomain'},
        { address: 'test003.localdomain' },
        { address: 'test005.localdomain' },
        { address: 'test0011.localdomain'}
      ]);
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
        transition: ['$transition', 'data', 'createOrUpdateHostsThen', 'hostProfile', 'waitForCommandCompletion',
          jasmine.any(Function)]
      });
    });

    describe('transitions', function () {
      var $q, $rootScope, $transition, data, createOrUpdateHostsThen, hostProfile, createHostsDeferred,
        openCommandModal, openCommandModalDeferred, transition, waitForCommandCompletion, OVERRIDE_BUTTON_TYPES;

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
          server: {},
          serverSpark: {}
        };

        waitForCommandCompletion = jasmine.createSpy('waitForCommandCompletion')
          .andReturn($q.when());

        OVERRIDE_BUTTON_TYPES = {
          OVERRIDE: 'override',
          PROCEED: 'proceed',
          PROCEED_SKIP: 'proceed and skip'
        };

        createHostsDeferred = $q.defer();
        createOrUpdateHostsThen = jasmine.createSpy('createOrUpdateHostsThen').andReturn(createHostsDeferred.promise);

        openCommandModalDeferred = $q.defer();
        openCommandModal = jasmine.createSpy('openCommandModal').andReturn(openCommandModalDeferred.promise);

        hostProfile = jasmine.createSpy('hostProfile').andReturn({
          onceValueThen: jasmine.createSpy('onceValueThen').andReturn($q.when())
        });

        transition = _.last(serverStatusStep.transition);
      }));

      describe('previous action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'previous';

          result = transition($transition, data, createOrUpdateHostsThen, hostProfile, openCommandModal);
        });

        it('should go to add servers step', function () {
          expect(result).toEqual({
            step: $transition.steps.addServersStep,
            resolve: {
              data: {
                flint: data.flint,
                server: data.server,
                serverSpark: data.serverSpark
              }
            }
          });
        });
      });

      describe('proceed and skip', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'proceed and skip';

          result = transition($transition, data, createOrUpdateHostsThen, hostProfile, waitForCommandCompletion);

          createHostsDeferred.resolve({
            body: {
              objects: [{command: { id: 1 }, host: { id: 2 }}]
            }
          });
          $rootScope.$digest();
        });

        it('should call waitForCommandCompletion', function () {
          expect(waitForCommandCompletion).toHaveBeenCalledWith(false);
        });
      });

      describe('proceed', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'proceed';

          result = transition($transition, data, createOrUpdateHostsThen, hostProfile, waitForCommandCompletion);

          createHostsDeferred.resolve({
            body: {
              objects: [{command: { id: 1 }, host: { id: 2 }}]
            }
          });
          $rootScope.$digest();
        });

        it('should get a hostProfileSpark', function () {
          expect(createOrUpdateHostsThen)
            .toHaveBeenCalledOnceWith(data.server, data.serverSpark);
        });

        it('should open the command modal', function () {
          expect(waitForCommandCompletion).toHaveBeenCalledOnceWith(true);
        });

        it('should create a host profile spark', function () {
          expect(hostProfile).toHaveBeenCalledOnceWith(data.flint, [{id: 2}]);
        });

        it('should register on onceValueThen', function () {
          expect(hostProfile.plan().onceValueThen).toHaveBeenCalledOnceWith('data');
        });

        it('should go to select server profile step', function () {
          expect(result).toEqual({
            step: $transition.steps.selectServerProfileStep,
            resolve: {
              data: {
                flint: data.flint,
                server: data.server,
                serverSpark: data.serverSpark,
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
