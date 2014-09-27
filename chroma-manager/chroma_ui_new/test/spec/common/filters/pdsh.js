describe('PDSH filter', function () {
  'use strict';

  var pdsh, items, hostPath;

  beforeEach(module('filters'));

  beforeEach(inject(function ($filter) {
    pdsh = $filter('pdsh');
  }));

  /**
   * Returns the host name given the item
   * @param {Object} item
   * @returns {String}
   */
  hostPath = function hostPath (item) {
    return item.host_name;
  };

  describe('General PDSH', function () {
    beforeEach(function () {
      items = [
        {host_name: 'hostname1'},
        {host_name: 'hostname2'},
        {host_name: 'hostname3'},
        {host_name: 'hostname4'},
        {host_name: 'hostname5'},
        {host_name: 'hostname6'},
        {host_name: 'hostname7'},
        {host_name: 'hostname8'},
        {host_name: 'hostname9'},
        {host_name: 'hostname10'}
      ];
    });

    it('should retrieve valid hostnames from the list of items', function () {
      var hostnames = {hostname2: 1, 'hostname7': 1};
      var result = pdsh(items, hostnames, hostPath, false);
      expect(result).toEqual([{host_name: 'hostname2'}, {host_name: 'hostname7'}]);
    });

    it('should retrieve matching substrings from the list of items with fuzzy match', function () {
      var hostnames = {hostname1: 1};
      var result = pdsh(items, hostnames, hostPath, true);
      expect(result).toEqual([{host_name: 'hostname1'}, {host_name: 'hostname10'}]);
    });

    it('should return no matches with fuzzy match turned off', function () {
      var hostnames = {hostname: 1};
      var result = pdsh(items, hostnames, hostPath, false);
      expect(result).toEqual([]);
    });

    it('should return no matches with fuzzy match', function () {
      var hostnames = {notinthere: 1};
      var result = pdsh(items, hostnames, hostPath, true);
      expect(result).toEqual([]);
    });
  });
});
