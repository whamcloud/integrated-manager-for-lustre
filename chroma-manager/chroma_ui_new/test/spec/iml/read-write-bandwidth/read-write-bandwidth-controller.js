describe('read write bandwidth controller', function () {
  'use strict';

  var $scope, DURATIONS, ReadWriteBandwidthStream, readWriteBandwidthStream;

  beforeEach(module('readWriteBandwidth'));

  mock.beforeEach(function createMock() {
    readWriteBandwidthStream = {
      setDuration: jasmine.createSpy('setDuration')
    };

    ReadWriteBandwidthStream = {
      setup: jasmine.createSpy('setup').andCallFake(function () {
        return readWriteBandwidthStream;
      })
    };

    return {
      name: 'ReadWriteBandwidthStream',
      value: ReadWriteBandwidthStream
    };
  });

  beforeEach(inject(function ($controller, $rootScope, _DURATIONS_) {
    DURATIONS = _DURATIONS_;
    $scope = $rootScope.$new();


    $controller('ReadWriteBandwidthCtrl', {
      $scope: $scope,
      ReadWriteBandwidthStream: ReadWriteBandwidthStream
    });
  }));

  it('should have no data to start', function () {
    expect($scope.readWriteBandwidth.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect(jasmine.objectContaining({
      size: 10,
      unit: DURATIONS.MINUTES
    }).jasmineMatches($scope.readWriteBandwidth))
      .toBe(true);
  });

  it('should setup the ReadWriteBandwidthStream', function () {
    expect(ReadWriteBandwidthStream.setup).toHaveBeenCalledOnceWith('readWriteBandwidth.data', $scope);
  });

  it('should set duration on the readWriteBandwidthStream', function () {
    expect(readWriteBandwidthStream.setDuration).toHaveBeenCalledOnceWith('minutes', 10);
  });

  it('should call readWriteBandwidthStream.setDuration on update', function () {
    $scope.readWriteBandwidth.onUpdate('hours', 20);

    expect(readWriteBandwidthStream.setDuration).toHaveBeenCalledWith('hours', 20);
  });

  describe('setting up the chart', function () {
    var chart, valueFormatter, captor;

    beforeEach(function () {
      captor = jasmine.captor();

      valueFormatter = jasmine.createSpy('valueFormatter');

      chart = {
        useInteractiveGuideline: jasmine.createSpy('useInteractiveGuideline'),
        isArea: jasmine.createSpy('isArea'),
        yAxis: {
          tickFormat: jasmine.createSpy('tickFormat')
        },
        xAxis: {
          showMaxMin: jasmine.createSpy('showMaxMin')
        }
      };

      $scope.readWriteBandwidth.options.setup(chart);
    });

    it('should set the chart to area mode', function () {
      expect(chart.isArea).toHaveBeenCalledOnceWith(true);
    });

    it('should hide max and min values on the x axis', function () {
      expect(chart.xAxis.showMaxMin).toHaveBeenCalledOnceWith(false);
    });

    describe('formatting ticks on the y axis', function () {
      var captor;

      beforeEach(function () {
        captor = jasmine.captor();

        expect(chart.yAxis.tickFormat).toHaveBeenCalledWith(captor.capture());
      });

      it('should format bytes', function () {
        expect(captor.value(300000)).toEqual('293 kB/s');
      });

      it('should leave 0 untouched', function () {
        expect(captor.value(0)).toEqual(0);
      });
    });
  });
});
