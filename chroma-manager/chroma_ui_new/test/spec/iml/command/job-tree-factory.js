describe('Job tree', function () {
  'use strict';

  beforeEach(module('command', 'dataFixtures'));

  var jobTree, jobFixtures;

  beforeEach(inject(function (_jobTree_, _jobFixtures_) {
    jobTree = _jobTree_;
    jobFixtures = _jobFixtures_;
  }));

  it('should convert a job tree', function () {
    jobFixtures.forEach(function testItem (item) {
      var result = jobTree(item.in);

      expect(result).toEqual(item.out);
    });
  });
});
