describe('Events model', function () {
  'use strict';

  var $httpBackend;

  beforeEach(module('models', 'ngResource', 'interceptors', 'constants', 'services'));

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

  describe('dismiss', function () {
    var $httpBackend, eventModel;

    beforeEach(inject(function (_$httpBackend_, _eventModel_) {
      $httpBackend = _$httpBackend_;
      eventModel = _eventModel_;
    }));

    it('should have a dismiss method', function () {
      $httpBackend.expectGET('/api/event/').respond({id: 3});

      var model = eventModel.get();

      $httpBackend.flush();

      expect(model.dismiss).toEqual(jasmine.any(Function));
    });

    it('should dismiss the command', function () {
      $httpBackend.expectGET('/api/event/').respond({id: 3});

      var model = eventModel.get();

      $httpBackend.flush(1);
      $httpBackend.expectPATCH('/api/event/3/').respond();

      model.dismiss().then(function then (result) {
        expect(result).toBe(true);
      });

      $httpBackend.flush();
    });
  });
});
