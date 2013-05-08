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

  function StatusCtrl ($scope, $q, alertModel, eventModel, commandModel, collectionModel) {
    var params = _.extend.bind(_, {}, {order_by: '-created_at', limit: 30, dismissed: false});

    var types = {};

    this.alertModel = alertModel.bind(params({order_by: '-begin'}));
    this.eventModel = eventModel.bind(params());
    this.commandModel = commandModel.bind(params());
    this.collectionModel = collectionModel({
      models: [
        {
          name: 'alertModel',
          model: this.alertModel.bind({limit: 10})
        },
        {
          name: 'eventModel',
          model: this.eventModel.bind({limit: 10})
        },
        {
          name: 'commandModel',
          model: this.commandModel.bind({limit: 10})
        }
      ]
    });

    // Flesh out types.
    ['alert', 'event', 'command', 'collection'].forEach(function populate(type) {
      var model = this['%sModel'.sprintf(type)];
      var historyModel = model.bind({dismissed: true});

      types[type] = {
        current: {
          name: type,
          model: model
        },
        history: {
          name: type,
          model: historyModel
        }
      };
    }.bind(this));

    $scope.status = {
      /**
       * @description An object literal of types that are available.
       * @name types
       * @type object
       */
      types: types,
      /**
       * @description An object literal reference to the current type state.
       * @name state
       * @type object
       */
      state: types.collection,
      /**
       * @description The current message view, can be current || history
       * @name view
       * @type string
       */
      view: 'current',
      /**
       * @description Returns the current states view.
       * @name getViewState
       * @returns {object}
       */
      getViewState: function () {
        return this.state[this.view];
      },
      /**
       * @description Moves the current state to the specified page.
       * @name getPage
       * @param {number} [page] If page is null || undefined then this method acts as a refresh for the current type.
       * @param {boolean} noBlock Should this method block the page?
       */
      getPage: function (page, noBlock) {
        if (!noBlock) {
          $.blockUI({message: null});
        }

        var viewState = this.getViewState();
        var func;

        if (viewState.models && viewState.models.$models) {
          viewState.models.paging.setPage(page);
          func = angular.noop;
        } else if (viewState.models) {
          //@TODO Leaky abstraction here, shouldn't have to set this directly.
          if (page != null) {
            viewState.models.paging.currentPage = page;
          }

          func = viewState.models.paging.getParams();
        }

        function callback(res) {
          viewState.models = res;
          unblock();
        }

        function unblock () {
          if (!noBlock) {
            $.unblockUI();
          }
        }

        viewState.model.query(func).$promise.then(callback, unblock);
      },
      /**
       * @description Dismisses the passed in message, then refreshes the page.
       * @name dismiss
       * @param {object} message The message to update and patch.
       * @param {boolean} noUpdate Whether an update should be triggered after this call.
       */
      dismiss: function (message, noUpdate) {
        message.dismissed = true;

        function success() { $scope.$emit('checkHealth'); }

        delete message.active;
        message.$patch().then(noUpdate? angular.noop: success);

        return message.$promise;
      }
    };

    /**
     * @description Patch all the messages.
     * @name dismissAll
     */
    $scope.status.dismissAll = function () {
      //@TODO: This is really bad, will not scale.
      var model = collectionModel({
        models: [
          {
            name: 'alertModel',
            model: this.alertModel.bind({limit: 0})
          },
          {
            name: 'eventModel',
            model: this.eventModel.bind({limit: 0})
          },
          {
            name: 'commandModel',
            model: this.commandModel.bind({limit: 0})
          }
        ]
      });

      //@TODO: This could probably be abstracted in the $http handler,
      $.blockUI({fadeIn: true, message: null});

      model.query(function success(res) {
        var promises = res.map(function (model) {
          return $scope.status.dismiss(model, true);
        });

        function callback() {
          $scope.$emit('checkHealth');
          $.unblockUI();
        }

        $q.all(promises).then(callback, callback);
      });
    }.bind(this);

    $scope.$root.$on('health', $scope.status.getPage.bind($scope.status, null, true));
  }

  angular.module('controllers').controller('StatusCtrl',
    ['$scope', '$q', 'alertModel', 'eventModel', 'commandModel', 'collectionModel', StatusCtrl]
  );
}(window.lodash));
