describe('Command controller', function () {
  'use strict';

  var $scope, $modal, commandController, CommandModel;

  beforeEach(module('command', 'modelFactory'));

  mock.beforeEach(
    function createCommandModelMock () {
      CommandModel = {
        save: jasmine.createSpy('CommandModel.save')
      };

      return {
        name: 'CommandModel',
        value: CommandModel
      };
    },
    function createModalMock() {
      $modal = {};

      return {
        name: '$modal',
        value: $modal
      };
    }
  );

  beforeEach(inject(function ($controller, _$modal_, $rootScope) {
    $modal = _$modal_;
    $scope = $rootScope.$new();

    commandController = $controller('CommandCtrl', {
      $scope: $scope
    });
  }));

  describe('handling job or state change with onActionSelection()', function () {
    beforeEach(function () {
      spyOn(commandController, 'executeJob');
      spyOn(commandController, 'changeState');
    });

    it('should call executeJob() when there is a job class', function () {
      var fakeVictim = {}, fakeAction = {class_name: 'bob'};

      $scope.onActionSelection(fakeVictim, fakeAction);

      expect(commandController.executeJob).toHaveBeenCalledWith(fakeVictim, fakeAction);
    });

    it('should call changeState() when there is not a job class', function () {
      var fakeVictim = {}, fakeAction = {};

      $scope.onActionSelection(fakeVictim, fakeAction);

      expect(commandController.changeState).toHaveBeenCalledWith(fakeVictim, fakeAction);
    });
  });

  describe('handling AdvertisedJob execution', function () {
    var modalOpen;

    beforeEach(function () {
      modalOpen = jasmine.createSpy('$modal.open').andReturn({
        result: { then: function () {} }
      });
      $modal.open = modalOpen;
    });

    it('should open a modal if the job requires confirmation', function () {
      var fakeVictim = {}, fakeAction = {confirmation: true};

      commandController.executeJob(fakeVictim, fakeAction);

      expect(modalOpen).toHaveBeenCalled();
    });

    it('should not open a modal if the job does not require confirmation', function () {
      var fakeVictim = {label: 'frank'},
          fakeAction = {class_name: 'bob', args: {}, verb: 'bludgeon'};
      var fakeJob = {class_name: fakeAction.class_name, args: fakeAction.args};
      var fakeMessage = fakeAction.verb + '(' + fakeVictim.label + ')';

      commandController.executeJob(fakeVictim, fakeAction);

      expect(modalOpen).not.toHaveBeenCalled();
      expect(CommandModel.save).toHaveBeenCalledWith({jobs: [fakeJob], message: fakeMessage});
    });
  });

  describe('handling state transitions', function () {
    var modalOpen, fakeVictim, fakeAction, fakeData;

    beforeEach(function () {
      modalOpen = jasmine.createSpy('$modal.open').andReturn({
        result: { then: function () {} }
      });
      $modal.open = modalOpen;

      fakeVictim = jasmine.createSpyObj('FakeCopytool', ['changeState']);

      fakeAction = { state: 'fakeState' };

      fakeData = {
          transition_job: { confirmation_prompt: 'prompt' },
          dependency_jobs: []
        };

      fakeVictim.testStateChange = function () {
        return { then: function (callback) { return callback(fakeData); } };
      };
    });

    it('should not do anything if there is no transition job', function () {
      fakeData.transition_job = null;

      commandController.changeState(fakeVictim, fakeAction);

      expect(modalOpen).not.toHaveBeenCalled();
    });

    it('should open a modal if the transition job requires confirmation', function () {
      commandController.changeState(fakeVictim, fakeAction);

      expect(modalOpen).toHaveBeenCalled();
    });

    it('should open a modal if any of the prerequisite jobs require confirmation', function () {
      fakeData.transition_job.confirmation_prompt = null;
      fakeData.dependency_jobs = [{description: 'foo', requires_confirmation: true}];

      commandController.changeState(fakeVictim, fakeAction);

      expect(modalOpen).toHaveBeenCalled();
    });

    it('should not open a modal if the transition does not require confirmation', function () {
      fakeData.transition_job.confirmation_prompt = null;

      commandController.changeState(fakeVictim, fakeAction);

      expect(modalOpen).not.toHaveBeenCalled();
      expect(fakeVictim.changeState).toHaveBeenCalledWith(fakeAction.state);
    });
  });

  describe('handling conf_param updates', function () {
    var fakeVictim, fakeParam;

    beforeEach(function () {
      fakeVictim = jasmine.createSpyObj('FakeTarget', ['$update']);
      fakeVictim.conf_params = {};

      fakeParam = { param_key: 'fake.param', param_value: 'hai!' };
    });

    it('should call $update on the victim', function () {
      commandController.setConfParam(fakeVictim, fakeParam);

      expect(fakeVictim.$update).toHaveBeenCalled();
    });
  });
});
