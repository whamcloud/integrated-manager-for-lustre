describe('big green button ctrl', function () {
  'use strict';

  beforeEach(module('controllers'));

  var $rootScope, $scope, healthModel;

  beforeEach(inject(function ($controller, _$rootScope_) {
    $rootScope = _$rootScope_;
    $scope = $rootScope.$new();
    healthModel = jasmine.createSpy('healthModel');

    $controller('BigGreenButtonCtrl', {
      $scope: $scope,
      healthModel: healthModel
    });
  }));

  it('should invoke the healthModel', function () {
    expect(healthModel).toHaveBeenCalledOnce();
  });

  it('should update the status when health is broadcast', function () {
    var newHealth = {
      health: 'GOOD',
      count: 10
    };

    $rootScope.$broadcast('health', newHealth);

    expect($scope.bigGreen.status).toEqual(newHealth);
  });

  it('should expose a count property', function () {
    $scope.bigGreen.status.count = 5;

    expect($scope.bigGreen.count).toBe(5);
  });

  it('should return the limit from count when it is > 99', function () {
    $scope.bigGreen.status.count = 100;

    expect($scope.bigGreen.count).toBe(99);
  });

  it('should expose an aboveLimit property', function () {
    $scope.bigGreen.status.count = 5;

    expect($scope.bigGreen.aboveLimit).toBe(false);
  });

  it('should be above the limit when count > 99', function () {
    $scope.bigGreen.status.count = 300;

    expect($scope.bigGreen.aboveLimit).toBe(true);
  });
});
