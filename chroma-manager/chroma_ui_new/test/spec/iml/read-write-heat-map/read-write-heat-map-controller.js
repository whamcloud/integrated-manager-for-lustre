describe('read write heat map controller', function () {
  'use strict';

  var $scope, ReadWriteHeatMapStream, readWriteHeatMapStream, chart, d3;

  beforeEach(module('readWriteHeatMap'));

  beforeEach(inject(function ($controller, $rootScope) {
    $scope = $rootScope.$new();

    readWriteHeatMapStream = {
      restart: jasmine.createSpy('restart'),
      startStreaming: jasmine.createSpy('startStreaming')
    };

    d3 = {
      event: {
        offsetX: 0,
        offsetY: 0
      }
    };

    ReadWriteHeatMapStream = {
      setup: jasmine.createSpy('setup').andReturn(readWriteHeatMapStream),
      TYPES: {
        READ: 'read',
        WRITE: 'write'
      }
    };

    $controller('ReadWriteHeatMapCtrl', {
      $scope: $scope,
      ReadWriteHeatMapStream: ReadWriteHeatMapStream,
      DURATIONS: {
        MINUTES: 'minutes'
      },
      d3: d3
    });

    chart = jasmine.createSpyObj('chart', ['options', 'onMouseOver', 'onMouseMove', 'onMouseOut', 'xAxis']);

    chart.xAxis.andReturn({
      showMaxMin: jasmine.createSpy('showMaxMin')
    });

  }));

  it('should start at 10 minutes', function () {
    expect($scope.readWriteHeatMap).toContainObject({
      unit: 'minutes',
      size: 10
    });
  });

  it('should start in read mode', function () {
    expect(readWriteHeatMapStream.type).toEqual('read');
  });

  it('should setup the stream to the right path and params', function () {
    var params = {
      qs: {
        unit: 'minutes',
        size: 10
      }
    };

    expect(ReadWriteHeatMapStream.setup).toHaveBeenCalledOnceWith('readWriteHeatMap.data', $scope, params);
  });

  it('should start streaming on setup', function () {
    expect(readWriteHeatMapStream.startStreaming).toHaveBeenCalledOnce();
  });

  it('should restart with new params on update', function () {
    $scope.readWriteHeatMap.onUpdate(1, 'second');

    expect(readWriteHeatMapStream.restart).toHaveBeenCalledOnceWith({ qs : { unit : 1, size : 'second' } });
  });

  it('should toggle the type', function () {
    $scope.readWriteHeatMap.toggle('write');
    expect(readWriteHeatMapStream.restart).toHaveBeenCalledOnceWith();
  });

  describe('chart setup', function () {
    beforeEach(function () {
      $scope.readWriteHeatMap.options.setup(chart);
    });

    it('should hide the y axis, set the margin, and provide a formatter', function () {
      expect(chart.options).toHaveBeenCalledOnceWith({
        showYAxis: false,
        formatter: jasmine.any(Function),
        margin: {left : 50}
      });
    });

    describe('mouse over', function () {
      var params;

      beforeEach(function () {
        params = {
          x: new Date('1/06/2013'),
          y: 'ost 0000',
          z: '2000000'
        };

        chart.onMouseOver.mostRecentCall.args[0](params);
      });

      it('should be visible', function () {
        expect($scope.readWriteHeatMap.isVisible).toBe(true);
      });

      it('should set the date', function () {
        expect($scope.readWriteHeatMap.date).toBe(params.x);
      });

      it('should set the x coordinate', function () {
        expect($scope.readWriteHeatMap.x).toBe(50);
      });

      it('should set the y coordinate', function () {
        expect($scope.readWriteHeatMap.y).toBe(50);
      });
    });

    it('should be visible on mouse move', function () {
      chart.onMouseMove.mostRecentCall.args[0]({
        x: new Date('')
      });

      expect($scope.readWriteHeatMap.isVisible).toBe(true);
    });

    it('should not be visible on mouse out', function () {
      chart.onMouseOut.mostRecentCall.args[0]();

      expect($scope.readWriteHeatMap.isVisible).toBe(false);
    });
  });
});