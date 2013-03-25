describe('Alerts model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'constants'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return the resource', inject(function (alertModel) {
    expect(alertModel).toBeDefined();
    expect(alertModel).toEqual(jasmine.any(Function));
  }));

  it('should have a method to load all alerts', inject(function (alertModel, $httpBackend) {
    expect(alertModel.loadAll).toBeDefined();

    $httpBackend
      .expectGET('/api/alert?limit=0')
      .respond({});

    alertModel.loadAll();
    $httpBackend.flush();
  }));
});
