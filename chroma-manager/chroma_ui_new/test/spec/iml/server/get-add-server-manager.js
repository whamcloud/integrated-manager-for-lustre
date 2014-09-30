describe('get add server manager', function () {
  'use strict';

  beforeEach(module('server'));

  describe('Add server steps constants', function () {
    var ADD_SERVER_STEPS;

    beforeEach(inject(function (_ADD_SERVER_STEPS_) {
      ADD_SERVER_STEPS = _ADD_SERVER_STEPS_;
    }));

    it('should contain the expected steps', function () {
      expect(ADD_SERVER_STEPS).toEqual(Object.freeze({
        ADD: 'addServersStep',
        STATUS: 'serverStatusStep',
        SELECT_PROFILE: 'selectServerProfileStep'
      }));
    });
  });

  describe('add server steps service', function () {
    var addServerSteps, addServersStep, serverStatusStep, selectServerProfileStep;

    beforeEach(module(function ($provide) {
      addServersStep = {};
      $provide.value('addServersStep', addServersStep);
      serverStatusStep = {};
      $provide.value('serverStatusStep', serverStatusStep);
      selectServerProfileStep = {};
      $provide.value('selectServerProfileStep', selectServerProfileStep);
    }));

    beforeEach(inject(function (_addServerSteps_) {
      addServerSteps = _addServerSteps_;
    }));

    it('should contain the expected steps', function () {
      expect(addServerSteps).toEqual({
        addServersStep: addServersStep,
        serverStatusStep: serverStatusStep,
        selectServerProfileStep: selectServerProfileStep
      });
    });
  });

  describe('get add server manager service', function () {
    var stepsManager, waitUntilLoadedStep;

    beforeEach(module(function ($provide) {
      stepsManager = jasmine.createSpy('stepsManager').andReturn({
        addStep: jasmine.createSpy('addStep'),
        addWaitingStep: jasmine.createSpy('addWaitingStep')
      });
      $provide.value('stepsManager', stepsManager);

      waitUntilLoadedStep = {};
      $provide.value('waitUntilLoadedStep', waitUntilLoadedStep);
    }));

    var getAddServerManager, addServerManager;

    beforeEach(inject(function (_getAddServerManager_) {
      getAddServerManager = _getAddServerManager_;
      addServerManager = getAddServerManager();
    }));

    it('should add each step', inject(function (addServerSteps) {
      expect(_.pluck(addServerManager.addStep.calls, 'args')).toEqual(_.pairs(addServerSteps));
    }));

    it('should add a waiting step', function () {
      expect(addServerManager.addWaitingStep).toHaveBeenCalledOnceWith(waitUntilLoadedStep);
    });

    it('should expose the server steps', inject(function (ADD_SERVER_STEPS) {
      expect(addServerManager.SERVER_STEPS).toEqual(ADD_SERVER_STEPS);
    }));
  });
});
