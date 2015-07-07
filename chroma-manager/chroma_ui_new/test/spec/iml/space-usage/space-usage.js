describe('space usage controller', function () {
  'use strict';

  function spaceUsageTransformer() {}

  beforeEach(module('space-usage', function ($provide) {
    $provide.value('streams', {
      targetStream: jasmine.createSpy('targetStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {spaceUsageTransformer: spaceUsageTransformer}));

  var DURATIONS, $scope, streams;

  beforeEach(inject(function (_DURATIONS_, $controller, $rootScope, _streams_) {
    DURATIONS = _DURATIONS_;
    streams = _streams_;
    $scope = $rootScope.$new();

    $controller('SpaceUsageCtrl', {
      $scope: $scope,
      streams: streams,
      spaceUsageTransformer: spaceUsageTransformer
    });
  }));

  it('should start with no data', function () {
    expect($scope.spaceUsage.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect($scope.spaceUsage).toContainObject({
      unit: DURATIONS.MINUTES,
      size: 10
    });
  });

  it('should create a target stream', function () {
    expect(streams.targetStream)
      .toHaveBeenCalledOnceWith('spaceUsage.data', $scope, 'httpGetMetrics', spaceUsageTransformer);
  });

  it('should start the target stream', function () {
    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      qs: {
        unit: DURATIONS.MINUTES,
        size: 10,
        metrics: 'kbytestotal,kbytesfree'
      }
    });
  });

  it('should restart the target stream', function () {
    $scope.spaceUsage.onUpdate(DURATIONS.HOURS, 5);

    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      qs: {
        unit: DURATIONS.HOURS,
        size: 5,
        metrics: 'kbytestotal,kbytesfree'
      }
    });
  });
});

describe('space usage transformer', function () {
  'use strict';

  beforeEach(module('space-usage', 'dataFixtures'));

  var spaceUsageTransformer, spaceUsageDataFixtures;

  beforeEach(inject(function (_spaceUsageTransformer_, _spaceUsageDataFixtures_) {
    spaceUsageTransformer = _spaceUsageTransformer_;
    spaceUsageDataFixtures = _spaceUsageDataFixtures_;
  }));

  it('should transform data as expected', function () {
    spaceUsageDataFixtures.forEach(function (item) {
      var resp = spaceUsageTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });
});
