describe('HumanBytes Filter', function () {
  'use strict';

  var humanBytes;

  beforeEach(module('filters', 'charts'));

  beforeEach(inject(function($filter) {
    humanBytes = $filter('humanBytes');
  }));

  var tests = [
    {input: 1000, expected: '1000 B'},
    {input: 1000, args: 0, expected: '1000 B'},
    {input: 1024, args: 0, expected: '1.000 kB'},
    {input: 4326, args: 5, expected: '4.2246 kB'},
    {input: 3045827469, expected: '2.837 GB'},
    {input: 84567942345572238, expected: '75.11 PB'},
    {input: 5213456204567832146028, expected: '4.416 ZB'},
    {input: NaN, expected: ''},
    {input: 'quack', expected: ''}
  ];

  tests.forEach(function runTest(test) {
    it(getDescription(test.input, test.expected), function expectFormat() {
      var result = humanBytes(test.input, test.args);

      expect(test.expected).toEqual(result);
    });

  });

  function getDescription(input, expected) {
    var description = 'should convert %s to %s';

    return description.sprintf(input, expected);
  }
});
