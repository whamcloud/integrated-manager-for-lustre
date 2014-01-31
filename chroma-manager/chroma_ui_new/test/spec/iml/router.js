describe('The router', function () {
  'use strict';

  var $routeSegmentProvider;

  beforeEach(function () {
    $routeSegmentProvider = {
      options: {},
      $get : function() {},
      segment: jasmine.createSpy('$routeSegmentProvider.segment'),
      when: jasmine.createSpy('$routeSegmentProvider.when').andCallFake(function () {
        return $routeSegmentProvider;
      }),
      within: jasmine.createSpy('$routeSegmentProvider.within').andCallFake(function () {
        return $routeSegmentProvider;
      })
    };

    angular.module('route-segment', []).provider({
      $routeSegment: $routeSegmentProvider
    });
  });

  beforeEach(module('imlRoutes'));

  beforeEach(inject(function () {}));

  describe('when setting up job stats', function () {
    var $q, TargetModel, TargetMetricModel, $route, deferred;

    beforeEach(inject(function (_$q_) {
      $q = _$q_;

      deferred = $q.defer();

      $route = {
        current: {
          params: {
            id: 1
          }
        }
      };

      TargetModel = {
        get: jasmine.createSpy('TargetModel.get').andReturn({
          $promise: deferred.promise
        })
      };

      TargetMetricModel = {
        getJobAverage: jasmine.createSpy('TargetMetricModel.get').andReturn({
          $promise: deferred.promise
        })
      };
    }));

    it('should setup routing', function () {
      expect($routeSegmentProvider.when)
        .toHaveBeenCalledOnceWith('/dashboard/jobstats/:id/:startDate/:endDate', 'app.jobstats');
    });

    it('should setup the segment', function () {
      expect($routeSegmentProvider.segment).toHaveBeenCalledOnceWith('jobstats', {
        controller: 'JobStatsCtrl',
        controllerAs: 'jobStats',
        templateUrl: 'iml/job-stats/assets/html/job-stats.html',
        resolve: {
          target: jasmine.any(Array),
          metrics: jasmine.any(Array)
        },
        untilResolved: {
          templateUrl: 'common/loading/assets/html/loading.html'
        }
      });
    });

    it('should get the target', function () {
      var resolveTarget = $routeSegmentProvider.segment.mostRecentCall.args[1].resolve.target[2];

      resolveTarget($route, TargetModel);

      expect(TargetModel.get).toHaveBeenCalledOnceWith({ id: 1 });
    });

    describe('metrics', function () {
      beforeEach(function () {
        var resolveMetrics = $routeSegmentProvider.segment.mostRecentCall.args[1].resolve.metrics[3];

        $route = {
          current: {
            params: {
              startDate: '2014-01-30T22:08:11.423Z',
              endDate: '2014-01-30T22:08:41.220Z',
              id: 1
            }
          }
        };

        resolveMetrics($q, $route, TargetMetricModel);
      });

      var metrics = ['read_bytes', 'write_bytes', 'read_iops', 'write_iops'];

      metrics.forEach(function (metric) {
        it('should get the target metric ' + metric, function () {
          expect(TargetMetricModel.getJobAverage).toHaveBeenCalledOnceWith({
            begin: '2014-01-30T22:08:11.423Z',
            end: '2014-01-30T22:08:41.220Z',
            job: 'id',
            id: 1,
            metrics: metric
          });
        });
      });
    });
  });
});