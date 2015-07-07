describe('Mdo controller', function () {
  'use strict';

  var $scope, DURATIONS, MdoStream, mdoStream, d3;

  beforeEach(module('mdo', 'd3'));

  mock.beforeEach('BASE', function createMock() {
    mdoStream = {
      setDuration: jasmine.createSpy('setDuration')
    };

    MdoStream = {
      setup: jasmine.createSpy('setup').andCallFake(function () {
        return mdoStream;
      })
    };

    return {
      name: 'MdoStream',
      value: MdoStream
    };
  });

  beforeEach(inject(function ($controller, $rootScope, _DURATIONS_, _d3_) {
    d3 = _d3_;
    DURATIONS = _DURATIONS_;
    $scope = $rootScope.$new();


    $controller('MdoCtrl', {
      $scope: $scope,
      MdoStream: MdoStream
    });
  }));

  it('should have no data to start', function () {
    expect($scope.mdo.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect(jasmine.objectContaining({
      size: 10,
      unit: DURATIONS.MINUTES
    }).jasmineMatches($scope.mdo))
      .toBe(true);
  });

  it('should setup the MdoStream', function () {
    expect(MdoStream.setup).toHaveBeenCalledOnceWith('mdo.data', $scope, {});
  });

  it('should set duration on the mdoStream', function () {
    expect(mdoStream.setDuration).toHaveBeenCalledOnceWith('minutes', 10);
  });

  it('should call mdoStream.setDuration on update', function () {
    $scope.mdo.onUpdate('hours', 20);

    expect(mdoStream.setDuration).toHaveBeenCalledWith('hours', 20);
  });

  describe('setting up the chart', function () {
    var chart, valueFormatter, captor;

    beforeEach(function () {
      captor = jasmine.captor();

      valueFormatter = jasmine.createSpy('valueFormatter');

      chart = {
        stacked: {
          style: jasmine.createSpy('style')
        },
        useInteractiveGuideline: jasmine.createSpy('useInteractiveGuideline'),
        interactiveLayer: {
          tooltip: {
            valueFormatter: valueFormatter
          }
        },
        yAxis: {
          tickFormat: jasmine.createSpy('tickFormat')
        },
        forceY: jasmine.createSpy('forceY'),
        xAxis: {
          showMaxMin: jasmine.createSpy('showMaxMin')
        }
      };

      $scope.mdo.options.setup(chart, d3);

      expect(valueFormatter).toHaveBeenCalledWith(captor.capture());
    });

    it('should use the interactive guideline', function () {
      expect(chart.useInteractiveGuideline).toHaveBeenCalledOnceWith(true);
    });

    it('should force the y axis', function () {
      expect(chart.forceY).toHaveBeenCalledOnceWith([0, 1]);
    });

    it('should hide max and min values on the x axis', function () {
      expect(chart.xAxis.showMaxMin).toHaveBeenCalledOnceWith(false);
    });

    it('should format for the expanded style', function () {
      chart.stacked.style.andReturn('expand');

      expect(captor.value(0.44)).toEqual('44.0%');
    });

    it('should round for the non-expanded styles', function () {
      chart.stacked.style.andReturn('stacked');

      expect(captor.value(10.5)).toEqual(11);
    });

    describe('formatting ticks on the y axis', function () {
      var captor;

      beforeEach(function () {
        captor = jasmine.captor();

        expect(chart.yAxis.tickFormat).toHaveBeenCalledWith(captor.capture());
      });


      it('should format y axis ticks to thousands', function () {
        expect(captor.value(5000)).toEqual('5.0K');
      });

      it('should round values', function () {
        expect(captor.value(5350)).toEqual('5.4K');
      });

      it('should leave values less than 1000 untouched', function () {
        expect(captor.value(999)).toEqual(999);
      });
    });
  });
});
