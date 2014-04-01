describe('memory usage controller', function () {
  'use strict';

  function memoryUsageTransformer() {}

  beforeEach(module('memory-usage', function ($provide) {
    $provide.value('streams', {
      hostStream: jasmine.createSpy('hostStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {memoryUsageTransformer: memoryUsageTransformer}));

  var DURATIONS, $scope, streams;

  beforeEach(inject(function (_DURATIONS_, $controller, $rootScope, _streams_) {
    DURATIONS = _DURATIONS_;
    streams = _streams_;
    $scope = $rootScope.$new();

    $controller('MemoryUsageCtrl', {
      $scope: $scope,
      streams: streams,
      memoryUsageTransformer: memoryUsageTransformer
    });
  }));

  it('should start with no data', function () {
    expect($scope.memoryUsage.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect($scope.memoryUsage).toContainObject({
      unit: DURATIONS.MINUTES,
      size: 10
    });
  });

  it('should create a host stream', function () {
    expect(streams.hostStream)
      .toHaveBeenCalledOnceWith('memoryUsage.data', $scope, 'httpGetMetrics', memoryUsageTransformer);
  });

  it('should start the host stream', function () {
    expect(streams.hostStream.plan().start).toHaveBeenCalledOnceWith({
      qs : {
        unit : DURATIONS.MINUTES,
        size : 10,
        reduce_fn: 'average',
        metrics: 'mem_MemFree,mem_MemTotal,mem_SwapTotal,mem_SwapFree'
      }
    });
  });

  it('should restart the host stream', function () {
    $scope.memoryUsage.onUpdate(DURATIONS.HOURS, 5);

    expect(streams.hostStream.plan().start).toHaveBeenCalledOnceWith({
      qs: {
        unit: DURATIONS.HOURS,
        size: 5,
        reduce_fn: 'average',
        metrics: 'mem_MemFree,mem_MemTotal,mem_SwapTotal,mem_SwapFree'
      }
    });
  });
});

describe('memory usage transformer', function () {
  'use strict';

  beforeEach(module('memory-usage', 'dataFixtures'));

  var memoryUsageTransformer, memoryUsageDataFixtures;

  beforeEach(inject(function (_memoryUsageTransformer_, _memoryUsageDataFixtures_) {
    memoryUsageTransformer = _memoryUsageTransformer_;
    memoryUsageDataFixtures = _memoryUsageDataFixtures_;
  }));

  it('should transform data as expected', function () {
    memoryUsageDataFixtures.forEach(function (item) {
      var resp = memoryUsageTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });
});