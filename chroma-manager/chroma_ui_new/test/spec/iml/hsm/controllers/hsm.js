describe('HSM controller', function () {
  'use strict';

  var $scope, $modal, DURATIONS, d3,
      HsmCdtStream, hsmCdtStream,
      HsmCopytoolStream, hsmCopytoolStream,
      HsmCopytoolOperationStream, hsmCopytoolOperationStream,
      FileSystemStream, fileSystemStream;

  beforeEach(module('hsm'));

  mock.beforeEach(
    function createCdtMock() {
      hsmCdtStream = {
        setDuration: jasmine.createSpy('setDuration')
      };

      HsmCdtStream = {
        setup: jasmine.createSpy('setup').andCallFake(function () {
          return hsmCdtStream;
        })
      };

      return {
        name: 'HsmCdtStream',
        value: HsmCdtStream
      };
    },
    function createCopytoolMock() {
      hsmCopytoolStream = {
        startStreaming: jasmine.createSpy('startStreaming')
      };

      HsmCopytoolStream = {
        setup: jasmine.createSpy('setup').andCallFake(function () {
          return hsmCopytoolStream;
        })
      };

      return {
        name: 'HsmCopytoolStream',
        value: HsmCopytoolStream
      };
    },
    function createCopytoolOperationMock() {
      hsmCopytoolOperationStream = {
        startStreaming: jasmine.createSpy('startStreaming')
      };

      HsmCopytoolOperationStream = {
        setup: jasmine.createSpy('setup').andCallFake(function () {
          return hsmCopytoolOperationStream;
        })
      };

      return {
        name: 'HsmCopytoolOperationStream',
        value: HsmCopytoolOperationStream
      };
    },
    function createFileSystemMock() {
      fileSystemStream = {
        startStreaming: jasmine.createSpy('startStreaming')
      };

      FileSystemStream = {
        setup: jasmine.createSpy('setup').andCallFake(function () {
          return fileSystemStream;
        })
      };

      return {
        name: 'FileSystemStream',
        value: FileSystemStream
      };
    },
    function createModalMock() {
      $modal = {};

      return {
        name: '$modal',
        value: $modal
      };
    }
  );

  beforeEach(inject(function ($controller, _$modal_, $rootScope, _DURATIONS_, _d3_) {
    $modal = _$modal_;
    d3 = _d3_;
    DURATIONS = _DURATIONS_;
    $scope = $rootScope.$new();

    $controller('HsmCtrl', {
      $scope: $scope,
      HsmCdtStream: HsmCdtStream
    });
  }));

  it('should have no data to start', function () {
    expect($scope.hsm.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect(jasmine.objectContaining({
      size: 10,
      unit: DURATIONS.MINUTES
    }).jasmineMatches($scope.hsm))
      .toBe(true);
  });

  it('should setup the HsmCdtStream', function () {
    expect(HsmCdtStream.setup).toHaveBeenCalledOnceWith('hsm.data', $scope);
  });

  it('should set duration on the HsmCdtStream', function () {
    expect(hsmCdtStream.setDuration).toHaveBeenCalledOnceWith('minutes', 10);
  });

  it('should call HsmCdtStream.setDuration on update', function () {
    $scope.hsm.onUpdate('hours', 20);

    expect(hsmCdtStream.setDuration).toHaveBeenCalledWith('hours', 20);
  });

  it('should setup the HsmCopytoolStream', function () {
    expect(HsmCopytoolStream.setup).toHaveBeenCalledOnceWith('hsm.copytools', $scope);
  });

  it('should start the HsmCopytoolStream', function () {
    expect(hsmCopytoolStream.startStreaming).toHaveBeenCalledOnce();
  });

  it('should setup the HsmCopytoolOperationStream', function () {
    expect(HsmCopytoolOperationStream.setup).toHaveBeenCalledOnceWith('hsm.copytoolOperations', $scope);
  });

  it('should start the HsmCopytoolOperationStream', function () {
    expect(hsmCopytoolOperationStream.startStreaming).toHaveBeenCalledOnce();
  });

  it('should setup the FileSystemStream', function () {
    expect(FileSystemStream.setup).toHaveBeenCalledOnceWith('hsm.fileSystems', $scope);
  });

  it('should start the FileSystemStream', function () {
    expect(fileSystemStream.startStreaming).toHaveBeenCalledOnce();
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

      $scope.hsm.options.setup(chart, d3);
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
      expect(chart.color).toHaveBeenCalledOnceWith(['#F3B600', '#A3B600', '#0067B4']);
    });

    describe('formatting ticks on the y axis', function () {
      var captor;

      beforeEach(function () {
        captor = jasmine.captor();

        expect(chart.yAxis.tickFormat).toHaveBeenCalledWith(captor.capture());
      });

      it('should format y axis ticks as integers, ignoring non-ints', function () {
        expect(captor.value(1)).toEqual('1');
        expect(captor.value(1.5)).toEqual('');
      });
    });
  });
});
