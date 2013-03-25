//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

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
      if(!Array.isArray(config.models)) {
        throw new TypeError('collectionModel expected config.models to be an array');
      }

      function query (success) {
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
