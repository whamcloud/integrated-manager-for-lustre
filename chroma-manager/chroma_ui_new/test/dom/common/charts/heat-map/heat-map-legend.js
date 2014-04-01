describe('heat map legend DOM testing', function () {
  'use strict';

  var heatMapLegend, raf, $legendGroup, legendGroup, $el, d3, getMin, getMax, getSteps;

  beforeEach(module('charts', 'd3'));

  mock.beforeEach('chartUtils', 'raf');

  beforeEach(inject(function (heatMapLegendFactory, _d3_, _raf_, chartUtils) {
    d3 = _d3_;
    raf = _raf_;

    chartUtils.chartParamMixins.andCallThrough();
    chartUtils.cl.andCallThrough();
    chartUtils.translator.andCallThrough();
    chartUtils.getBBox.andReturn({ width: 100 });

    $el = angular.element('<svg class="foo"><g></g></svg>');
    $legendGroup = $el.find('g');

    getMin = $el.find.bind($el, '.min');
    getMax = $el.find.bind($el, '.max');
    getSteps = $el.find.bind($el, '.steps');

    legendGroup = d3.select($legendGroup[0]);

    heatMapLegend = heatMapLegendFactory();
  }));

  describe('empty data set', function () {
    it('should be empty with no data', function () {
      setup([]);

      expect($legendGroup.children().length).toBe(0);
    });

    it('should be empty with no values', function () {
      setup([
        {
          values: []
        }
      ]);

      expect($legendGroup.children().length).toBe(0);
    });
  });

  it('should be empty with one point', function () {
    setup([
      {
        values: [
          {z: 5}
        ]
      }
    ]);

    expect($legendGroup.children().length).toBe(0);
  });

  it('should have destroy as noop before selection has been passed', function () {
    expect(heatMapLegend.destroy).toBe(_.noop);
  });

  describe('multiple points', function () {
    beforeEach(function () {
      setup([
        {
          values: [
            {z: 5},
            {z: 6}
          ]
        }
      ]);

      raf.requestAnimationFrame.flush();
    });

    it('should list the min', function () {
      expect(getMin().text()).toEqual('Min: 5');
    });

    it('should list the max', function () {
      expect(getMax().text()).toEqual('Max: 6');
    });

    it('should translate the steps position', function () {
      expect(getSteps().attr('transform')).toEqual('translate(105,5)');
    });

    it('should set the max x position', function () {
      expect(getMax().attr('x')).toEqual('210');
    });

    it('should set the dy for min', function () {
      expect(getMin().attr('dy')).toEqual('1.2em');
    });

    it('should set the dy for max', function () {
      expect(getMax().attr('dy')).toEqual('1.2em');
    });
  });

  describe('destroy', function () {
    var $body;

    beforeEach(function () {
      $body = angular.element('body');

      setup([
        {
          values: [
            {z: 5},
            {z: 6}
          ]
        }
      ]);

      //We need $el to live in the DOM so we can verify remove.
      $body.append($el);
    });

    afterEach(function () {
      $el.remove();
    });

    it('should destroy the legend', function () {
      heatMapLegend.destroy();

      expect($body.find('svg.foo > g').length).toBe(0);
    });
  });

  /**
   * calls the heatMapLegend with the passed data.
   * @param {Array} data
   */
  function setup(data) {
    legendGroup
      .datum(data)
      .call(heatMapLegend);
  }
});