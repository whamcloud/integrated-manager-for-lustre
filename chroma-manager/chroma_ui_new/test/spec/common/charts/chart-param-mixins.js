describe('chart utils', function () {
  'use strict';

  var chartUtilsMixins;

  beforeEach(module('charts', 'd3'));

  beforeEach(inject(function (_chartParamMixins_) {
    chartUtilsMixins = _chartParamMixins_;
  }));

  it('should return a configuration function', function () {
    expect(chartUtilsMixins).toEqual(jasmine.any(Function));
  });

  describe('exposing config object properties', function () {
    var config, mixin;

    beforeEach(function () {
      config = {
        foo: 'bar',
        margin:  {top: 20, right: 30, bottom: 40, left: 50}
      };

      mixin = chartUtilsMixins(config);
    });

    it('should provide a getter based on the config object properties', function () {
      expect(mixin.foo()).toEqual('bar');
    });

    it('should provide a setter based on the config object properties', function () {
      var value = 'baz';

      mixin.foo(value);

      expect(mixin.foo()).toEqual(value);
    });

    it('should clone the config to discourage relying on config mutation', function () {
      var value = 'baz';

      mixin.foo(value);

      expect(config.foo).toEqual('bar');
    });

    it('should have special getter/setters for certain well known keys', function () {
      var margin = {top: 0},
        expected = _.extend(config.margin, {top: 0});

      mixin.margin(margin);

      expect(mixin.margin()).toEqual(expected);
    });

    it('should mixin to a source if one is provided', function () {
      var source = {};

      chartUtilsMixins(config, source);

      expect(source.foo()).toEqual('bar');
    });
  });
});
