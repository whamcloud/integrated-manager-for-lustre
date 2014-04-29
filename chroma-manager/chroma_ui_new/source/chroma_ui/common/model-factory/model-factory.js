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


angular.module('modelFactory').provider('modelFactory', function () {
  'use strict';

  var urlPrefix = '';

  return {
    setUrlPrefix: function (url) {
      urlPrefix = url;
    },
    $get: ['$resource', function ($resource) {
      /**
       * @description Extends $resource making it slightly more useful.
       * @returns {$resource}
       * @constructor
       */
      return function getModel(config) {
        var defaults = {
          actions: {
            get: { method: 'GET' },
            save: { method: 'POST' },
            update: { method: 'PUT' },
            delete: { method: 'DELETE' },
            patch: { method: 'PATCH' },
            query: { method: 'GET', isArray: true }
          },
          params: {},
          subTypes: {}
        };

        var merged = _.merge(defaults, config);

        if (merged.url === undefined) throw new Error('A url property must be provided to modelFactory!');

        _(merged.actions).forEach(function (action) {
          action.interceptor = {
            response: function (resp) {
              if (!Resource.subTypes) return resp.resource;

              var boundAddSubTypes = addSubTypes.bind(null, Resource.subTypes);

              if (action.isArray)
                resp.resource.forEach(boundAddSubTypes);
              else
                boundAddSubTypes(resp.resource);

              return resp.resource;
            }
          };
        });

        var Resource = $resource(urlPrefix + merged.url, merged.params, merged.actions);

        return Resource;

        function addSubTypes(subTypes, resource) {
          _(subTypes || {}).forEach(function (SubType, name) {
            if (!resource.hasOwnProperty(name)) return;

            resource[name] = new SubType(resource[name]);

            if (SubType.subTypes) addSubTypes(SubType.subTypes, resource[name]);
          });
        }
      };
    }]
  };
});
