describe('heat map chart', function () {
  'use strict';

  var heatMapChartFactory;

  beforeEach(module('charts', 'nvMock'));

  beforeEach(inject(function (_heatMapChartFactory_) {
    heatMapChartFactory = _heatMapChartFactory_;
  }));

  it('should have destroy as noop before selection has been passed', function () {
    expect(heatMapChartFactory().destroy).toBe(_.noop);
  });
});