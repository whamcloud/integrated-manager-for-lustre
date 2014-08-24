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


(function () {
  'use strict';


  // This is gross but we can't depend on $http to be working when there is an exception.
  // We also may not auto cache templates at dev time.
  var template = '<div class="modal-header"> \
        <h3>An Error Has Occurred!</h3> \
    </div> \
    <div class="modal-body"> \
      <ul> \
        <li ng-repeat="item in exceptionModal.messages"> \
          <h5>{{ item.name | capitalize:true }}:</h5> \
          <pre ng-if="exceptionModal.loadingStack && item.name === \'Client Stack Trace\'" \
          class="loading">Processing... <i class="fa fa-spinner fa-spin fa-2x"></i></pre> \
          <pre ng-if="!exceptionModal.loadingStack || item.name !== \'Client Stack Trace\'">{{item.value}}</pre> \
        </li> \
      </ul> \
    </div> \
    <div class="modal-footer"> \
      <button ng-click="exceptionModal.reload()" class="btn btn-large btn-block" type="button"> \
        <i class="icon-rotate-right"></i> Reload\
      </button> \
    </div>';


  angular.module('exception').factory('exceptionModal', ['$modal', function ($modal) {
    var defaultOptions = {
      backdrop: 'static',
      controller: 'ExceptionModalCtrl',
      keyboard: false,
      template: template,
      windowClass: 'exception-modal'
    };

    return function open(opts) {
      var options = _.merge(defaultOptions, opts);

      return $modal.open(options);
    };
  }]);
}());
