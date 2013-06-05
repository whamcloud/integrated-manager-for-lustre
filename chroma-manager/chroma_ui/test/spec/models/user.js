describe('User model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'services'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));


  it('should return whether the eula should be displayed', inject(function (UserModel, $httpBackend) {
    $httpBackend.expectGET('/api/user/').respond({
      accepted_eula: false,
      is_superuser: true
    });

    var model = UserModel.get();

    $httpBackend.flush();

    expect(model.shouldShowEula()).toBeTruthy();

    model.accepted_eula = true;

    expect(model.shouldShowEula()).toBeFalsy();
  }));
});
