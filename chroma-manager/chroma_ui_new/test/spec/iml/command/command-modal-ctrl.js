describe('command modal', function () {
  'use strict';

  beforeEach(module('command'));

  describe('command transform', function () {
    var commandTransform;

    beforeEach(inject(function (_commandTransform_) {
      commandTransform = _commandTransform_;
    }));

    it('should be a function', function () {
      expect(commandTransform).toEqual(jasmine.any(Function));
    });

    var states = {
      cancelled: { cancelled: true },
      failed: { errored: true },
      succeeded: { complete: true },
      pending: {
        cancelled: false,
        failed: false,
        complete: false
      }
    };

    Object.keys(states).forEach(function testState (state) {
      it('should be in state ' + state, function () {
        var response = commandTransform(wrap(states[state]));

        var expected = _.extend({
          state: state,
          jobIds: []
        }, states[state]);

        expect(response).toEqual(wrap(expected));
      });
    });

    it('should throw if error', function () {
      expect(shouldThrow).toThrow();

      function shouldThrow () {
        commandTransform({ error: {} });
      }
    });

    it('should trim logs', function () {
      var result = commandTransform(wrap({
        logs: '    '
      }));

      expect(result.body.objects[0].logs).toEqual('');
    });

    it('should extract job ids', function () {
      var result = commandTransform(wrap({
        jobs: [
          '/api/job/24/',
          '/api/job/25/'
        ]
      }));

      expect(result.body.objects[0].jobIds).toEqual(['24', '25']);
    });

    function wrap () {
      var commands = [].slice.call(arguments, 0);

      return {
        body: {
          objects: commands.map(function (command) {
            return _.extend({
              logs: '',
              jobs: []
            }, command);
          })
        }
      };
    }
  });

  describe('open command modal', function () {
    var $modal, openCommandModal, spark;

    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('open')
      };

      $provide.value('$modal', $modal);
    }));

    beforeEach(inject(function (_openCommandModal_) {

      spark = {
        setLastData: jasmine.createSpy('setLastData'),
        addPipe: jasmine.createSpy('addPipe'),
        sendGet: jasmine.createSpy('sendGet')
      };

      openCommandModal = _openCommandModal_;
      openCommandModal(spark);
    }));

    it('should be a function', function () {
      expect(openCommandModal).toEqual(jasmine.any(Function));
    });

    it('should open the modal', function () {
      expect($modal.open).toHaveBeenCalledOnceWith({
        templateUrl: 'iml/command/assets/html/command-modal.html',
        controller: 'CommandModalCtrl',
        windowClass: 'command-modal',
        backdrop: 'static',
        backdropClass: 'command-modal-backdrop',
        resolve: {
          commands: [jasmine.any(Function)]
        }
      });
    });

    describe('commands', function () {
      var handle, commandSpark;

      beforeEach(function () {
        handle = $modal.open.mostRecentCall.args[0].resolve.commands[0];
        commandSpark = handle();
      });

      it('should provide a command spark', function () {
        expect(commandSpark).toEqual(spark);
      });
    });
  });

  describe('command modal ctrl', function () {
    var $scope, $modalInstance, commands;

    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();

      spyOn($scope, '$on').andCallThrough();

      $modalInstance = {
        close: jasmine.createSpy('close')
      };

      commands = {
        end: jasmine.createSpy('end'),
        onValue: jasmine.createSpy('onValue')
      };

      $controller('CommandModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        commands: commands
      });
    }));

    it('should open the first accordion', function () {
      expect($scope.commandModal.accordion0).toBe(true);
    });

    it('should close the modal', function () {
      $scope.commandModal.close();

      expect($modalInstance.close).toHaveBeenCalledOnceWith('close');
    });

    it('should listen for pipeline', function () {
      expect(commands.onValue).toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    it('should set the commands on pipeline', function () {
      commands.onValue.mostRecentCall.args[1]({
        body: {
          objects: [{ foo: 'bar' }]
        }
      });

      expect($scope.commandModal.commands).toEqual([{ foo: 'bar' }]);
    });
  });
});
