describe('App controller', function () {
  'use strict';

  var $routeSegment, appController, sessionFixture, $httpBackend, navigate, fixtures;

  beforeEach(module('app'));

  mock.beforeEach('navigate', '$routeSegment');

  beforeEach(inject(function (_$routeSegment_, $controller, _$httpBackend_, _navigate_, _fixtures_) {
    $routeSegment = _$routeSegment_;
    appController = $controller('AppCtrl');
    $httpBackend = _$httpBackend_;
    navigate = _navigate_;
    fixtures = _fixtures_;

    sessionFixture = fixtures.getFixture('session', function (fixture) {
      return fixture.status === 200;
    });

    $httpBackend.whenGET('session/').respond.apply(null, sessionFixture.toArray());
    $httpBackend.whenDELETE('session/').respond(204);
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should have a method to redirect to login', function () {
    $httpBackend.flush();

    appController.login();

    expect(navigate).toHaveBeenCalledOnceWith('login/');
  });

  it('should have a method to logout and redirect to login', function () {
    $httpBackend.flush();

    appController.logout();

    $httpBackend.flush();

    expect(navigate).toHaveBeenCalledOnceWith('login/');
  });

  it('should expose the $routeSegment on the controller', function () {
    $httpBackend.flush();

    expect(appController.$routeSegment).toEqual($routeSegment);
  });

  describe('logged in', function () {
    beforeEach(function () {
      $httpBackend.flush();
    });

    it('should expose the session as a property', function () {
      sessionFixture.data.user = jasmine.any(Object);

      expect(jasmine.objectContaining(sessionFixture.data).jasmineMatches(appController.session)).toBe(true);
    });

    it('should expose the user as a property', function () {
      expect(jasmine.objectContaining(sessionFixture.data.user).jasmineMatches(appController.user)).toBe(true);
    });

    it('should tell if the user is logged in', function () {
      expect(appController.loggedIn).toBe(true);
    });

    it('should direct the on click method to the proper action', function () {
      expect(appController.onClick).toBe(appController.logout);
    });
  });

  describe('logged out', function () {
    beforeEach(function () {
      sessionFixture = fixtures.getFixture('session', function (fixture) {
        return fixture.data.user == null;
      });

      $httpBackend.expectGET('session/').respond.apply(null, sessionFixture.toArray());

      $httpBackend.flush();
    });

    it('should expose the session as a property', function () {
      sessionFixture.data.user = jasmine.any(Object);

      expect(jasmine.objectContaining(sessionFixture.data).jasmineMatches(appController.session)).toBe(true);
    });

    it('should expose the user as a property', function () {
      expect(jasmine.objectContaining(sessionFixture.data.user).jasmineMatches(appController.user)).toBe(true);
    });

    it('should tell if the user is logged in', function () {
      expect(appController.loggedIn).toBe(false);
    });

    it('should direct the on click method to the proper action', function () {
      expect(appController.onClick).toBe(appController.login);
    });
  });
});
