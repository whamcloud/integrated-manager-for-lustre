(function (_) {
  'use strict';

  describe('Command Dropdown', function () {

    var data, el;

    beforeEach(module('services', 'constants', function () {
      data = {
        resource_uri: 'foo',
        available_jobs: [
          {
            args: {
              'host_id': 279
            },
            class_name: 'ForceRemoveHostJob',
            confirmation: 'The record for the server in Chroma Manager is removed without\n' +
              'attempting to contact server.',
            verb: 'Force Remove',
            long_description: null
          },
          {
            args: {
              host_id: 279
            },
            class_name: 'RebootHostJob',
            confirmation: 'Initiate a reboot on the host.',
            verb: 'Reboot',
            long_description: null
          },
          {
            args: {
              host_id: 279
            },
            class_name: 'ShutdownHostJob',
            confirmation: 'Initiate an orderly shutdown on the host. ',
            verb: 'Shutdown',
            long_description: 'baz'
          }
        ],
        available_transitions: [
          {
            state: 'removed',
            verb: 'Remove',
            long_description: null
          },
          {
            state: 'lnet_down',
            verb: 'Stop LNet',
            long_description: 'foo'
          },
          {
            state: 'lnet_unloaded',
            verb: 'Unload LNet',
            long_description: 'bar'
          }
        ]
      };

      el = angular.element('<div />');
    }));

    beforeEach(inject(function ($injector, safeApply) {
      // patch $window.
      var $window = $injector.get('$window');

      $window.LiveObject = {
        resourceType: jasmine.createSpy('resourceType').andReturn('host')
      };

      $window.CommandNotification = {
        uriIsWriteLocked: jasmine.createSpy('uriIsWriteLocked').andCallFake(function (uri) {
          return uri === 'bar';
        })
      };

      safeApply.addToRootScope();

    }));

    it('should return a configuration object', inject(function (commandDropdownService) {
      expect(commandDropdownService).toEqual(jasmine.any(Object));
      expect(commandDropdownService.link).toEqual(jasmine.any(Function));
    }));

    it('should build a list of items given some data', inject(function (commandDropdownService, $rootScope) {
      var $scope = $rootScope.$new();

      $scope.data = data;

      commandDropdownService.link($scope, el, {});
      $scope.data.available_transitions.forEach(function (transition) {
        var match = _.where($scope.list, {
          verb: transition.verb,
          type: 'transitions'
        });

        expect(match.length).toEqual(1);
      });

      $scope.data.available_jobs.forEach(function (job) {
        var match = _.where($scope.list, {
          verb: job.verb,
          type: 'jobs'
        });

        expect(match.length).toEqual(1);
      });
    }));

    it('should attach bridge events to the scope',
      inject(function (commandDropdownService, $rootScope) {
      var $scope = $rootScope.$new();
      $scope.data = data;

      expect(el.hasClass('hide')).toBeFalsy();
      commandDropdownService.link($scope, el, {});
      expect(el.hasClass('hide')).toBeFalsy();

      $scope.$broadcast('disableCommandDropdown', 'foo');

      expect(el.hasClass('hide')).toBeTruthy();

      var newData = _.cloneDeep(data);
      newData.available_transitions.push({
        state: 'lnet_up',
        verb: 'Start Lnet'
      });

      $scope.$broadcast('updateCommandDropdown', 'foo', newData);

      expect($scope.data).toBe(newData);
    }));

    it('should hide new buttons when uriIsWriteLocked',
      inject(function (commandDropdownService, $rootScope, $window) {
      var $scope = $rootScope.$new();
      $scope.data = _.cloneDeep(data);
      $scope.data.resource_uri = 'bar';

      expect(el.hasClass('hide')).toBeFalsy();

      commandDropdownService.link($scope, el, {});

      expect(el.hasClass('hide')).toBeTruthy();
      expect($window.CommandNotification.uriIsWriteLocked).toHaveBeenCalledWith('bar');
    }));

    it('should delegate to a click handler if one is provided', inject(function (commandDropdownService, $rootScope) {
      var $scope = $rootScope.$new();
      $scope.data = data;
      $scope.commandClick = jasmine.createSpy('commandClick');
      commandDropdownService.link($scope, el, {commandClick: ''});

      var $event = {};
      $scope.transitionClicked($event);

      expect($scope.commandClick).toHaveBeenCalledOnceWith({
        $event: $event,
        data: data,
        done: jasmine.any(Function)
      });
    }));
  });
})(window.lodash);
