describe('Login Controller', function () {
  'use strict';

  var loginController, $httpBackend, $modal, sessionFixture, sessionFixtures, $rootScope, navigate;

  var userEulaStates = {
    EULA: 'eula',
    PASS: 'pass',
    DENIED: 'denied'
  };

  beforeEach(module('login'));

  mock.beforeEach('$modal', 'navigate', 'help');

  beforeEach(inject(function ($controller, _$httpBackend_, _$modal_, _$rootScope_, _navigate_, fixtures) {
    $httpBackend = _$httpBackend_;
    $rootScope = _$rootScope_;
    $modal = _$modal_;
    navigate = _navigate_;
    sessionFixtures = fixtures.asName('session');

    loginController = $controller('LoginCtrl', {
      user_EULA_STATES: userEulaStates
    });

    sessionFixture = sessionFixtures.getFixture(function (fixture) {
      return fixture.status === 200;
    });

    $httpBackend.whenPOST('session/').respond(201);
    $httpBackend.whenGET('session/').respond.apply(null, sessionFixture.toArray());
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should have a method to go to index', function () {
    loginController.goToIndex();

    expect(navigate).toHaveBeenCalledWith();
  });

  describe('authenticated user', function () {
    var credentials = {
        username: 'foo',
        password: 'bar'
      };

    beforeEach(function () {
      $httpBackend.expectPOST('session/', credentials).respond(201);

      _.extend(loginController, credentials);

      loginController.submitLogin();

      expect($modal.open.callCount).toEqual(0);
    });

    it('should show the eula dialog if api says so', function () {
      $httpBackend.flush();

      expect($modal.open.callCount).toEqual(1);

      expect($modal.open).toHaveBeenCalledWith({
        templateUrl: 'common/login/assets/html/eula.html',
        keyboard: false,
        backdrop: 'static',
        controller: 'EulaCtrl',
        windowClass: 'eula-modal',
        resolve: jasmine.argThat(function(arg) {
          return typeof arg.user === 'function';
        })
      });
    });

    it('should redirect to base uri if api says so', function () {
      sessionFixture.data.user.eula_state = userEulaStates.PASS;
      $httpBackend.expectGET('session/').respond.apply(null, sessionFixture.toArray());

      $httpBackend.flush();

      expect($modal.open.callCount).toEqual(0);
      expect(navigate).toHaveBeenCalledOnceWith();
    });

    it('should logout when eula is rejected', function () {
      $httpBackend.flush();

      $httpBackend.expectDELETE('session/').respond(204);

      $modal.instances['common/login/assets/html/eula.html'].dismiss('dismiss');

      $httpBackend.flush();
    });

    it('should login when eula is accepted', function () {
      $httpBackend.flush();

      $modal.instances['common/login/assets/html/eula.html'].close();

      $rootScope.$digest();

      expect(navigate).toHaveBeenCalledWith();
    });
  });

  describe('unauthenticated user', function () {
    beforeEach(function () {
      var failedAuth = sessionFixtures.getFixture(function (fixture) {
        return fixture.status === 400;
      });

      $httpBackend.expectPOST('session/').respond.apply(null, failedAuth.toArray());

      _.extend(loginController, {username: 'badHacker', password: 'bruteForce'});
      loginController.submitLogin();
    });

    it('should have a rejected promise', function () {
      var err = jasmine.createSpy('err');

      loginController.validate.catch(err);

      $httpBackend.flush();
      $rootScope.$digest();

      expect(err).toHaveBeenCalled();
    });

    it('should update progress', function () {
      expect(loginController.inProgress).toBeTruthy();

      $httpBackend.flush();

      expect(loginController.inProgress).toBeFalsy();
    });
  });

  describe('non-superuser', function () {
    beforeEach(function () {
      var adminSession = sessionFixtures.getFixture(function (fixture) {
        return fixture.data.user && fixture.data.user.username === 'admin';
      });

      $httpBackend.expectGET('session/').respond.apply(null, adminSession.toArray());

      _.extend(loginController, {username: 'admin', password: 'foo'});
      loginController.submitLogin();

      $httpBackend.flush();
    });

    it('should be denied', function () {
      expect($modal.open.callCount).toEqual(1);

      expect($modal.open).toHaveBeenCalledWith({
        templateUrl: 'common/access-denied/assets/html/access-denied.html',
        keyboard: false,
        backdrop: 'static',
        controller: 'AccessDeniedCtrl',
        resolve: { message: jasmine.any(Function) }
      });
    });

    it('should not perform any further actions', function () {
      expect(navigate).not.toHaveBeenCalled();

      expect(loginController.inProgress).toBeTruthy();
    });
  });
});
