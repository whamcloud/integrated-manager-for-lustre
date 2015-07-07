describe('read write bandwidth transformer', function () {
  'use strict';

  var readWriteBandwidthTransformer, readWriteBandwidthDataFixtures;

  beforeEach(module('readWriteBandwidth', 'dataFixtures'));

  beforeEach(inject(function (_readWriteBandwidthTransformer_, _readWriteBandwidthDataFixtures_) {
    readWriteBandwidthTransformer = _readWriteBandwidthTransformer_;
    readWriteBandwidthDataFixtures = _readWriteBandwidthDataFixtures_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      readWriteBandwidthTransformer({});
    }

    expect(shouldThrow).toThrow('readWriteBandwidthTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    readWriteBandwidthTransformer(resp);

    expect(resp.body).toEqual([]);
  });

  it('should transform data as expected', function () {
    readWriteBandwidthDataFixtures.forEach(function (item) {
      var resp = readWriteBandwidthTransformer({body: item.in});

      var data = resp.body;

      data.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      expect(data).toEqual(item.out);
    });
  });
});
