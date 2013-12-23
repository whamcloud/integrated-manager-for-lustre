describe('heat map legend', function () {
  'use strict';

  var heatMapLegendFactory, d3, chartUtils, selection, eachSpy, linearScale, raf;

  beforeEach(module('charts'));

  mock.beforeEach('d3', 'chartUtils', 'raf');

  beforeEach(inject(function (_heatMapLegendFactory_, _d3_, _chartUtils_, _raf_) {
    heatMapLegendFactory = _heatMapLegendFactory_;
    raf = _raf_;
    d3 = _d3_;
    chartUtils = _chartUtils_;

    chartUtils.getBBox.andReturn(100);

    linearScale = Mock.spyInstance(d3.scale.linear.originalValue());

    d3.scale.linear.andReturn(linearScale);

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
      linearScale.interpolate.andReturn(linearScale);

      defaultConfig = {
        margin : { top : 5, right : 0, bottom : 5, left : 0 },
        width : 200,
        height : 30,
        formatter: _.identity,
        lowColor: '#fbeCeC',
        highColor: '#d9534f',
        rightAlign: true,
        legendScale: linearScale
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

        linearScale.domain.andReturn(linearScale);
        linearScale.range.andReturn(linearScale);

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
        expect(linearScale.domain).toHaveBeenCalledOnceWith([0, 100]);
      });

      it('should set the range to the config colors', function () {
        expect(linearScale.range).toHaveBeenCalledOnceWith([defaultConfig.lowColor, defaultConfig.highColor]);
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