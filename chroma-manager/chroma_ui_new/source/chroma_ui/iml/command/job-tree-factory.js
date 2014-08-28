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


angular.module('command')
  .factory('jobTree', function jobTreeFactory () {
    'use strict';

    /**
     * Given an array of jobs turns them into
     * a tree structure.
     * @param {Array} jobs
     * @returns {Object}
     */
    return function jobTree (jobs) {
      var shallowestOccurrence = {};

      var children = _(jobs).pluck('wait_for').flatten().unique().value();
      var roots = _(jobs).pluck('resource_uri').difference(children).value();

      var tree = roots.map(function buildTree (uri) {
        var root = getAJob(uri);
        return jobChildren(root, 0);
      });

      tree.forEach(function pruneTree (job) {
        prune(job, 0);
      });

      return tree;

      /**
       * Returns a job for a given resource_uri
       * or undefined if there is no match.
       * @param {String} uri
       * @returns {Object|undefined}
       */
      function getAJob (uri) {
        return _.find(jobs, { resource_uri: uri });
      }

      /**
       * Populates a job with it's children.
       * Marks the shallowest occurrence of a job for pruning purposes.
       * @param {Object} job
       * @param {Number} depth
       * @returns {Object}
       */
      function jobChildren (job, depth) {
        var shallowest = shallowestOccurrence[job.resource_uri];
        if (shallowest == null || shallowest > depth)
          shallowestOccurrence[job.resource_uri] = depth;

        var children = job.wait_for.reduce(function expandChildren (arr, uri) {
          var child = getAJob(uri);

          if (child)
            arr.push(jobChildren(child, depth + 1));

          return arr;
        }, []);

        return _.extend({ children: children }, job);
      }

      /**
       * Traverses the tree removing jobs deeper than
       * their shallowest depth.
       * @param {Object} job
       * @param {Number} depth
       */
      function prune (job, depth) {
        var childDepth = depth + 1;

        job.children = job.children
          .filter(function pruneByDepth (child) {
            return shallowestOccurrence[child.resource_uri] >= childDepth;
          })
          .map(function pruneChild (child) {
            prune(child, childDepth);

            return child;
          });
      }
    };
  });
