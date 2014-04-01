describe('file usage controller', function () {
  'use strict';

  function fileUsageTransformer () {}

  beforeEach(module('file-usage', function ($provide) {
    $provide.value('streams', {
      targetStream: jasmine.createSpy('targetStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {fileUsageTransformer: fileUsageTransformer}));

  var DURATIONS, $scope, streams;

  beforeEach(inject(function (_DURATIONS_, $controller, $rootScope, _streams_) {
    DURATIONS = _DURATIONS_;
    streams = _streams_;
    $scope = $rootScope.$new();

    $controller('FileUsageCtrl', {
      $scope: $scope,
      streams: streams,
      fileUsageTransformer: fileUsageTransformer
    });
  }));

  it('should start with no data', function () {
    expect($scope.fileUsage.data).toEqual([]);
  });

  it('should default to 10 minutes', function () {
    expect($scope.fileUsage).toContainObject({
      unit: DURATIONS.MINUTES,
      size: 10
    });
  });

  it('should create a target stream', function () {
    expect(streams.targetStream)
      .toHaveBeenCalledOnceWith('fileUsage.data', $scope, 'httpGetMetrics', fileUsageTransformer);
  });

  it('should start the target stream', function () {
    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      qs : {
        unit : DURATIONS.MINUTES,
        size : 10,
        metrics: 'filestotal,filesfree'
      }
    });
  });

  it('should restart the target stream', function () {
    $scope.fileUsage.onUpdate(DURATIONS.HOURS, 5);

    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      qs: {
        unit: DURATIONS.HOURS,
        size: 5,
        metrics: 'filestotal,filesfree'
      }
    });
  });
});

describe('file usage transformer', function () {
  'use strict';

  beforeEach(module('file-usage', 'dataFixtures'));

  var fileUsageTransformer, fileUsageDataFixtures;

  beforeEach(inject(function (_fileUsageTransformer_, _fileUsageDataFixtures_) {
    fileUsageTransformer = _fileUsageTransformer_;
    fileUsageDataFixtures = _fileUsageDataFixtures_;
  }));

  it('should transform data as expected', function () {
    fileUsageDataFixtures.forEach(function (item) {
      var resp = fileUsageTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });
});