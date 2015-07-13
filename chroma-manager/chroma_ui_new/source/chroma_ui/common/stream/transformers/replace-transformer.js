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


/**
 * This creates a transformer that replaces data in the scope with data from the backend.
 */
angular.module('stream').factory('replaceTransformer', [function replaceTransformerFactory() {
  'use strict';

  function updateObject(oldObject, newObject) {
    // If there is a version to compare, only update existing objects
    // with newer data.
    if (newObject.version != null &&
        parseFloat(newObject.version) <= parseFloat(oldObject.version))
      return;

    _(oldObject).clear().assign(newObject);
  }

  function updateResourceArray(currentObjects, incomingObjects) {
    var updateObjects = [];

    incomingObjects.forEach(function (item) {
      if (item.id == null)
        throw new Error('Incoming resources must have an .id property!');

      var currentObject = _.find(currentObjects, { id: item.id });
      if (currentObject == null) {
        // Not found. New object.
        updateObjects.push(item);
      } else {
        updateObject(currentObject, item);
        updateObjects.push(currentObject);
      }
    });

    // Replace the current list of objects with our list of updated
    // and new objects. This way we handle deleted objects.
    _.replace(currentObjects, updateObjects);
  }

  /**
   * Test for the characteristics of a Tastypie resource list
   * (e.g. GET /api/foo/).
   */
  function isResourceList(data) {
    return (data != null && Array.isArray(data.objects));
  }

  /**
   * Update data in the bound scope variable with incoming stream data.
   *   Metric data is completely replaced.
   *   API resource objects are individually updated.
   */
  return function replaceScope(resp) {
    var scopeData = this.getter();
    var newData = resp.body;

    if (isResourceList(scopeData) && isResourceList(newData)) {
      /* Looks like a Tastypie resource list. */
      updateResourceArray(scopeData.objects, newData.objects);
    } else if (Array.isArray(scopeData)) {
      /* Looks like a list of metric datapoints. */
      if (!Array.isArray(newData))
        throw new Error('scopeData and newData must both be the same type!');

      _.replace(scopeData, newData);
    } else {
      updateObject(scopeData, newData);
    }

    return scopeData;
  };
}]);
