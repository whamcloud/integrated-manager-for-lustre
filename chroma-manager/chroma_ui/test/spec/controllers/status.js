describe('status controller', function () {
  'use strict';

  beforeEach(module('controllers', 'models', 'ngResource', 'services', 'constants', 'interceptors'));

  var $httpBackend;
  var scope;

  var urls = {
    alertCollection: '/api/alert/?dismissed=false&limit=10&order_by=-begin',
    eventCollection: '/api/event/?dismissed=false&limit=10&order_by=-created_at',
    commandCollection: '/api/command/?dismissed=false&limit=10&order_by=-created_at'
  };

  function expectReqRes (config) {
    config = config || {};

    Object.keys(urls).forEach(function (url) {
      $httpBackend
        .expectGET(urls[url])
        .respond(config[url] || {meta: {}, objects: []});
    });
  }

  beforeEach(inject(function ($injector, $rootScope) {
    $httpBackend = $injector.get('$httpBackend');
    scope = $rootScope.$new();
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should return a status object', inject(function ($controller) {
    expectReqRes();

    $controller('StatusCtrl', {$scope: scope});
    scope.$root.$broadcast('health');
    $httpBackend.flush();

    var collectionKeys = Object.keys(scope.status.types.collection);
    var currentCollectionKeys = Object.keys(scope.status.types.collection.current);

    expect(scope.status).toEqual(jasmine.any(Object));
    expect(scope.status.types).toEqual(jasmine.any(Object));
    expect(scope.status.types.alert).toEqual(jasmine.any(Object));
    expect(collectionKeys).toContain('current');
    expect(collectionKeys).toContain('history');
    expect(currentCollectionKeys).toContain('name');
    expect(currentCollectionKeys).toContain('model');
    expect(currentCollectionKeys).toContain('models');
    expect(scope.status.types.event).toEqual(jasmine.any(Object));
    expect(scope.status.types.command).toEqual(jasmine.any(Object));
    expect(scope.status.getPage).toEqual(jasmine.any(Function));
    expect(scope.status.dismiss).toEqual(jasmine.any(Function));
  }));

  it('should dismiss a message', inject(function ($controller) {
    var commands = {
      "meta": {
        "limit": 30,
        "next": null,
        "offset": 0,
        "previous": null,
        "total_count": 3
      },
      "objects": [
        {
          "id": 1,
          "message": "Creating OST"
        },
        {
          "id": 2,
          "message": "Start file system testfs"
        },
        {
          "id": 3,
          "message": "Stop file system testfs"
        }
      ]
    };

    $controller('StatusCtrl', {$scope: scope});

    scope.status.state = scope.status.types.command;

    expect(scope.status.types.command.current.models).toBeUndefined();

    $httpBackend.expectGET('/api/command/?dismissed=false&limit=30&order_by=-created_at').respond(commands);

    scope.$root.$broadcast('health');

    $httpBackend.flush();

    $httpBackend
      .expectPATCH('/api/command/1/?dismissed=false&limit=30&order_by=-created_at')
      .respond({});

    expect(scope.status.types.command.current.models.length).toBe(3);

    scope.status.dismiss(scope.status.types.command.current.models[0]);

    $httpBackend.flush();
  }));
});
