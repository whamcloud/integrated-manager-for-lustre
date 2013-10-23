describe('Eula', function () {
  'use strict';

  var $scope, $httpBackend, $modalInstance;

  beforeEach(module('login', function ($provide) {
    $provide.value('help', {
      get: jasmine.createSpy('get').andCallFake(function () {
        return 'foo';
      })
    });
  }));

  mock.beforeEach('$modal');

  beforeEach(inject(function ($controller, $rootScope, $modal, _$httpBackend_, UserModel) {
    $scope = $rootScope.$new();
    $httpBackend = _$httpBackend_;
    $modalInstance = $modal.open({templateUrl: 'modalTemplate'});

    $controller('EulaCtrl', {
      $scope: $scope,
      $modalInstance: $modalInstance,
      user: new UserModel()
    });
  }));

  it('should update the user on accept', function () {
    $httpBackend.expectPUT('user/', {accepted_eula: true}).respond(202);

    $scope.eulaCtrl.accept();

    expect($modalInstance.close).not.toHaveBeenCalled();

    $httpBackend.flush();

    expect($modalInstance.close).toHaveBeenCalled();
  });

  it('should perform the appropriate actions on reject', function () {
    $httpBackend.expectPUT('user/', {accepted_eula: false}).respond(202);

    expect($modalInstance.dismiss).not.toHaveBeenCalled();

    $scope.eulaCtrl.reject();

    $httpBackend.flush();

    expect($modalInstance.dismiss).toHaveBeenCalled();
  });
});
