describe('Chart Utils', function () {
  'use strict';

  var chartUtils;

  beforeEach(module('charts'));

  beforeEach(inject(function (_chartUtils_) {
    chartUtils = _chartUtils_;
  }));

  it('should provide a function to translate points', function () {
    var x = 10, y = 20;

    var actual = chartUtils.translator(x, y);

    expect(actual).toEqual('translate(' + x + ',' + y + ')');
  });

  it('should provide a function to prepend a string with a period', function () {
    var str = 'foo';

    var actual = chartUtils.cl(str);

    expect(actual).toEqual('.' + str);
  });

  it('should add chartParamMixins as a function', function () {
    expect(chartUtils.chartParamMixins).toEqual(jasmine.any(Function));
  });
});