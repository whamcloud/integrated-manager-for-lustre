describe('server detail modal controller', function () {
  'use strict';

  describe('controller', function () {
    beforeEach(module('server'));

    var $scope, $modalInstance, item, itemScope, myServer;

    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();

      $modalInstance = {
        close: jasmine.createSpy('close'),
        dismiss: jasmine.createSpy('dismiss')
      };

      item = {
        id: 1,
        address: 'foo1.localdomain'
      };
      itemScope = {
        servers: {
          objects: [
            {
              id: 1,
              address: 'foo1.localdomain'
            }
          ]
        }
      };

      $controller('ServerDetailModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        item: item,
        itemScope: itemScope
      });

      myServer = $scope.serverDetailModal.item;
    }));

    it('should set item on the scope', function () {
      expect(myServer).toEqual(item);
    });

    it('should dismiss the modal on close', function () {
      $scope.serverDetailModal.close();

      expect($modalInstance.dismiss).toHaveBeenCalledOnceWith('close');
    });

    it('should contain 1 alert', function () {
      expect($scope.serverDetailModal.alerts.length).toEqual(1);
    });

    it('should contain an alert message', function () {
      expect($scope.serverDetailModal.alerts[0].msg).toEqual('The information below describes' +
        ' the last state of foo1.localdomain before it was removed.');
    });

    it('should contain the address', function () {
      expect($scope.serverDetailModal.address).toEqual(item.address);
    });

    it('should not be removed', function () {
      expect($scope.serverDetailModal.removed).toEqual(false);
    });

    describe('closing the alert', function () {
      beforeEach(function () {
        $scope.serverDetailModal.closeAlert(0);
      });

      it('should not contain an alert', function () {
        expect($scope.serverDetailModal.alerts.length).toEqual(0);
      });
    });

    describe('removing the server', function () {
      beforeEach(function () {
        itemScope.servers.objects.pop();
        myServer = $scope.serverDetailModal.item;
      });

      it('should contain the last server state', function () {
        expect(myServer).toEqual(item);
      });

      it('should be in removed status', function () {
        expect($scope.serverDetailModal.removed).toEqual(true);
      });

      it('should set teh currentItem to item', function () {
        expect($scope.serverDetailModal.currentItem).toEqual(item);
      });

    });
  });

  describe('Open Server Detail Modal', function () {

    var $modal, openServerDetailModal, data;
    beforeEach(module('server', function ($provide) {
      $modal = {
        open: jasmine.createSpy('open')
      };

      $provide.value('$modal', $modal);
    }));

    beforeEach(inject(function (_openServerDetailModal_) {
      openServerDetailModal = _openServerDetailModal_;

      data = {
        item: {},
        itemScope: {}
      };

      openServerDetailModal(data.item, data.itemScope);
    }));

    it('should call the open method on $modal', function () {
      expect($modal.open).toHaveBeenCalledOnceWith({
        templateUrl: 'iml/server/assets/html/server-detail-modal.html',
        controller: 'ServerDetailModalCtrl',
        keyboard: false,
        backdrop: 'static',
        resolve: {
          item: jasmine.any(Function),
          itemScope: jasmine.any(Function)
        }
      });
    });

    ['item', 'itemScope'].forEach(function testGetter (getterName) {
      describe('get ' + getterName, function () {
        var getter, myValue;
        beforeEach(function () {
          getter = $modal.open.mostRecentCall.args[0].resolve[getterName];
          myValue = getter();
        });

        it('should return the item passed into the service', function () {
          expect(myValue).toBe(data[getterName]);
        });
      });
    });
  });
});
