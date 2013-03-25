describe('Commands model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'constants'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return the resource', inject(function (commandModel) {
    expect(commandModel).toBeDefined();
    expect(commandModel).toEqual(jasmine.any(Function));
  }));

  it('should have a method to load all commands', inject(function (commandModel, $httpBackend) {
    expect(commandModel.loadAll).toBeDefined();

    $httpBackend
      .expectGET('/api/command?limit=0')
      .respond({});

    commandModel.loadAll();

    $httpBackend.flush();
  }));
});
