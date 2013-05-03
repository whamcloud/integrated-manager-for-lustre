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
    expect($scope.powerCtrl.getOptionClass).toEqual(jasmine.any(Function));

    expect($scope.powerCtrl.createPdu).toEqual(jasmine.any(Function));
    expect($scope.powerCtrl.formatTagCssClass).toEqual(jasmine.any(Function));
    expect($scope.powerCtrl.formatResult).toEqual(jasmine.any(Function));

  });

  it('should provide the needed classes', function () {
    var outlet = {
      hasPower: jasmine.createSpy('hasPower').andReturn('on'),
      isAvailable: jasmine.createSpy('isAvailable').andReturn(true)
    };

    var result = $scope.powerCtrl.getOptionClass(outlet);

    expect(result).toEqual(['on']);

    outlet.host = '1/2/3';
    outlet.isAvailable = jasmine.createSpy('isAvailable').andReturn(false);

    result = $scope.powerCtrl.getOptionClass(outlet);

    expect(result).toEqual(['on', 'select2-selected']);
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

  describe('Formatting select2 element', function () {
    var element;
    var elementScope;

    beforeEach(inject(function createElement($rootScope) {
      element = angular.element('<div />');
      elementScope = $rootScope.$new();
      element.data('$scope', elementScope);
    }));

    it('should format the tag css class', function () {
      elementScope.outlet = {
        hasPower: jasmine.createSpy('hasPower').andReturn('unknown')
      };

      var result = $scope.powerCtrl.formatTagCssClass({element: element});

      expect(elementScope.outlet.hasPower).toHaveBeenCalled();

      expect(result).toEqual('unknown');
    });

    it('should format the result', function () {
      elementScope.outlet = {
        identifier: 'foo'
      };

      var result = $scope.powerCtrl.formatResult({element: element});

      expect(result).toEqual('Outlet: foo');
    });
  });

});
