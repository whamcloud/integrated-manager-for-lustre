describe('ost-balance-transformer', function () {
  'use strict';

  var ostBalanceTransformer, ostBalanceDataFixtures, stream;

  beforeEach(module('ostBalance', 'dataFixtures'));

  beforeEach(inject(function (_ostBalanceTransformer_, _ostBalanceDataFixtures_) {
    ostBalanceTransformer = _ostBalanceTransformer_;
    ostBalanceDataFixtures = _ostBalanceDataFixtures_;

    stream = {};
  }));

  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      ostBalanceTransformer.call(stream, {});
    }

    expect(shouldThrow).toThrow('ostBalanceTransformer expects resp.body to be an object!');
  });

  it('should transform data', function () {
    ostBalanceDataFixtures.forEach(function (item) {
      var resp = ostBalanceTransformer.call(stream, {body: item.in});

      expect(resp.body).toEqual(item.out);
    });
  });
});