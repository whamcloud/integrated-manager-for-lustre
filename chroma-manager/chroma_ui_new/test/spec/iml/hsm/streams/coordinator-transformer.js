describe('HSM coordinator transformer', function () {
  'use strict';

  var hsmCdtTransformer, hsmCdtDataFixtures;

  beforeEach(module('hsm', 'dataFixtures'));

  beforeEach(inject(function (_hsmCdtTransformer_, _hsmCdtDataFixtures_) {
    hsmCdtTransformer = _hsmCdtTransformer_;
    hsmCdtDataFixtures = _hsmCdtDataFixtures_;
  }));

  it('should throw if resp.body is not an array', function () {
    function shouldThrow() {
      hsmCdtTransformer({});
    }

    expect(shouldThrow).toThrow('Transformer expects resp.body to be an array!');
  });

  it('should resolve early if resp.body is an empty array', function () {
    var resp = {body: []};

    hsmCdtTransformer(resp);

    expect(resp.body).toEqual([]);
  });

  it('should transform data as expected', function () {
    hsmCdtDataFixtures.forEach(function (item) {
      var resp = hsmCdtTransformer({body: item.in});

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
