describe('status controller', function () {
  'use strict';

  beforeEach(module('controllers', 'models', 'ngResource', 'services', 'constants', 'interceptors', 'ui.bootstrap',
    function ($provide) {
      var $elementMock = {
        find: jasmine.createSpy('find').andCallFake(function () {
          return $elementMock;
        }),
        scrollTop: jasmine.createSpy('scrollTop')
      };

      $provide.value('$element', $elementMock);
    }
  ));

  var $httpBackend, $scope, $element, notificationResponse, createController;

  beforeEach(inject(function ($injector, $rootScope, $controller, _$element_) {
    $httpBackend = $injector.get('$httpBackend');
    $scope = $rootScope.$new();
    $element = _$element_;

    createController = function () {
      $controller('StatusCtrl', {
        $scope: $scope
      });
    };

    notificationResponse = {
      'meta': {
        'limit': 30,
        'next': null,
        'offset': 0,
        'previous': null,
        'total_count': 3
      },
      'objects': [
        {
          'id': 1,
          'message': 'Creating OST',
          complete: true,
          type: 'Command'
        },
        {
          'id': 2,
          'message': 'Start file system testfs',
          complete: true,
          type: 'Command'
        },
        {
          'id': 3,
          'message': 'Stop file system testfs',
          complete: true,
          type: 'Command'
        }
      ]
    };
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should return a status object', function () {
    $httpBackend
      .expectGET('/api/notification/?dismissed=false&limit=30&order_by=-created_at')
      .respond(notificationResponse);

    createController();

    $scope.$root.$broadcast('health');
    $httpBackend.flush();

    var notificationKeys = Object.keys($scope.status.types.notification);
    var currentNotificationKeys = Object.keys($scope.status.types.notification.current);

    expect($scope.status).toEqual(jasmine.any(Object));
    expect($scope.status.types).toEqual(jasmine.any(Object));
    expect($scope.status.types.alert).toEqual(jasmine.any(Object));
    expect($scope.status.types.event).toEqual(jasmine.any(Object));
    expect($scope.status.types.command).toEqual(jasmine.any(Object));

    expect(notificationKeys).toContain('current');
    expect(notificationKeys).toContain('history');
    expect(currentNotificationKeys).toContain('name');
    expect(currentNotificationKeys).toContain('model');
    expect(currentNotificationKeys).toContain('models');
    expect($scope.status.getPage).toEqual(jasmine.any(Function));
    expect($scope.status.dismiss).toEqual(jasmine.any(Function));
  });

  it('should dismiss a message', function () {
    var commands = {
      'meta': {
        'limit': 30,
        'next': null,
        'offset': 0,
        'previous': null,
        'total_count': 3
      },
      'objects': [
        {
          'id': 1,
          'message': 'Creating OST',
          complete: true
        },
        {
          'id': 2,
          'message': 'Start file system testfs',
          complete: true
        },
        {
          'id': 3,
          'message': 'Stop file system testfs',
          complete: true
        }
      ]
    };

    createController();

    $scope.status.state = $scope.status.types.command;

    expect($scope.status.types.command.current.models).toBeUndefined();

    $httpBackend.expectGET('/api/command/?dismissed=false&limit=30&order_by=-created_at').respond(commands);

    $scope.$root.$broadcast('health');

    $httpBackend.flush();

    $httpBackend
      .expectPATCH('/api/command/1/')
      .respond({});

    expect($scope.status.types.command.current.models.length).toBe(3);

    $scope.status.dismiss($scope.status.types.command.current.models[0]);

    $httpBackend.flush();
  });

  it('should scroll the message container', function () {
    createController();

    $httpBackend
      .expectGET('/api/notification/?dismissed=false&limit=30&order_by=-created_at')
      .respond(notificationResponse);

    $scope.status.updateViewState();

    $httpBackend.flush();

    expect($element.find).toHaveBeenCalledWith('ul.messages');
    expect($element.scrollTop).toHaveBeenCalledWith(0);
  });
});
