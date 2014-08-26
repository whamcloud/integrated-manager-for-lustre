describe('Confirm server action modal', function () {
  'use strict';

  beforeEach(module('server'));

  var $scope, $modalInstance, hosts, actionName, confirmServer;

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();

    $modalInstance = {
      close: jasmine.createSpy('close'),
      dismiss: jasmine.createSpy('dismiss')
    };

    hosts = [
      {}
    ];

    actionName = 'Install Updates';

    $controller('ConfirmServerActionModalCtrl', {
      $scope: $scope,
      $modalInstance: $modalInstance,
      hosts: hosts,
      actionName: actionName
    });

    confirmServer = $scope.confirmServerActionModal;
  }));

  it('should set hosts on the scope', function () {
    expect(confirmServer.hosts).toBe(hosts);
  });

  it('should set the actionName on the scope', function () {
    expect(confirmServer.actionName).toEqual(actionName);
  });

  it('should close the modal on go', function () {
    confirmServer.go();

    expect($modalInstance.close).toHaveBeenCalledOnceWith('go');
  });

  it('should dismiss the modal on cancel', function () {
    confirmServer.cancel();

    expect($modalInstance.dismiss).toHaveBeenCalledOnceWith('cancel');
  });

});
