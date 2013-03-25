describe('Events model', function () {
  'use strict';

  var $httpBackend;

  beforeEach(module('models', 'ngResource', 'constants'));

  beforeEach(inject(function ($injector) {
    $httpBackend = $injector.get('$httpBackend');
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should retrieve the class', inject(function (eventModel) {
    expect(eventModel).toBeDefined();
    expect(eventModel).toEqual(jasmine.any(Function));
  }));

  it('should have a method to load all events', inject(function (eventModel) {
    expect(eventModel.loadAll).toBeDefined();

    $httpBackend
      .expectGET('/api/event?limit=0')
      .respond({});

    eventModel.loadAll();
    $httpBackend.flush();
  }));
});
