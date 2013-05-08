describe('Collection Model', function () {
  'use strict';

  beforeEach(module('constants', 'models', 'ngResource', 'services', 'interceptors'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should throw an error if no models are passed to the config', inject(function (collectionModel) {
    expect(collectionModel).toThrow();
  }));

  it('should return an array with properties from the query method', inject(function (collectionModel) {
    var model = collectionModel({models: []});
    expect(model.query).toEqual(jasmine.any(Function));

    var res = model.query();
    expect(res).toEqual(jasmine.any(Array));

    expect(res.$promise).toEqual(jasmine.any(Object));
    expect(res.$models).toEqual(jasmine.any(Object));
    expect(res.query).toEqual(jasmine.any(Function));
  }));

  it('should concatenate the models', inject(function (collectionModel, alertModel, eventModel, $httpBackend) {
    var model = collectionModel({models: [
      {
        name: 'alertModel',
        model: alertModel
      },
      {
        name: 'eventModel',
        model: eventModel
      }
    ]});

    $httpBackend.expectGET('/api/alert/').respond({meta: {}, objects: [{foo: 'bar'}]});
    $httpBackend.expectGET('/api/event/').respond({meta: {}, objects: [{baz: 'meh'}]});

    var models = model.query();

    $httpBackend.flush();

    expect(models[0].foo).toEqual('bar');
    expect(models[1].baz).toEqual('meh');
  }));
});
