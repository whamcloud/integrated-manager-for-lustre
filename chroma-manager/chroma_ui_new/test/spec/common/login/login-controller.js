describe('Login Controller', function () {
  'use strict';

  var loginController, $window, $httpBackend, $modal, sessionFixture, sessionFixtures, $rootScope;
  var uiRoot = 'root/of/app';

  var userEulaStates = {
    EULA: 'eula',
    PASS: 'pass',
    DENIED: 'denied'
  };

  var helpText = {
    access_denied_eula: 'access denied :('
  };

  beforeEach(module('login', '$windowMock'));

  beforeEach(inject(function ($controller, _$httpBackend_, _$modal_, _$window_, _$rootScope_, fixtures) {
    $httpBackend = _$httpBackend_;
    $rootScope = _$rootScope_;
    $modal = _$modal_;
    $window = _$window_;
    sessionFixtures = fixtures.asName('session');

    loginController = $controller('LoginCtrl', {
      user_EULA_STATES: userEulaStates,
      HELP_TEXT: helpText,
      UI_ROOT: uiRoot
    });

    sessionFixture = sessionFixtures.getFixture(function (fixture) {
      return fixture.status === 200;
    });

    $httpBackend.whenPOST('session').respond(201);
    $httpBackend.whenGET('session').respond.apply(null, sessionFixture.toArray());
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('authenticated user', function () {
    var credentials = {
        username: 'foo',
        password: 'bar'
      };

    beforeEach(function () {
      $httpBackend.expectPOST('session', credentials).respond(201);

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
        resolve: jasmine.argThat(function(arg) {
          return typeof arg.user === 'function';
        })
      });
    });

    it('should redirect to base uri if api says so', function () {
      sessionFixture.data.user.eula_state = userEulaStates.PASS;
      $httpBackend.expectGET('session').respond.apply(null, sessionFixture.toArray());

      $httpBackend.flush();

      expect($modal.open.callCount).toEqual(0);
      expect($window.location.__hrefSpy__.callCount).toEqual(1);

      expect($window.location.__hrefSpy__).toHaveBeenCalledWith('root/of/app');
    });

    it('should logout when eula is rejected', function () {
      $httpBackend.flush();

      $httpBackend.expectDELETE('session').respond(204);

      $modal.instances['common/login/assets/html/eula.html'].dismiss('dismiss');

      $httpBackend.flush();
    });

    it('should login when eula is accepted', function () {
      $httpBackend.flush();

      $modal.instances['common/login/assets/html/eula.html'].close();

      $rootScope.$digest();

      expect($window.location.__hrefSpy__).toHaveBeenCalledWith('root/of/app');
    });
  });

  describe('unauthenticated user', function () {
    beforeEach(function () {
      var failedAuth = sessionFixtures.getFixture(function (fixture) {
        return fixture.status === 400;
      });

      $httpBackend.expectPOST('session').respond.apply(null, failedAuth.toArray());

      _.extend(loginController, {username: 'badHacker', password: 'bruteForce'});
      loginController.submitLogin();
    });

    it('should have a rejected promise', function () {
      var err = jasmine.createSpy('err');

      loginController.validate.promise.catch(err);

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

      $httpBackend.expectGET('session').respond.apply(null, adminSession.toArray());

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
      expect($window.location.__hrefSpy__).not.toHaveBeenCalled();

      expect(loginController.inProgress).toBeTruthy();
    });
  });
});
