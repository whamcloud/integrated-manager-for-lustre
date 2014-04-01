describe('Ost Balance controller', function () {
  'use strict';

  var $scope, DURATIONS, OstBalanceStream, ostBalanceStream, d3;

  beforeEach(module('ostBalance', 'd3'));

  mock.beforeEach('BASE');

  beforeEach(inject(function ($controller, $rootScope, _DURATIONS_, _d3_) {
    d3 = _d3_;
    DURATIONS = _DURATIONS_;
    $scope = $rootScope.$new();

    ostBalanceStream = {
      setPercentage: jasmine.createSpy('setPercentage'),
      startStreaming: jasmine.createSpy('startStreaming')
    };

    OstBalanceStream = {
      setup: jasmine.createSpy('setup').andReturn(ostBalanceStream)
    };

    $controller('OstBalanceCtrl', {
      $scope: $scope,
      OstBalanceStream: OstBalanceStream
    });
  }));

  it('should have no data to start', function () {
    expect($scope.ostBalance.data).toEqual([]);
  });

  it('should set a new percentage', function () {
    $scope.ostBalance.onUpdate(25);

    expect(ostBalanceStream.setPercentage).toHaveBeenCalledWith(25);
  });

  it('should setup the stream', function () {
    expect(OstBalanceStream.setup).toHaveBeenCalledWith('ostBalance.data', $scope, {});
  });

  describe('setting up the chart', function () {
    var chart, captor;

    beforeEach(function () {
      captor = jasmine.captor();

      chart = {
        yAxis: {
          tickFormat: jasmine.createSpy('tickFormat')
        },
        showXAxis: jasmine.createSpy('showXAxis'),
        rotateLabels: jasmine.createSpy('rotateLabels'),
        stacked: jasmine.createSpy('stacked'),
        forceY: jasmine.createSpy('forceY'),
        tooltip: jasmine.createSpy('tooltip')
      };

      $scope.ostBalance.options.setup(chart, d3);
    });

    it('should force the y axis', function () {
      expect(chart.forceY).toHaveBeenCalledOnceWith([0, 1]);
    });

    it('should start in stacked mode', function () {
      expect(chart.stacked).toHaveBeenCalledOnceWith(true);
    });

    it('should hide the x axis', function () {
      expect(chart.showXAxis).toHaveBeenCalledOnceWith(false);
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