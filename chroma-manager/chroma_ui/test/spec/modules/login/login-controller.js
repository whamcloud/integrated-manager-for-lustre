describe('Login', function () {
  'use strict';

  var $scope;
  var $httpBackend;
  var Dialog;
  var EULA_STATES;
  var $window;

  beforeEach(module('login', 'interceptors'));

  beforeEach(module(function ($provide) {
    $provide.value('HELP_TEXT', {
      access_denied_eula: 'foo'
    });

    $provide.decorator('$dialog', function ($delegate) {
      //Patch up the $dialog with a spy.
      var dialog = $delegate.dialog();
      Dialog = dialog.constructor;
      Dialog.prototype = Object.getPrototypeOf(dialog);

      window.spyOn(Dialog.prototype, 'open');

      $delegate.dialog = function (opts) {
        return new Dialog(opts);
      };

      return $delegate;
    });
  }));

  beforeEach(inject(function ($rootScope, $controller, _$httpBackend_, user_EULA_STATES) {
    $scope = $rootScope.$new();
    $httpBackend = _$httpBackend_;
    EULA_STATES = user_EULA_STATES;

    //We're not testing asStatic so modify it to return it's caller.
    $rootScope.config = {
      asStatic: angular.identity
    };

    var hrefSpy = jasmine.createSpy('hrefSpy');

    // Mock out $window.location.href to retrieve it's value later.
    $window = {
      location: Object.create(null, {
        href: {
          set: function (newLocation) {
            hrefSpy(newLocation);
          },
          get: function () {
            return hrefSpy;
          }
        }
      })
    };

    $controller('LoginCtrl', {$scope: $scope, $window: $window});
  }));


  function createExpectation(userObj) {
    $httpBackend.expectPOST('/api/session/').respond(201);

    $httpBackend.expectGET('/api/session/').respond({user: userObj});
  }

  it('should allow a user with an accepted eula', inject(function (UI_ROOT) {
    createExpectation({eula_state: EULA_STATES.PASS});

    $scope.login.submitLogin();

    $httpBackend.flush();

    expect($window.location.href).toHaveBeenCalledWith(UI_ROOT);

    expect(Dialog.prototype.open).not.toHaveBeenCalled();
  }));

  it('should deny a user', function () {
    createExpectation({eula_state: EULA_STATES.DENIED});

    $scope.login.submitLogin();

    $httpBackend.flush();

    expect($window.location.href).not.toHaveBeenCalled();

    expect(Dialog.prototype.open).toHaveBeenCalledWith('partials/dialogs/access_denied.html', 'AccessDeniedCtrl');
  });

  it('should show the eula to a user who has not accepted', function () {
    createExpectation({eula_state: EULA_STATES.EULA});

    $scope.login.submitLogin();

    $httpBackend.flush();

    expect($window.location.href).not.toHaveBeenCalled();

    expect(Dialog.prototype.open).toHaveBeenCalledWith('js/modules/login/assets/html/eula.html', 'EulaCtrl');
  });

});
