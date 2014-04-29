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


angular.module('sortable', []).directive('sorter', [function () {
  'use strict';

  var CLASS_NAMES = {
    OVERLAY: 'sort-overlay',
    SORTING: 'sorting',
    OVER: 'over'
  },
  sortOverlay = document.createElement('div');
  sortOverlay.className = CLASS_NAMES.OVERLAY;

  return {
    restrict: 'A',
    scope: { items: '=' },
    controller: ['$element', '$scope', function ($element, $scope) {
      var self = this;

      this._sortItems = [];

      this.addSortItem = function (item) {
        this._sortItems.push(item);
      };

      this.dragStart = function () {
        $element.addClass(CLASS_NAMES.SORTING);

        self._sortItems.forEach(function (item) {
          var overlay = angular.element(sortOverlay.cloneNode()).appendTo(item)[0];

          overlay.addEventListener('dragenter', dragEnter, false);

          overlay.addEventListener('dragover', dragOver, false);

          overlay.addEventListener('dragleave', dragLeave, false);

          overlay.addEventListener('drop', drop, false);
        });
      };

      this.dragEnd = function () {
        $element.removeClass(CLASS_NAMES.SORTING);
      };

      function dragEnter(event) {
        // jshint validthis: true
        angular.element(this).addClass(CLASS_NAMES.OVER);

        if (event.preventDefault) event.preventDefault();

        return false;
      }

      function dragOver(event) {
        event.dataTransfer.dropEffect = 'move';

        if (event.preventDefault) event.preventDefault();

        return false;
      }

      function dragLeave() {
        // jshint validthis: true
        angular.element(this).removeClass(CLASS_NAMES.OVER);
      }

      function drop(event) {
        $scope.$apply(function () {
          var index = parseInt(event.dataTransfer.getData('text'), 10),
            toMove = $scope.items.splice(index, 1).pop();

          $scope.items.splice(angular.element(event.target).scope().$index, 0, toMove);

          $element.find('.' + CLASS_NAMES.OVERLAY).each(function () {
            this.removeEventListener('dragenter', dragEnter, false);

            this.removeEventListener('dragover', dragOver, false);

            this.removeEventListener('dragleave', dragLeave, false);

            this.removeEventListener('drop', drop, false);
          }).remove();
        });

        if (event.stopPropagation) event.stopPropagation();
        event.preventDefault();

        return false;
      }

      $scope.$on('$destroy', function () {
        self._sortItems = null;
      });
    }]
  };
}]).directive('sortItem', [function () {
  'use strict';

  return {
    restrict: 'A',
    require: '^sorter',
    link: function ($scope, wrappedEl, attrs, sortContainerCtrl) {
      var el = wrappedEl[0];

      sortContainerCtrl.addSortItem(wrappedEl);

      wrappedEl.attr('draggable', true);

      el.addEventListener('dragstart', dragStart, false);

      el.addEventListener('dragend', sortContainerCtrl.dragEnd, false);

      $scope.$on('$destroy', function () {
        el.removeEventListener('dragstart', dragStart, false);
        el.removeEventListener('dragend', sortContainerCtrl.dragEnd, false);

        el = null;
        wrappedEl = null;
      });

      function dragStart(event) {
        sortContainerCtrl.dragStart();

        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text', $scope.$index.toString());
      }
    }
  };
}]);
