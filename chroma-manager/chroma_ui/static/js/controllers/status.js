//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

  angular.module('controllers').controller('StatusCtrl',
    ['$scope', '$element', 'alertModel', 'eventModel', 'commandModel', 'notificationModel', 'confirmDialog',
      StatusCtrl]);

  function StatusCtrl ($scope, $element, alertModel, eventModel, commandModel, notificationModel, confirmDialog) {
    var dialog;

    var params = _.extend.bind(_, {}, {
      order_by: '-created_at',
      limit: 30,
      dismissed: false
    });
    var types = {};

    this.alertModel = alertModel.bind(params({
      order_by: '-begin'
    }));
    this.eventModel = eventModel.bind(params());
    this.commandModel = commandModel.bind(params());
    this.notificationModel = notificationModel.bind(params());

    // Flesh out types.
    ['alert', 'event', 'command', 'notification'].forEach(function populate (type) {
      var model = this['%sModel'.sprintf(type)];
      var historyModel = model.bind({
        dismissed: true
      });

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
    }, this);

    $scope.status = {
      /**
       * An object literal of types that are available.
       * @name types
       * @type object
       */
      types: types,
      /**
       * An object literal reference to the current type state.
       * @name state
       * @type object
       */
      state: types.notification,
      /**
       * The current message view, can be current || history
       * @name view
       * @type string
       */
      view: 'current',
      /**
       * Returns the current states view.
       * @name getViewState
       * @returns {object}
       */
      getViewState: function getViewState () {
        return this.state[this.view];
      },
      /**
       * A simple wrapper around getPage that scrolls the message container to the top.
       * @name updateViewState
       * @param {number} [page] If page is null || undefined then this method acts as a refresh for the current type.
       */
      updateViewState: function updateViewState (page) {
        this.getPage(page, true)
          .finally(function scrollTop() {
            $element.find('ul.messages').scrollTop(0);
          });
      },
      /**
       * @description Moves the current state to the specified page.
       * @name getPage
       * @param {number} [page] If page is null || undefined then this method acts as a refresh for the current type.
       * @param {boolean} shouldBlock Should this method block the page?
       * @returns {object} A promise.
       */
      getPage: function getPage (page, shouldBlock) {
        if (shouldBlock)
          block();

        var viewState = this.getViewState();

        var newPageParams;
        if (viewState.models)
          newPageParams = viewState.models.paging.getParams(page);
        else
          newPageParams = {};

        return viewState.model.query(newPageParams).$promise
          .then(function callback (res) {
            viewState.models = res;
          })
          .finally(function done() {
            if (shouldBlock)
              unblock();
          });
      },
      /**
       * Dismisses the passed in message, then refreshes the page.
       * @param {object} message The message to update and patch.
       * @param {boolean} noUpdate Whether an update should be triggered after this call.
       */
      dismiss: function dismiss (message, noUpdate) {
        message.dismiss()
          .then(function then (result) {
            if (result === true && !noUpdate)
              checkHealth();
          });
      },
      dismissAllConfirm: function dismissAllConfirm () {
        dialog = confirmDialog.setup({
          content: {
            title: 'Dismiss All',
            message: 'Do you wish to dismiss all status messages?',
            confirmText: 'Dismiss All'
          }
        });

        dialog
          .open()
          .then(function startRequest() {
            block();

            return notificationModel.dismissAll().$promise;
          })
          .finally(function done () {
            checkHealth();
            unblock();
          });
      }
    };

    $scope.$root.$on('health', $scope.status.getPage.bind($scope.status, null, false));

    /**
     * Places a blocking modal on the screen.
     */
    function block () {
      $scope.$emit('blockUi', {
        fadeIn: true,
        message: null
      });
    }

    /**
     * Removes the blocking modal from the screen
     */
    function unblock () {
      $scope.$emit('unblockUi');
    }

    /**
     * Emits an event to check system health.
     */
    function checkHealth () {
      $scope.$emit('checkHealth');
    }
  }
}(window.lodash));
