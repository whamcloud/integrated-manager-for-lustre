describe('Commands model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'interceptors', 'services', 'constants'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return the resource', inject(function (commandModel) {
    expect(commandModel).toBeDefined();
    expect(commandModel).toEqual(jasmine.any(Function));
  }));

  it('should return the state', inject(function (commandModel, $httpBackend, STATES) {
    var actualExpect = {};
    actualExpect[STATES.INCOMPLETE] = {complete: false};
    actualExpect[STATES.ERROR] = {complete: true, errored: true};
    actualExpect[STATES.CANCELED] = {complete: true, cancelled: true};
    actualExpect[STATES.COMPLETE] = {complete: true};

    Object.keys(actualExpect).forEach(function (state) {
      $httpBackend.expectGET('/api/command/')
        .respond(actualExpect[state]);

      var model = commandModel.get();

      $httpBackend.flush();

      expect(model.getState()).toEqual(state);
    });
  }));

  it('should block dismiss if not completed', inject(function ($httpBackend, commandModel) {
    $httpBackend.expectGET('/api/command/').respond({complete: false});

    var model = commandModel.get();

    $httpBackend.flush();

    expect(model.notDismissable()).toBe(true);
  }));

  it('should allow dismiss if completed', inject(function ($httpBackend, commandModel) {
    $httpBackend.expectGET('/api/command/').respond({complete: true});

    var model = commandModel.get();

    $httpBackend.flush();

    expect(model.notDismissable()).toBe(false);
  }));

  it('should return a no dismiss message key', inject(function (commandModel, $httpBackend) {
    $httpBackend.expectGET('/api/command/').respond({});

    var model = commandModel.get();

    $httpBackend.flush();

    expect(model.noDismissMessage()).toEqual('no_dismiss_message_command');
  }));
});
