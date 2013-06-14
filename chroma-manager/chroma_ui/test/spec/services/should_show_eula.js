describe('Should Show Eula service', function () {
  'use strict';

  var Dialog;
  var $httpBackend;
  var doneCallback;

  beforeEach(module('services', 'models', 'ngResource', 'ui.bootstrap'));

  beforeEach(module(function ($provide) {
    doneCallback = jasmine.createSpy('doneCallback');

    $provide.value('credentials', {
      username: 'foo',
      password: 'bar'
    });

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

  beforeEach(inject(function ($injector) {
    $httpBackend = $injector.get('$httpBackend');

    $injector.get('$rootScope').config = {
      asStatic: angular.identity
    };
  }));

  function createExpectation(userObj) {
    $httpBackend.expectGET('/api/session/').respond({
      user: userObj
    });

    $httpBackend.expectDELETE('/api/session/').respond(204);

    if (userObj.accepted_eula) {
      $httpBackend.expectPOST('/api/session/').respond(201);
    }
  }

  it('should allow a non-superuser with an accepted eula', inject(function (shouldShowEula, $httpBackend) {
    createExpectation({
      accepted_eula: true,
      is_superuser: false
    });

    shouldShowEula(doneCallback);

    $httpBackend.flush();

    expect(doneCallback).toHaveBeenCalled();

    expect(Dialog.prototype.open).not.toHaveBeenCalled();
  }));

  it('should block a non-allowed user', inject(function (shouldShowEula, $httpBackend) {
    createExpectation({
      accepted_eula: false,
      is_superuser: false
    });

    shouldShowEula(doneCallback);

    $httpBackend.flush();

    expect(doneCallback).not.toHaveBeenCalled();

    expect(Dialog.prototype.open).toHaveBeenCalledWith('partials/dialogs/access_denied.html', 'AccessDeniedCtrl');
  }));

  it('should allow an authorized superuser', inject(function (shouldShowEula, $httpBackend) {
    createExpectation({
      accepted_eula: true,
      is_superuser: true
    });

    shouldShowEula(doneCallback);

    $httpBackend.flush();

    expect(doneCallback).toHaveBeenCalled();

    expect(Dialog.prototype.open).not.toHaveBeenCalled();
  }));

  it('should show the eula to a superuser who has not accepted', inject(function (shouldShowEula, $httpBackend) {
    createExpectation({
      accepted_eula: false,
      is_superuser: true
    });

    shouldShowEula(doneCallback);

    $httpBackend.flush();

    expect(doneCallback).not.toHaveBeenCalled();

    expect(Dialog.prototype.open).toHaveBeenCalledWith('partials/dialogs/eula.html', 'EulaCtrl');
  }));
});
