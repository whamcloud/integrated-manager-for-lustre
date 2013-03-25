//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


(function () {
  'use strict';

  angular.module('interceptors')
    .factory('tastypieInterceptor', function tastypieInterceptor () {
      /**
       * A Factory function that intercepts successful http responses
       * and puts the meta property at a higher level if it is a tastypie generated response.
       * @returns {Function} A new promise.
       */
      return function tastypieIntercepted (promise) {
        return promise.then(function (resp) {
          var fromTastyPie = _.isObject(resp.data) && _.isObject(resp.data.meta) && Array.isArray(resp.data.objects);

          // If we got data, and it looks like a tastypie meta/objects body
          // then pull off the meta.
          if (fromTastyPie) {
            var temp = resp.data.objects;

            resp.props = resp.data;
            delete resp.data.objects;

            resp.data = temp;
          }

          // Return the response for further processing.
          return resp;
        });
      };
    })
    .config(function ($httpProvider) {
      // register the interceptor.
      $httpProvider.responseInterceptors.push('tastypieInterceptor');
    });
}());
