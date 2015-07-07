describe('The target metric model', function () {
  'use strict';

  var TargetMetricModel, deferred;

  mock.factory(function modelFactory($q) {
    deferred = $q.defer();

    var baseModel = Object.create({
      query: jasmine.createSpy('baseModel.query').andReturn({
        $promise: deferred.promise
      })
    });

    return jasmine.createSpy('modelFactory').andReturn(baseModel);
  });

  beforeEach(module('jobStats'));

  mock.beforeEach('modelFactory');

  beforeEach(inject(function (_TargetMetricModel_) {
    TargetMetricModel = _TargetMetricModel_;
  }));

  it('should average the data', function () {
    var input = [
      {data: {'cp.0': 1, 'dd.0': 6}, ts: '2014-01-30T19:40:50+00:00'},
      {data: {'cp.0': 3, 'dd.0': 2}, ts: '2014-01-30T19:41:00+00:00'}
    ];

    deferred.resolve(input);

    TargetMetricModel.getJobAverage({}).then(function (output) {
      expect(output).toEqual([
        {name: 'cp.0', average: 2},
        {name: 'dd.0', average: 4}
      ]);
    });
  });

  it('should return [] when no data', function () {
    deferred.resolve([]);

    TargetMetricModel.getJobAverage({}).then(function (output) {
      expect(output).toEqual([]);
    });
  });
});
