describe('server detail modal controller', function () {
  'use strict';

  describe('controller', function () {
    beforeEach(module('server'));

    var $scope, $modalInstance, item, itemScope, myServer, overrideActionClick, serverSpark, selectedServers;

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
        },
        jobMonitorSpark: jasmine.createSpy('jobMonitorSpark'),
        alertMonitorSpark: jasmine.createSpy('alertMonitorSpark')
      };

      overrideActionClick = jasmine.createSpy('overrideActionClick')
        .andReturn(jasmine.createSpy('overrideActionClickService'));

      serverSpark = jasmine.createSpy('serverSpark')
        .andReturn({
          onValue: jasmine.createSpy('onValue')
        });

      selectedServers = {
        addNewServers: jasmine.createSpy('addNewServers')
      };

      $controller('ServerDetailModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        item: item,
        itemScope: itemScope,
        serverSpark: serverSpark,
        selectedServers: selectedServers,
        overrideActionClick: overrideActionClick
      });

      myServer = $scope.serverDetailModal.item;
    }));

    it('should set item on the scope', function () {
      expect(myServer).toEqual(item);
    });

    it('should contain the job monitor spark', function () {
      expect($scope.serverDetailModal.jobMonitorSpark).toEqual(itemScope.jobMonitorSpark);
    });

    it('should contain the alert monitor spark', function () {
      expect($scope.serverDetailModal.alertMonitorSpark).toEqual(itemScope.alertMonitorSpark);
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

    describe('overrideActionClick', function () {
      it('should call overrideActionClick', function () {
        expect(overrideActionClick).toHaveBeenCalledWith(jasmine.any(Object));
      });

      it('should return the overrideActionClick service', function () {
        expect($scope.serverDetailModal.overrideActionClick).toEqual(overrideActionClick.plan());
      });
    });

    describe('server spark', function () {
      it('should invoke the server spark', function () {
        expect(serverSpark).toHaveBeenCalledOnce();
      });

      it('should call addNewServers when new data arrives on the spark', function () {
        expect(serverSpark.plan().onValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
      });

      it('should call selectedServers.addNewServers when new data arrives on the spark', function () {
        serverSpark.plan().onValue.mostRecentCall.args[1]({
          body: {
            objects: [
              {id: 1}
            ]
          }
        });

        expect(selectedServers.addNewServers).toHaveBeenCalledOnceWith([{id: 1}]);
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
