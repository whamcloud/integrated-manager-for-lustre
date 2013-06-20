describe('Power Control', function () {
  'use strict';

  var $scope;

  beforeEach(module('controllers', 'ui.bootstrap'));

  beforeEach(module(function ($provide) {
    function getModelMock(name) {
      return {
        query: jasmine.createSpy(name).andReturn([])
      };
    }

    // Mock out deps.
    $provide.value('hostModel', getModelMock('hostModel'));
    $provide.value('PowerControlDeviceModel', getModelMock('PowerControlDeviceModel'));
    $provide.value('$dialog', {
      dialog: jasmine.createSpy('dialog').andReturn({
        open: jasmine.createSpy('dialogOpen')
      })
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
      asStatic: jasmine.createSpy('asStatic').andReturn('foo')
    };

    $scope.powerCtrl.createPdu();

    expect($dialog.dialog).toHaveBeenCalled();
    expect($dialog.dialog.plan().open).toHaveBeenCalledWith('foo', 'CreatePduCtrl');
  }));

  it('should delete a pdu', inject(function () {
    var device = {
      $delete: jasmine.createSpy('$delete').andReturn({
        then: jasmine.createSpy('then').andCallFake(function (arg) {
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
