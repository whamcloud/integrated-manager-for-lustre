describe('Natural Sort Filter', function () {
  'use strict';

  var naturalSort, hostnames, expected, predicate;

  beforeEach(module('filters'));

  beforeEach(inject(function ($filter) {
    naturalSort = $filter('naturalSort');

    hostnames = [
      'hostname0012',
      'alpa001',
      '4delta5kappa',
      'hostname005',
      'beta002',
      'hostname006',
      'hostname007',
      'hostname0015',
      'hostname008',
      'delta003gammamoretext',
      'hostname009',
      'hostname0010',
      'delta004alpha',
      'hostname0011',
      'hostname0013',
      'hostname0014',
      80,
      'delta003gamma'
    ];

    expected = [
      '4delta5kappa',
      80,
      'alpa001',
      'beta002',
      'delta003gamma',
      'delta003gammamoretext',
      'delta004alpha',
      'hostname005',
      'hostname006',
      'hostname007',
      'hostname008',
      'hostname009',
      'hostname0010',
      'hostname0011',
      'hostname0012',
      'hostname0013',
      'hostname0014',
      'hostname0015'
    ];

    predicate = function predicate (val) {
      return val;
    };

  }));

  it('should sort the hostnames array in natural order', function () {
    var naturalSortedHostNames = naturalSort(hostnames, predicate);
    expect(naturalSortedHostNames).toEqual(expected);
  });

  it('should sort the hostnames array in natural order and return the reversed array', function () {
    var naturalSortedHostNames = naturalSort(hostnames, predicate, true);
    expect(naturalSortedHostNames).toEqual(expected.reverse());
  });
});
