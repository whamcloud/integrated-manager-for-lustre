//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


angular.module('imlRoutes', ['ngRoute', 'route-segment', 'view-segment', 'auth'])
  .config(['$routeSegmentProvider', 'GROUPS', function ($routeSegmentProvider, GROUPS) {
    'use strict';

    $routeSegmentProvider.segmentAuthenticated = segmentAuthenticated;

    /**
     * Extends the params.resolve property with the hasAccess function so that it will be executed
     * upon being resolved.
     * @param {String} name
     * @param {Object} params
     * @returns {Object}
     */
    function segmentAuthenticated (name, params) {
      params.resolve = params.resolve || {};

      params.resolve.hasAccess = ['hasAccess', function checkIfHasAccess (hasAccess) {
        hasAccess(params);
      }];

      /* jshint validthis:true */
      return this.segment(name, params);
    }

    var within = $routeSegmentProvider.within;

    $routeSegmentProvider.within = newWithin;

    /**
     * Overrides the within method in the routeSegmentProvider such that it appends a segmentAuthenticated
     * property onto the result.
     * @param {String} childName
     * @returns {Object}
     */
    function newWithin (childName) {
      var result = within(childName);
      result.segmentAuthenticated = segmentAuthenticated;

      return result;
    }

    $routeSegmentProvider.options.autoLoadTemplates = true;
    $routeSegmentProvider.options.strictMode = true;

    $routeSegmentProvider.when('/login/', 'login').segment('login', {
      controller: 'LoginCtrl',
      controllerAs: 'login',
      templateUrl: 'common/login/assets/html/login.html'
    });

    $routeSegmentProvider.segment('app', {
      controller: 'AppCtrl',
      controllerAs: 'app',
      templateUrl: 'iml/app/assets/html/app.html'
    });

    $routeSegmentProvider.when('/', 'app.dashboard.base')
      .when('/dashboard', 'app.dashboard.base')
      .when('/dashboard/fs/:fsId', 'app.dashboard.fs')
      .when('/dashboard/fs/:fsId/OST/:ostId', 'app.dashboard.ost')
      .when('/dashboard/fs/:fsId/MDT/:mdtId', 'app.dashboard.mdt')
      .when('/dashboard/server/:serverId', 'app.dashboard.server')
      .when('/dashboard/server/:serverId/OST/:ostId', 'app.dashboard.ost')
      .when('/dashboard/server/:serverId/MDT/:mdtId', 'app.dashboard.mdt');

    $routeSegmentProvider.within('app')
      .segment('dashboard', {
        templateUrl: 'iml/dashboard/assets/html/dashboard.html'
      })
      .within()
      .segment('base', {
        controller: 'BaseDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/base-dashboard.html'
      })
      .segment('fs', {
        controller: 'FsDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/fs-dashboard.html',
        dependencies: ['fsId']
      })
      .segment('server', {
        controller: 'ServerDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/server-dashboard.html',
        dependencies: ['serverId']
      })
      .segment('ost', {
        controller: 'OstDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/ost-dashboard.html',
        dependencies: ['fsId', 'serverId', 'ostId']
      })
      .segment('mdt', {
        controller: 'MdtDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/mdt-dashboard.html',
        dependencies: ['fsId', 'serverId', 'mdtId']
      });

    $routeSegmentProvider
      .when('/about', 'app.about')
      .when('/configure/hsm', 'app.hsm')
      .when('/configure/server', 'app.server');

    $routeSegmentProvider.within('app')
      .segment('about', {
        controller: 'AboutCtrl',
        controllerAs: 'about',
        templateUrl: 'iml/about/assets/html/about.html'
      })
      .segmentAuthenticated('hsm', {
        controller: 'HsmCtrl',
        templateUrl: 'iml/hsm/assets/html/hsm.html',
        access: GROUPS.FS_ADMINS,
        untilResolved: {
          templateUrl: 'common/loading/assets/html/loading.html'
        }
      }).segmentAuthenticated('server', {
        controller: 'ServerCtrl',
        templateUrl: 'iml/server/assets/html/server.html',
        resolve: {
          jobMonitorSpark: ['jobMonitor', function jobMonitorSpark (jobMonitor) {
            var spark = jobMonitor();

            return spark.onceValueThen('data')
              .then(function onData () {
                return spark;
              });
          }],
          alertMonitorSpark: ['alertMonitor', function alertMonitorSpark (alertMonitor) {
            var spark = alertMonitor();

            return spark.onceValueThen('data')
              .then(function onData () {
                return spark;
              });
          }]
        },
        access: GROUPS.FS_ADMINS,
        untilResolved: {
          templateUrl: 'common/loading/assets/html/loading.html'
        }
      });

    $routeSegmentProvider.when('/dashboard/jobstats/:id/:startDate/:endDate', 'app.jobstats');

    $routeSegmentProvider.within('app').segment('jobstats', {
      controller: 'JobStatsCtrl',
      controllerAs: 'jobStats',
      templateUrl: 'iml/job-stats/assets/html/job-stats.html',
      resolve: {
        target: ['$route', 'TargetModel', function resolveTarget ($route, TargetModel) {
          return TargetModel.get({
            id: $route.current.params.id
          }).$promise;
        }],
        metrics: ['$q', '$route', 'TargetMetricModel', function resolveMetrics ($q, $route, TargetMetricModel) {
          var commonParams = {
            begin: $route.current.params.startDate,
            end: $route.current.params.endDate,
            job: 'id',
            id: $route.current.params.id
          };
          var metrics = ['read_bytes', 'write_bytes', 'read_iops', 'write_iops'];

          var promises = metrics.reduce(function reducer (out, metric) {

            var params = _.extend({}, commonParams, {metrics: metric});

            out[metric] = TargetMetricModel.getJobAverage(params);

            return out;
          }, {});

          return $q.all(promises);
        }]
      },
      untilResolved: {
        templateUrl: 'common/loading/assets/html/loading.html'
      }
    });
  }]);

angular.module('imlRoutes').factory('hasAccess', ['$route', 'authorization', '$location', '$rootScope', '$q',
  function ($route, authorization, $location, $rootScope, $q) {
    'use strict';

    /**
     * Determines if the user has access to the specified route given their access (on the params object). If they
     * have access, it will resolve immediately. If, however, they do not have access, it will do one of two actions:
     * 1. If readEnabled is true it will route to the dashboard
     * 2. If readEnabled is false it will route to the login screen
     * @param {Object} params The params associated with the route
     * @returns {$q.promise}
     */
    return function hasAccess (params) {
      var authenticated = authorization.groupAllowed(params.access);

      if (authenticated)
        return $q.when();

      var targetLocation = {
        controller: 'BaseDashboardCtrl',
        templateUrl: 'iml/dashboard/assets/html/base-dashboard.html'
      };

      var targetPath = '/';

      if (!authorization.readEnabled) {
        targetLocation = {
          controller: 'LoginCtrl',
          controllerAs: 'login',
          templateUrl: 'common/login/assets/html/login.html'
        };
        targetPath = '/login';
      }

      // Handle case where not authenticated
      params.resolveFailed = targetLocation;
      $location.path(targetPath);

      return $q.reject();
    };
  }]);
