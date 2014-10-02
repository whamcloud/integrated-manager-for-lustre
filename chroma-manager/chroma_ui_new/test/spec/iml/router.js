describe('The router', function () {
  'use strict';

  var $rootScope, $routeSegmentProvider, GROUPS, $q;

  beforeEach(function () {
    $routeSegmentProvider = {
      options: {},
      $get: function () {},
      segment: jasmine.createSpy('$routeSegmentProvider.segment').andCallFake(routeSegementProvider),
      when: jasmine.createSpy('$routeSegmentProvider.when').andCallFake(routeSegementProvider),
      within: jasmine.createSpy('$routeSegmentProvider.within').andCallFake(routeSegementProvider)
    };

    function routeSegementProvider () {
      return $routeSegmentProvider;
    }

    angular.module('route-segment', []).provider({
      $routeSegment: $routeSegmentProvider
    });
  });

  beforeEach(module('imlRoutes', 'auth'));

  beforeEach(inject(function (_GROUPS_, _$rootScope_, _$q_) {
    GROUPS = _GROUPS_;
    $rootScope = _$rootScope_;
    $q = _$q_;
  }));

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

  describe('authorization', function () {

    it('should load pages that are access restricted using the hasAccess resolve', function () {
      expect($routeSegmentProvider.segment)
        .toHaveBeenCalledOnceWith('server', {
          controller: 'ServerCtrl',
          templateUrl: 'iml/server/assets/html/server.html',
          resolve: {
            jobMonitorSpark: jasmine.any(Array),
            alertMonitorSpark: jasmine.any(Array),
            hasAccess: ['hasAccess', jasmine.any(Function)]
          },
          access: GROUPS.FS_ADMINS,
          untilResolved: {
            templateUrl: 'common/loading/assets/html/loading.html'
          }});
    });

    it('should add the segmentAuthenticated property to the result of within', function () {
      expect($routeSegmentProvider.segmentAuthenticated).not.toBeNull();
    });

    ['jobMonitorSpark', 'alertMonitorSpark'].forEach(function testSparks (sparkType) {
      describe(sparkType, function () {
        var monitorSpark, monitor, spark;

        beforeEach(function () {
          spark = {
            onceValueThen: jasmine.createSpy('onceValueThen').andReturn($q.when())
          };
          monitor = jasmine.createSpy('monitor').andReturn(spark);

          var segment = $routeSegmentProvider.segment.calls.filter(function findServerSegment (segment) {
            return segment.args[0] === 'server' && segment.args[1].resolve != null;
          });

          monitorSpark = segment[0].args[1].resolve[sparkType];
        });

        it('should return a spark', function () {
          var expectedSpark = monitorSpark[monitorSpark.length - 1](monitor);

          expectedSpark.then(function hasSpark (resp) {
            expect(resp).toBe(spark);
          });

          $rootScope.$apply();
        });
      });
    });
  });
});

describe('hasAccess service', function () {
  'use strict';
  var hasAccess, result, params, $rootScope, authorization, $location, $q;

  beforeEach(module('imlRoutes', function setupDependencies ($provide) {
    authorization = {
      groupAllowed: jasmine.createSpy('groupAllowed').andReturn(true)
    };

    $provide.value('authorization', authorization);

    $location = jasmine.createSpyObj('$location', ['path']);

    $provide.value('$location', $location);

    params = {
      access: 'superusers'
    };

  }));

  beforeEach(inject(function (_hasAccess_, _$q_, _$rootScope_) {
    hasAccess = _hasAccess_;
    $q = _$q_;
    $rootScope = _$rootScope_;
  }));

  describe('hasAccess is true', function () {
    beforeEach(function () {
      result = hasAccess(params);
    });

    it('should call the groupAllowed method in the authorization service with the specified access',
      function () {
        expect(authorization.groupAllowed).toHaveBeenCalledWith(params.access);
      });

    it('should resolve', function () {
      var resolve = jasmine.createSpy('resolve');
      result.then(resolve);

      $rootScope.$apply();

      expect(resolve).toHaveBeenCalledOnce();
    });

    it('should not contain a resolveFailed property on the params', function () {
      expect(params.resolveFailed).toBeUndefined();
    });
  });

  describe('hasAccess is false', function () {
    beforeEach(function () {
      authorization.groupAllowed.andReturn(false);
    });

    var noAccessProviders = [
      {
        readEnabled: true,
        resolveFailed: {
          controller: 'BaseDashboardCtrl',
          templateUrl: 'iml/dashboard/assets/html/base-dashboard.html'
        },
        targetLocation: '/'
      },
      {
        readEnabled: false,
        resolveFailed: {
          controller: 'LoginCtrl',
          controllerAs: 'login',
          templateUrl: 'common/login/assets/html/login.html'
        },
        targetLocation: '/login'
      }
    ];

    noAccessProviders.forEach(function testNoAccess (provider) {
      describe('read enabled is ' + provider.readEnabled, function () {
        beforeEach(function () {
          authorization.readEnabled = provider.readEnabled;
          result = hasAccess(params);
        });

        it('should have resolveFailed property on params', function () {
          expect(params.resolveFailed).toEqual(provider.resolveFailed);
        });

        it('should call the location service with ' + provider.targetLocation, function () {
          expect($location.path).toHaveBeenCalledWith(provider.targetLocation);
        });

        it('should reject', function () {
          var reject = jasmine.createSpy('reject');
          result.catch(reject);

          $rootScope.$apply();

          expect(reject).toHaveBeenCalledOnce();
        });
      });
    });
  });
});
