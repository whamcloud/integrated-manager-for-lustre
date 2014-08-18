describe('heat map legend', function () {
  'use strict';

  var heatMapLegendFactory, d3, chartUtils, selection, eachSpy, raf;

  beforeEach(module('charts'));

  mock.beforeEach('d3', 'chartUtils', 'raf');

  beforeEach(inject(function (_heatMapLegendFactory_, _d3_, _chartUtils_, _raf_) {
    heatMapLegendFactory = _heatMapLegendFactory_;
    raf = _raf_;
    d3 = _d3_;
    chartUtils = _chartUtils_;

    chartUtils.getBBox.andReturn(100);

    d3.scale.linear = jasmine.createSpy('linear').andReturn({
      domain: jasmine.createSpy('domain'),
      range: jasmine.createSpy('range'),
      ticks: jasmine.createSpy('ticks')
    });
    d3.scale.linear.plan().domain.andReturn(d3.scale.linear.plan());
    d3.scale.linear.plan().range.andReturn(d3.scale.linear.plan());

    d3.range = jasmine.createSpy('range').andReturn([]);

    eachSpy = jasmine.createSpy('each');

    selection = {
      each: eachSpy
    };
  }));

  it('should return a factory function', function () {
    expect(heatMapLegendFactory).toEqual(jasmine.any(Function));
  });

  describe('working with the chart object', function () {
    var chart, defaultConfig;

    beforeEach(function () {
      defaultConfig = {
        margin : { top : 5, right : 0, bottom : 5, left : 0 },
        width : 200,
        height : 30,
        formatter: _.identity,
        colorScale: d3.scale.linear.plan(),
        rightAlign: true
      };

      chart = heatMapLegendFactory();

      //Simulate chartParamMixins
      Object.keys(defaultConfig).forEach(function (key) {
        chart[key] = jasmine.createSpy(key).andCallFake(function () {
          return defaultConfig[key];
        });
      });
    });

    it('should mixin the config', function () {
      expect(chartUtils.chartParamMixins).toHaveBeenCalledWith(defaultConfig, jasmine.any(Function));
    });

    it('should iterate over the selection', function () {
      chart(selection);

      expect(selection.each).toHaveBeenCalledOnce();
    });

    describe('working with data', function () {
      var context, mockSelection;

      beforeEach(function () {
        context = {};

        var chartSelection = d3.select.originalValue('svg'),
          enteringSelection = chartSelection.data([]);

        mockSelection = Mock.spyInstance(chartSelection);

        var mockEnteringSelection = Mock.spyInstance(enteringSelection);

        mockSelection.selectAll.andReturn(mockSelection);
        mockSelection.select.andReturn(mockSelection);
        mockSelection.append.andReturn(mockSelection);
        mockSelection.attr.andReturn(mockSelection);
        mockSelection.data.andReturn(mockEnteringSelection);

        mockEnteringSelection.enter.andReturn(mockSelection);
        mockEnteringSelection.select.andReturn(mockSelection);

        d3.select.andReturn(mockSelection);

        eachSpy.andCallFake(function (func) {
          func.call(context, [
            {
              values: [
                {z: 1},
                {z: 100}
              ]
            }
          ]);
        });

        d3.merge.andCallThrough();
        d3.extent.andCallThrough();

        chart(selection);
      });

      it('should grab a reference to the context', function () {
        expect(d3.select).toHaveBeenCalledOnceWith(context);
      });

      it('should set the domain to 0 and 100', function () {
        expect(d3.scale.linear.plan().domain).toHaveBeenCalledOnceWith([0, 100]);
      });

      it('should set the range to the config colors', function () {
        expect(d3.scale.linear.plan().range)
          .toHaveBeenCalledOnceWith(['#8ebad9', '#d6e2f3', '#fbb4b4', '#fb8181', '#ff6262']);
      });

      it('should set the min text', function () {
        expect(mockSelection.text).toHaveBeenCalledWith('Min: 1');
      });

      it('should set the max text', function () {
        expect(mockSelection.text).toHaveBeenCalledWith('Max: 100');
      });

      describe('destroy', function () {
        beforeEach(function () {
          chart.destroy();
        });

        it('should call remove on the container', function () {
          expect(mockSelection.remove).toHaveBeenCalledOnce();
        });


        it('should cancel any pending requestAnimationFrames', function () {
          expect(raf.cancelAnimationFrame).toHaveBeenCalledOnce();
        });
      });
    });
  });
});
