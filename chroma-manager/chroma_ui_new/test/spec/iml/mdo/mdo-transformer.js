describe('mdo transformer', function () {
  'use strict';

  var mdoTransformer, mdoDataFixtures;

  beforeEach(module('mdo', 'dataFixtures'));

  beforeEach(inject(function (_mdoTransformer_, _mdoDataFixtures_) {
    mdoTransformer = _mdoTransformer_;
    mdoDataFixtures = _mdoDataFixtures_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      mdoTransformer({});
    }

    expect(shouldThrow).toThrow('mdoTransformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    mdoTransformer(resp);

    expect(resp.body).toEqual([]);
  });

  it('should transform data as expected', function () {
    mdoDataFixtures.forEach(function (item) {
      var resp = mdoTransformer({body: item.in});

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