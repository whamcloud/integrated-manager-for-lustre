describe('Server Status Step', function () {
  'use strict';

  beforeEach(module('server'));

  describe('controller', function () {
    var $stepInstance, data, serverStatus, statusSpark, hostlistFilter;

    beforeEach(inject(function ($rootScope, $controller) {
      var $scope = $rootScope.$new();

      $stepInstance = {
        transition: jasmine.createSpy('transition')
      };

      statusSpark = {
        onValue: jasmine.createSpy('onValue'),
        end: jasmine.createSpy('end')
      };

      data = {
        pdsh: 'storage0.localdomain'
      };

      hostlistFilter = {
        setHash: jasmine.createSpy('setHash').andCallFake(returnHostlistFilter),
        setHosts: jasmine.createSpy('setHosts').andCallFake(returnHostlistFilter),
        compute: jasmine.createSpy('compute')
      };

      function returnHostlistFilter () {
        return hostlistFilter;
      }

      serverStatus = $controller('ServerStatusStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data,
        statusSpark: statusSpark,
        hostlistFilter: hostlistFilter
      });
    }));

    it('should set the pdsh expression on the scope', function () {
      expect(serverStatus.pdsh).toEqual(data.pdsh);
    });

    it('should set hostnamesHash', function () {
      serverStatus.pdshUpdate('foo,bar', ['foo', 'bar'], {'foo': 1, 'bar': 1});

      expect(hostlistFilter.setHash).toHaveBeenCalledOnceWith({foo: 1, bar: 1});
    });

    describe('transitioning', function () {
      beforeEach(function () {
        serverStatus.transition('next');
      });

      it('should delegate to $stepInstance', function () {
        expect($stepInstance.transition).toHaveBeenCalledOnceWith('next', {
          data: data,
          showCommand: false
        });
      });

      it('should end the status spark', function () {
        expect(statusSpark.end).toHaveBeenCalledOnce();
      });
    });

    it('should listen on the pipeline', function () {
      expect(statusSpark.onValue)
        .toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    describe('on pipeline', function () {
      var response;

      beforeEach(function () {
        response = {
          body: {
            valid: false,
            objects: [
              { address: 'test001.localdomain'},
              { address: 'test0011.localdomain'},
              { address: 'test003.localdomain' },
              { address: 'test0015.localdomain' },
              { address: 'test005.localdomain' }
            ]
          }
        };

        var handler = statusSpark.onValue.mostRecentCall.args[1];
        handler(response);
      });

      it('should set the hosts on the filter', function () {
        expect(hostlistFilter.setHosts).toHaveBeenCalledOnceWith(response.body.objects);
      });

      it('should set status validity', function () {
        expect(serverStatus.isValid).toBe(false);
      });
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
        controller: 'ServerStatusStepCtrl as serverStatus',
        onEnter: ['data', 'getTestHostSparkThen', 'serversToApiObjects', jasmine.any(Function)],
        transition: jasmine.any(Function)
      });
    });

    describe('on enter', function () {
      var data, getTestHostSparkThen, onEnter, serversToApiObjects;

      beforeEach(function () {
        getTestHostSparkThen = jasmine.createSpy('getTestHostSparkThen');
        serversToApiObjects = jasmine.createSpy('serversToApiObjects')
          .andReturn([{
            address: 'lotus-34vm5.iml.intel.com',
            auth_type: 'existing_keys_choice'
          },
          {
            address: 'lotus-34vm6.iml.intel.com',
            auth_type: 'existing_keys_choice'
          }]);

        data = {
          flint: jasmine.createSpy('flint'),
          servers: {
            addresses: [
              'lotus-34vm5.iml.intel.com',
              'lotus-34vm6.iml.intel.com'
            ]
          }
        };

        onEnter = _.last(serverStatusStep.onEnter);
        onEnter(data, getTestHostSparkThen, serversToApiObjects);
      });

      it('should convert the servers to api objects', function () {
        expect(serversToApiObjects).toHaveBeenCalledOnceWith(data.servers);
      });

      it('should test the api objects', function () {
        expect(getTestHostSparkThen).toHaveBeenCalledOnceWith(data.flint, {
          objects: serversToApiObjects.plan()
        });
      });
    });

    describe('transition', function () {
      var steps;

      beforeEach(function () {
        steps = {
          addServersStep: {},
          selectServerProfileStep: {}
        };
      });

      it('should go to add servers step for a previous action', function () {
        var result = serverStatusStep.transition(steps, 'previous');

        expect(result).toEqual(steps.addServersStep);
      });

      it('should go to select profile step for proceed and skip', function () {
        var result = serverStatusStep.transition(steps, 'proceed and skip');

        expect(result).toEqual(steps.selectServerProfileStep);
      });

      it('should go to select profile step for proceed', function () {
        var result = serverStatusStep.transition(steps, 'proceed');

        expect(result).toEqual(steps.selectServerProfileStep);
      });
    });
  });
});
