describe('Session model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'interceptors', 'services'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));


  it('should intercept the GET response to create a user model', inject(function (SessionModel, $httpBackend) {
    $httpBackend.expectGET('/api/session/').respond({
      user: {}
    });

    var model = SessionModel.get();

    $httpBackend.flush();

    expect(model.user.$update).toBeDefined();
  }));
});
