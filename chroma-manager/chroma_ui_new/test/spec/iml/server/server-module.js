describe('Server module', function() {
  'use strict';

  var $scope, controller, pdshParser, pdshFilter, server;

  beforeEach(module('server'));

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();
    pdshParser = jasmine.createSpy('pdshParser');
    pdshFilter = jasmine.createSpy('pdshFilter');
    controller = $controller('ServerCtrl', {
      $scope: $scope,
      pdshParser: pdshParser,
      pdshFilter: pdshFilter
    });

    server = $scope.server;
  }));

  var expectedProperties = {
    maxSize: 10,
    itemsPerPage: 10,
    currentPage: 1,
    pdshFuzzy: false
  };

  it ('should have 100 server entries', function () {
    expect(server.servers.objects.length).toEqual(100);
  });

  Object.keys(expectedProperties).forEach(function verifyScopeValue (key) {
    describe('test initial values', function() {
      it('should have a ' + key + ' value of ' + expectedProperties[key], function () {
        expect(server[key]).toEqual(expectedProperties[key]);
      });
    });
  });

  describe('test table functionality', function () {
    it('should have 100 items', function () {
      expect(server.getTotalItems()).toEqual(100);
    });

    it('should return an expanded pdsh expression when the expression is updated', function () {
      server.currentPage = 5;
      pdshParser.andReturn({expansion: ['expression1']});
      server.pdshUpdate('expression');
      expect(pdshParser).toHaveBeenCalledWith('expression');
      expect(server.hostnames).toEqual(['expression1']);
      expect(server.currentPage).toEqual(1);
    });

    it('should return the host name from getHostPath', function () {
      var hostname = server.getHostPath({host_name: 'hostname1'});
      expect(hostname).toEqual('hostname1');
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
  });
});
