describe('Session model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'services'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));


  it('should patch it\'s get method to return a user model', inject(function (SessionModel, $httpBackend) {
    $httpBackend.expectGET('/api/session/').respond({
      user: {}
    });

    var model = SessionModel.get();

    $httpBackend.flush();

    expect(model.user.shouldShowEula).toBeDefined();
  }));
});
