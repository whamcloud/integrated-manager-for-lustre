//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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


(function () {
  'use strict';

  var globalConfig = {
    formatBaseUrl: angular.identity,
    defaultActions: {
      get: {method: 'GET'},
      getCollection: {method: 'GET', isArray: true},
      post: {method: 'POST'},
      put: {method: 'PUT'},
      patch: {method: 'PATCH'},
      del: {method: 'DELETE'}
    },
    defaultResponseInterceptor: function (resp) {
      return resp.resource;
    }
  };

  function ResourcefulProvider () {}

  Object.keys(globalConfig).forEach(function (key) {
    var methodName = 'set' + _.first(key).toUpperCase() + _.rest(key).join('');

    ResourcefulProvider.prototype[methodName] = function (newValue) {
      globalConfig[key] = newValue;
    };
  });

  ResourcefulProvider.prototype.$get = ['$http', '$parse', '$q', 'route', function ($http, $parse, $q, routeGetter) {
    /**
     *
     * @param {String} url
     * @returns {Resource}
     */
    return function resourceFactory(url, config) {
      config = config || {};

      var route = routeGetter(url, globalConfig.formatBaseUrl);
      var localActions = _.extend({}, globalConfig.defaultActions, config.actions);

      function extractParams(data, actionParams) {
        var ids = {};
        actionParams = _.extend({}, config.defaultParams, actionParams);

        _.forEach(actionParams, function (value, key) {
          if (_.isFunction(value)) {
            value = value();
          }
          ids[key] = value && value.charAt && value.charAt(0) === '@' ? $parse(value.substr(1))(data) : value;
        });
        return ids;
      }

      /**
       *
       * @name Resource
       * @constructor
       */
      function Resource(value) {
        angular.copy(value || {}, this);

        this.populateSubTypes();
      }

      Resource.addAction = function (name, config) {
        var hasBody = /^(POST|PUT|PATCH)$/i.test(config.method);

        Resource[name] = function (params, data) {
          if (arguments.length === 1 && hasBody) {
            data = params;
            params = undefined;
          }

          var isInstance = data instanceof Resource;
          var instance = isInstance ? data : (config.isArray ? [] : new Resource(data));
          var httpConfig = {};

          _.forEach(config, function (value, key) {
            if (['params', 'isArray', 'interceptor'].indexOf(key) === -1) {
              httpConfig[key] = angular.copy(value);
            }
          });

          httpConfig.data = data;

          route.setUrlParams(httpConfig, _.extend({}, extractParams(data, config.params || {}), params));

          return Resource.makeRequest(httpConfig, instance, config.interceptor || {}, !isInstance);
        };

        Resource.prototype['$' + name] = function (params) {
          var result =  Resource[name](params, this);

          return result.$promise || result;
        };
      };

      Resource.makeRequest = function (httpConfig, instance, interceptors, initCall) {
        var promise = $http(httpConfig).then(function success(response) {
          var data = response.data;
          var promise = instance.$promise;

          if (data) {
            if (_.isArray(instance)) {
              instance.length = 0;
              data.forEach(function (item) {
                instance.push(new Resource(item));
              });
            } else {
              angular.copy(data, instance);
              instance.populateSubTypes();
              instance.$promise = promise;
            }
          }

          instance.$resolved = true;

          response.resource = instance;

          return response;
        }, function errback(response) {
          instance.$resolved = true;

          return $q.reject(response);
        }).then(
            interceptors.response || globalConfig.defaultResponseInterceptor,
            interceptors.responseError
        );

        if (initCall) {
          // we are creating instance / collection
          // - set the initial promise
          // - return the instance / collection
          instance.$promise = promise;
          instance.$resolved = false;

          return instance;
        }

        // instance call
        return promise;
      };

      _.forEach(localActions, function (config, name) {
        Resource.addAction(name, config);
      });

      _.forEach(config.instanceMethods, function (value, key) {
        if (!this.hasOwnProperty(key)) {
          this[key] = value;
        }
      }, Resource.prototype);

      Resource.prototype.populateSubTypes = function () {
        _.forEach(config.subTypes, function (Value, key) {
          var getter = $parse(key);
          var data = getter(this);

          if (data) {
            getter.assign(this, new Value(data));
          }
        }, this);
      };

      return Resource;
    };
  }];

  angular.module('resourceful', []).provider('resourceful', ResourcefulProvider);
}());
