describe('The job stats controller', function () {
  'use strict';

  var target, jobStatsCtrl;

  beforeEach(module('jobStats'));

  beforeEach(inject(function ($controller) {
    target = {
      name: 'foo'
    };

    var $routeSegment = {
      $routeParams: {
        startDate: '2014-01-30T22:08:11.423Z',
        endDate: '2014-01-30T22:08:41.220Z'
      }
    };

    jobStatsCtrl = $controller('JobStatsCtrl', {
      target: target,
      $routeSegment: $routeSegment,
      metrics: {
        read_bytes: [],
        write_bytes: [],
        read_iops: [],
        write_iops: []
      }
    });
  }));

  it('should expose the target name on the scope', function () {
    expect(jobStatsCtrl.name).toEqual(target.name);
  });

  it('should expose the start and end params on the scope', function () {
    expect(jobStatsCtrl).toContainObject({
      startDate: '2014-01-30T22:08:11.423Z',
      endDate: '2014-01-30T22:08:41.220Z'
    });
  });

  it('should expose metrics on the scope', function () {
    expect(jobStatsCtrl).toContainObject({
      read_bytes: [],
      write_bytes: [],
      read_iops: [],
      write_iops: []
    });
  });
});
