describe('Commands model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'services', 'constants'));

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
});
