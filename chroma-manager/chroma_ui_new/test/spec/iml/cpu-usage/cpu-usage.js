describe('cpu usage controller', function () {
  'use strict';

  function cpuUsageTransformer () {}

  beforeEach(module('cpu-usage', function ($provide) {
    $provide.value('streams', {
      hostStream: jasmine.createSpy('hostStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {cpuUsageTransformer: cpuUsageTransformer}));

  var DURATIONS, $scope, streams;

  beforeEach(inject(function (_DURATIONS_, $controller, $rootScope, _streams_) {
    DURATIONS = _DURATIONS_;
    streams = _streams_;
    $scope = $rootScope.$new();

    $controller('CpuUsageCtrl', {
      $scope: $scope,
      streams: streams,
      cpuUsageTransformer: cpuUsageTransformer
    });
  }));

  it('should start with no data', function () {
    expect($scope.cpuUsage.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect($scope.cpuUsage).toContainObject({
      unit: DURATIONS.MINUTES,
      size: 10
    });
  });

  it('should create a host stream', function () {
    expect(streams.hostStream)
      .toHaveBeenCalledOnceWith('cpuUsage.data', $scope, 'httpGetMetrics', cpuUsageTransformer);
  });

  it('should start the host stream', function () {
    expect(streams.hostStream.plan().start).toHaveBeenCalledOnceWith({
      qs : {
        unit : DURATIONS.MINUTES,
        size : 10,
        reduce_fn : 'average',
        metrics : 'cpu_total,cpu_user,cpu_system,cpu_iowait'
      }
    });
  });

  it('should restart the host stream', function () {
    $scope.cpuUsage.onUpdate(DURATIONS.HOURS, 5);

    expect(streams.hostStream.plan().start).toHaveBeenCalledOnceWith({
      qs: {
        unit: DURATIONS.HOURS,
        size: 5,
        reduce_fn : 'average',
        metrics : 'cpu_total,cpu_user,cpu_system,cpu_iowait'
      }
    });
  });
});

describe('cpu usage transformer', function () {
  'use strict';

  beforeEach(module('cpu-usage', 'dataFixtures'));

  var cpuUsageTransformer, cpuUsageDataFixtures;

  beforeEach(inject(function (_cpuUsageTransformer_, _cpuUsageDataFixtures_) {
    cpuUsageTransformer = _cpuUsageTransformer_;
    cpuUsageDataFixtures = _cpuUsageDataFixtures_;
  }));

  it('should transform data as expected', function () {
    cpuUsageDataFixtures.forEach(function (item) {
      var resp = cpuUsageTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });
});