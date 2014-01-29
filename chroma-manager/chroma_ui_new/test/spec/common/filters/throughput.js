describe('Throughput Filter', function () {
  'use strict';

  var throughput;

  beforeEach(module('filters', 'charts'));

  beforeEach(inject(function($filter) {
    throughput = $filter('throughput');
  }));

  var tests = [
    {input: 1000, expected: '1000 B/s'},
    {input: 1000, bps: true, expected: '7.813 kb/s'},
    {input: 3045827469, expected: '2.837 GB/s'},
    {input: 3045827469, bps: true, expected: '22.69 Gb/s'},
    {input: NaN, expected: ''},
    {input: 'quack', expected: ''}
  ];

  tests.forEach(function runTest(test) {
    it(getDescription(test.input, test.expected), function expectFormat() {
      var result = throughput(test.input, test.bps);

      expect(test.expected).toEqual(result);
    });

  });

  function getDescription(input, expected) {
    var description = 'should convert %s to %s';

    return description.sprintf(input, expected);
  }
});
