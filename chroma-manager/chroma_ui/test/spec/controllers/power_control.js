describe('Power Control', function () {
  'use strict';

  var $scope, dialogInstance;

  beforeEach(module('controllers', 'ui.bootstrap'));

  beforeEach(module(function ($provide) {
    function getModelMock(name) {
      return {
        query: jasmine.createSpy(name).and.returnValue([])
      };
    }

    // Mock out deps.
    $provide.value('hostModel', getModelMock('hostModel'));
    $provide.value('PowerControlDeviceModel', getModelMock('PowerControlDeviceModel'));

    dialogInstance = {
      open: jasmine.createSpy('dialogOpen')
    };
    $provide.value('$dialog', {
      dialog: jasmine.createSpy('dialog').and.returnValue(dialogInstance)
    });
    $provide.value('pageTitle', {
      set: jasmine.createSpy('set')
    });
  }));

  beforeEach(inject(function ($controller, $rootScope) {
    $scope = $rootScope.$new();

    $controller('PowerCtrl', {$scope: $scope});
  }));

  it('should have the expected scope properties', function () {
    expect($scope.powerCtrl).toEqual(jasmine.any(Object));
    expect($scope.powerCtrl.hosts).toEqual(jasmine.any(Array));
    expect($scope.powerCtrl.powerControlDevices).toEqual(jasmine.any(Array));

    expect($scope.powerCtrl.createPdu).toEqual(jasmine.any(Function));
  });

  it('should instantiate the pdu dialog', inject(function ($dialog) {
    $scope.config = {
      asStatic: jasmine.createSpy('asStatic').and.returnValue('foo')
    };

    $scope.powerCtrl.createPdu();

    expect($dialog.dialog).toHaveBeenCalled();
    expect(dialogInstance.open).toHaveBeenCalledWith('foo', 'CreatePduCtrl');
  }));

  it('should delete a pdu', inject(function () {
    var device = {
      $delete: jasmine.createSpy('$delete').and.returnValue({
        then: jasmine.createSpy('then').and.callFake(function (arg) {
          arg();
        })
      })
    };

    $scope.powerCtrl.powerControlDevices = [device];
    $scope.powerCtrl.deletePdu(device);

    expect(device.$delete).toHaveBeenCalled();
    expect($scope.powerCtrl.powerControlDevices.length).toBe(0);
  }));
});
