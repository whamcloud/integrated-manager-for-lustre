describe('ObjectStorageServers controller', function () {
  'use strict';

  var $scope, DURATIONS, MdsStream, mdsStream, d3;

  beforeEach(module('objectStorageServers'));

  mock.beforeEach(function createMock() {
    mdsStream = {
      setDuration: jasmine.createSpy('setDuration')
    };

    MdsStream = {
      setup: jasmine.createSpy('setup').andCallFake(function () {
        return mdsStream;
      })
    };

    return {
      name: 'MdsStream',
      value: MdsStream
    };
  });

  beforeEach(inject(function ($controller, $rootScope, _DURATIONS_, _d3_) {
    d3 = _d3_;
    DURATIONS = _DURATIONS_;
    $scope = $rootScope.$new();

    $controller('ObjectStorageServersCtrl', {
      $scope: $scope,
      MdsStream: MdsStream
    });
  }));

  it('should have no data to start', function () {
    expect($scope.objectStorageServers.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect(jasmine.objectContaining({
      size: 10,
      unit: DURATIONS.MINUTES
    }).jasmineMatches($scope.objectStorageServers))
      .toBe(true);
  });

  it('should setup the MdsStream', function () {
    expect(MdsStream.setup).toHaveBeenCalledOnceWith('objectStorageServers.data', $scope, {
      qs: {
        role : 'OSS'
      }
    });
  });

  it('should set duration on the mdsStream', function () {
    expect(mdsStream.setDuration).toHaveBeenCalledOnceWith('minutes', 10);
  });

  it('should call mdsStream.setDuration on update', function () {
    $scope.objectStorageServers.onUpdate('hours', 20);

    expect(mdsStream.setDuration).toHaveBeenCalledWith('hours', 20);
  });

  describe('setting up the chart', function () {
    var chart;

    beforeEach(function () {
      chart = {
        useInteractiveGuideline: jasmine.createSpy('useInteractiveGuideline'),
        yAxis: {
          tickFormat: jasmine.createSpy('tickFormat')
        },
        forceY: jasmine.createSpy('forceY'),
        xAxis: {
          showMaxMin: jasmine.createSpy('showMaxMin')
        },
        color: jasmine.createSpy('color')
      };

      $scope.objectStorageServers.options.setup(chart, d3);
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

    it('should set the expected colors', function () {
      expect(chart.color).toHaveBeenCalledOnceWith(['#F3B600', '#0067B4']);
    });

    describe('formatting ticks on the y axis', function () {
      var captor;

      beforeEach(function () {
        captor = jasmine.captor();

        expect(chart.yAxis.tickFormat).toHaveBeenCalledWith(captor.capture());
      });


      it('should format y axis ticks with percentage', function () {
        expect(captor.value(0.51)).toEqual('51.0%');
      });
    });
  });
});