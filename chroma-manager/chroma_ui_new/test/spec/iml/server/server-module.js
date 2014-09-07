describe('Server module', function() {
  'use strict';

  var $scope, pdshParser, pdshFilter, naturalSortFilter,
    server, $modal, serverSpark,  openCommandModal,
    selectedServers, serverActions, jobMonitor, alertMonitor, jobMonitorSpark,
    alertMonitorSpark, openLnetModal, openAddServerModal;

  beforeEach(module('server'));

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();

    $modal = {
      open: jasmine.createSpy('open').andReturn({
        result: {
          then: jasmine.createSpy('then')
        }
      })
    };

    serverSpark = jasmine.createSpy('serverSpark').andReturn({
      onValue: jasmine.createSpy('onValue'),
      end: jasmine.createSpy('end')
    });

    selectedServers = {
      servers: {},
      toggleType: jasmine.createSpy('toggleType'),
      addNewServers: jasmine.createSpy('addNewServers')
    };

    serverActions = [{
      value: 'Install Updates'
    }];

    openCommandModal = jasmine.createSpy('openCommandModal');

    openLnetModal = jasmine.createSpy('openLnetModal');

    openAddServerModal = jasmine.createSpy('openAddServerModal').andReturn({
      opened: {
        then: jasmine.createSpy('then')
      },
      result: {
        then: jasmine.createSpy('then')
      }
    });

    pdshParser = jasmine.createSpy('pdshParser');
    pdshFilter = jasmine.createSpy('pdshFilter');
    naturalSortFilter = jasmine.createSpy('naturalSortFilter').andCallFake(_.identity);

    jobMonitorSpark = {
      end: jasmine.createSpy('end')
    };
    alertMonitorSpark = {
      end: jasmine.createSpy('end')
    };

    jobMonitor = jasmine.createSpy('jobMonitor').andReturn(jobMonitorSpark);
    alertMonitor = jasmine.createSpy('alertMonitor').andReturn(alertMonitorSpark);

    $scope.$on = jasmine.createSpy('$on');

    $controller('ServerCtrl', {
      $scope: $scope,
      $modal: $modal,
      pdshParser: pdshParser,
      pdshFilter: pdshFilter,
      serverSpark: serverSpark,
      selectedServers: selectedServers,
      naturalSortFilter: naturalSortFilter,
      serverActions: serverActions,
      openCommandModal: openCommandModal,
      jobMonitor: jobMonitor,
      alertMonitor: alertMonitor,
      openLnetModal: openLnetModal,
      openAddServerModal: openAddServerModal
    });

    server = $scope.server;
  }));

  var expectedProperties = {
    maxSize: 10,
    itemsPerPage: 10,
    currentPage: 1,
    pdshFuzzy: false
  };

  Object.keys(expectedProperties).forEach(function verifyScopeValue (key) {
    describe('test initial values', function() {
      it('should have a ' + key + ' value of ' + expectedProperties[key], function () {
        expect(server[key]).toEqual(expectedProperties[key]);
      });
    });
  });

  describe('test table functionality', function () {
    it('should return an expanded pdsh expression when the expression is updated', function () {
      server.currentPage = 5;
      pdshParser.andReturn({expansion: ['expression1']});
      server.pdshUpdate('expression', ['expression']);
      expect(server.hostnames).toEqual(['expression']);
      expect(server.currentPage).toEqual(1);
    });

    it('should return the host name from getHostPath', function () {
      var hostname = server.getHostPath({address: 'hostname1.localdomain'});
      expect(hostname).toEqual('hostname1.localdomain');
    });

    it('should set the current page', function () {
      server.setPage(10);
      expect(server.currentPage).toEqual(10);
    });

    it('should have an ascending sorting class name', function () {
      server.inverse = true;
      expect(server.getSortClass()).toEqual('fa-sort-asc');
    });

    it('should return the correct items per page', function () {
      server.itemsPerPage = '6';
      expect(server.getItemsPerPage()).toEqual(6);
    });

    it('should have a descending sorting class name', function () {
      server.inverse = false;
      expect(server.getSortClass()).toEqual('fa-sort-desc');
    });

    it('should retrieve only the filtered items when calling getTotalItems', function () {
      server.hostnames = [
        'hostname1'
      ];

      pdshFilter.andReturn(['hostname1']);
      var result = server.getTotalItems();

      expect(result).toEqual(1);
      expect(pdshFilter).toHaveBeenCalledWith(server.servers.objects, server.hostnames, server.getHostPath, false);
    });

    it('should set table editable', function () {
      server.setEditable(true);

      expect(server.editable).toBe(true);
    });

    it('should set the editable name', function () {
      server.setEditName('Install Updates');

      expect(server.editName).toEqual('Install Updates');
    });

    it('should open a configure lnet dialog', function () {
      var record = {
        id: 1
      };

      server.configureLnet(record);

      expect(openLnetModal).toHaveBeenCalledOnceWith(record);
    });

    it('should open the addServer Dialog', function () {
      server.addServer();

      expect(openAddServerModal).toHaveBeenCalledOnce();
    });

    it('should get an action by value', function () {
      var result = server.getActionByValue('Install Updates');

      expect(result).toEqual({
        value: 'Install Updates'
      });
    });

    describe('running an action', function () {
      var handler;

      beforeEach(function () {
        selectedServers.servers = {
          'https://hostname1.localdomain.com': true
        };

        pdshFilter.andReturn([{
          fqdn: 'https://hostname1.localdomain.com'
        }]);

        server.runAction('Install Updates');

        handler = $modal.open.plan().result.then.mostRecentCall.args[0];
      });

      it('should open a confirmation modal', function () {
        expect($modal.open).toHaveBeenCalledOnceWith({
          templateUrl: 'iml/server/assets/html/confirm-server-action-modal.html',
          controller: 'ConfirmServerActionModalCtrl',
          windowClass: 'confirm-server-action-modal',
          keyboard: false,
          backdrop: 'static',
          resolve: {
            action: jasmine.any(Function),
            hosts: jasmine.any(Function)
          }
        });
      });

      it('should register a then listener', function () {
        expect($modal.open.plan().result.then).toHaveBeenCalledOnceWith(jasmine.any(Function));
      });

      it('should stop editing when confirmed', function () {
        handler();

        expect(server.editable).toBe(false);
      });

      it('should open the command modal', function () {
        handler({ foo: 'bar' });

        expect(openCommandModal).toHaveBeenCalledOnceWith({
          body: {
            objects: [{ foo: 'bar' }]
          }
        });
      });
    });
  });

  describe('override action click', function () {
    var record, action;

    beforeEach(function () {
      record = {
        state: 'undeployed',
        install_method: 'root_password'
      };

      action = {
        state: 'deployed'
      };
    });

    it('should be a function', function () {
      expect(server.overrideActionClick).toEqual(jasmine.any(Function));
    });

    it('should fallback without an action state', function () {
      server.overrideActionClick(record, {}).then(function (resp) {
        expect(resp).toEqual('fallback');
      });

      $scope.$digest();
    });

    it('should open the add server modal when needed', function () {
      server.overrideActionClick(record, action).then(function () {
        expect(openAddServerModal).toHaveBeenCalledOnceWith(record);
      });

      $scope.$digest();
    });
  });

  describe('destroy', function () {
    beforeEach(function () {
      var handler = $scope.$on.mostRecentCall.args[1];
      handler();
    });

    it('should listen', function () {
      expect($scope.$on).toHaveBeenCalledWith('$destroy', jasmine.any(Function));
    });

    it('should end the jobMonitor on destroy', function () {
      expect(jobMonitorSpark.end).toHaveBeenCalledOnce();
    });

    it('should end the alertMonitor on destroy', function () {
      expect(alertMonitorSpark.end).toHaveBeenCalledOnce();
    });
  });
});
