describe('Eula', function () {
  'use strict';

  var $scope;
  var $window;

  beforeEach(module('login'));

  beforeEach(module(function ($provide) {
    // Mock out deps.
    $provide.value('dialog', {
      close: jasmine.createSpy('dialogClose')
    });

    $provide.value('doneCallback', jasmine.createSpy('doneCallback'));
  }));

  beforeEach(inject(function ($controller, $rootScope, UserModel) {
    $scope = $rootScope.$new();

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

    $controller('EulaCtrl', {$scope: $scope, user: new UserModel(), $window: $window, HELP_TEXT: {eula: 'foo'}});
  }));

  it('should have actions accept and reject the eula', function () {
    expect($scope.eulaCtrl.accept).toEqual(jasmine.any(Function));
    expect($scope.eulaCtrl.reject).toEqual(jasmine.any(Function));
  });

  it('should update the user on accept', inject(function (doneCallback, dialog, $httpBackend) {
    $httpBackend.expectPUT('/api/user/', {accepted_eula: true}).respond(202);

    $scope.eulaCtrl.accept();

    expect(dialog.close).not.toHaveBeenCalled();

    expect(doneCallback).not.toHaveBeenCalled();

    $httpBackend.flush();

    expect(dialog.close).toHaveBeenCalled();

    expect(doneCallback).toHaveBeenCalled();
  }));

  it('should perform the appropriate actions on reject',
    inject(function (doneCallback, dialog, $httpBackend, $browser) {
      $httpBackend.expectPUT('/api/user/', {accepted_eula: false}).respond(202);
      $httpBackend.expectDELETE('/api/session/').respond(204);

      $scope.eulaCtrl.reject();

      // Flush the PUT
      $httpBackend.flush(1);

      expect(dialog.close).toHaveBeenCalled();

      // Flush the DELETE
      $httpBackend.flush(1);

      expect(doneCallback).not.toHaveBeenCalled();

      expect($window.location.href).toHaveBeenCalledOnceWith($browser.url());
    }
  ));
});
