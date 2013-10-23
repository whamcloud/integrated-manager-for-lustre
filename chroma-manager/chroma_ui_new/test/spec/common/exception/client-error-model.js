describe('client error model', function () {
  'use strict';

  beforeEach(module('exception', 'interceptors'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));


  it('should return the expected url', inject(function (ClientErrorModel, $httpBackend) {
    $httpBackend.expectGET('client_error/').respond(200);

    ClientErrorModel.get();

    $httpBackend.flush();
  }));
});
