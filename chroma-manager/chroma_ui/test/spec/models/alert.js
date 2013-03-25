describe('Alerts model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'constants', 'services'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return the resource', inject(function (alertModel) {
    expect(alertModel).toBeDefined();
    expect(alertModel).toEqual(jasmine.any(Function));
  }));

  it('should return the state', inject(function (alertModel, $httpBackend, STATES) {
    $httpBackend.expectGET('/api/alert/')
      .respond({});

    var model = alertModel.get();

    $httpBackend.flush();

    expect(model.getState()).toEqual(STATES.ERROR);
  }));
});
