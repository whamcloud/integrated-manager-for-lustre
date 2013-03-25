describe('Events model', function () {
  'use strict';

  var $httpBackend;

  beforeEach(module('models', 'ngResource', 'constants', 'services'));

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

  it('should return the state', inject(function (eventModel, $httpBackend, STATES) {
    var states = [STATES.ERROR, STATES.WARN, STATES.INFO];

    states.forEach(function (state) {
      $httpBackend.expectGET('/api/event/')
        .respond({severity: state});

      var model = eventModel.get();

      $httpBackend.flush();

      expect(model.getState()).toEqual(state);
    });
  }));
});
