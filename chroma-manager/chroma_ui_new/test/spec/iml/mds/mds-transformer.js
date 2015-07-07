describe('mds transformer', function () {
  'use strict';

  var mdsTransformer, mdsDataFixtures;

  beforeEach(module('mds', 'dataFixtures'));

  beforeEach(inject(function (_mdsTransformer_, _mdsDataFixtures_) {
    mdsTransformer = _mdsTransformer_;
    mdsDataFixtures = _mdsDataFixtures_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      mdsTransformer({});
    }

    expect(shouldThrow).toThrow('mdsTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    mdsTransformer(resp);

    expect(resp.body).toEqual([]);
  });

  it('should transform data as expected', function () {
    mdsDataFixtures.forEach(function (item) {
      var resp = mdsTransformer({body: item.in});

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
