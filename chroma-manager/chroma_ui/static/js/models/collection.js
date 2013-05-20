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


(function (_) {
  'use strict';

  angular.module('models').factory('collectionModel', ['$q', function ($q) {
    /**
     * @description Returns a list which is a concatenation of the passed in models.
     * @name messagesFactory
     * @param {{
     *   models: [
     *     {
     *       name: string,
     *       model: function
     *     }
     *   ],
     *   sorter: function
     * }} config
     * @function
     */
    return function collectionFactory(config) {
      if (!Array.isArray(config.models)) {
        throw new TypeError('collectionModel expected config.models to be an array');
      }

      function query(success) {
        /*jshint validthis: true */

        var collection;

        if (Array.isArray(this)) {
          collection = this;
        } else {
          collection = [];
          collection.$models = config.models;
          collection.query = query;
        }

        var models = config.models.map(function (model) {
          return model.model.query();
        });

        collection.$promise = $q.all(_.pluck(models, '$promise')).then(function success() {
          // Join the models, empty the collection and splice in.
          var params = [].concat.apply([0, collection.length], models);
          [].splice.apply(collection, params);

          //@TODO Move this into paging service.
          var pagers = _.pluck(models, 'paging');

          collection.paging = {
            limit: Math.min.apply(null, _.pluck(pagers, 'limit')),
            noOfPages: Math.max.apply(null, _.pluck(pagers, 'noOfPages')),
            currentPage: Math.max.apply(null, _.pluck(pagers, 'currentPage')),
            setPage: function (page) {
              config.models.forEach(function (item, index) {
                var curr = models[index].paging;

                if (page != null) {
                  curr.currentPage = page;
                }

                item.model = item.model.bind(curr.getParams());
              });
            }
          };

          return collection;
        });

        collection.$promise.then(success);

        return collection;
      }

      return {
        query: query,
        bind: function (params) {
          var cloned = _.cloneDeep(config);

          cloned.models.forEach(function (item) {
            item.model = item.model.bind(params);
          });

          return collectionFactory(cloned);
        }
      };
    };
  }]);
}(window.lodash));
