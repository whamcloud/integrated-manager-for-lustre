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

var nullSafe = fp.safe(1, fp.__, null);

angular.module('bigDifferModule')
  .value('diffObj3', fp.curry(4, function diffObj3Factory (lensMap, a, b, c) {
    return Object.keys(lensMap)
      .map(function getLenses (key) {
        return {
          name: key,
          lens: lensMap[key]
        };
      })
      .map(function buildDiffMap (lensItem) {
        var safeLens = nullSafe(lensItem.lens);
        var eqLens = fp.eqFn(safeLens, safeLens);

        var dirtyLocal = !eqLens(a, b);
        var dirtyRemote = !eqLens(a, c);
        var dirtyLocalRemote = !eqLens(b, c);

        if (!dirtyLocal && !dirtyRemote)
          return;

        var obj = {
          name: lensItem.name,
          lens: lensItem.lens,
          resetInitial: lensItem.lens.set(fp.__, a),
          resetLocal: lensItem.lens.set(fp.__, b),
          diff: {
            initial: safeLens(a),
            remote: safeLens(c)
          }
        };

        if (dirtyLocal && dirtyRemote && dirtyLocalRemote)
          obj.type = 'conflict';
        else if (dirtyLocal)
          obj.type = 'local';
        else if (dirtyRemote)
          obj.type = 'remote';

        return obj;
      })
      .filter(fp.identity)
      .reduce(function buildDiffMap (obj, lensItem) {
        obj[lensItem.name] = lensItem;

        return obj;
      }, {});
  }))
  .factory('diffObjInColl3', ['diffObj3', 'matchInColl', function diffObjInColl3Factory (diffObj3, matchInColl) {
    return fp.curry(5, function diffObjInColl3 (idLens, lensMap, ax, b, cx) {
      var matchById = matchInColl(idLens, fp.__, b);
      var aMatch = matchById(ax);
      var cMatch = matchById(cx);

      return diffObj3(lensMap, aMatch, b, cMatch);
    });
  }])
  .factory('mergeObj', ['diffObj3', function mergeObjFactory (diffObj3) {
    return fp.curry(3, function mergeObj (lensMap, local, remote) {
      local = angular.copy(local);
      remote = angular.copy(remote);

      if (local == null)
        return remote;

      var dirties = diffObj3(lensMap, local, local, remote);

      var dirtyKeys = Object.keys(dirties);

      if (dirtyKeys)
        dirtyKeys.forEach(function patch (key) {
          var dirty = dirties[key];

          dirty.lens.set(dirty.diff.initial, remote);
        });

      return remote;
    });
  }])
  .value('matchInColl', fp.curry(3, function matchInColl (idLens, coll, item) {
    var eqIdLens = fp.eqLens(nullSafe(idLens), item);
    return fp.find(eqIdLens, coll);
  }))
  .factory('mergeColl', ['mergeObj', 'matchInColl', function mergeCollFactory (mergeObj, matchInColl) {
    return fp.curry(4, function mergeColl (idLens, lensMap, locals, remotes) {
      locals = angular.copy(locals);
      remotes = angular.copy(remotes);

      var matchLocal = matchInColl(idLens, locals);

      return remotes.map(function mergeMatches (item) {
        var localMatch = matchLocal(item);

        return localMatch ? mergeObj(lensMap, localMatch, item) : item;
      });
    });
  }])
  .service('bigDiffer', ['diffObj3', 'mergeObj', 'mergeColl', 'diffObjInColl3',
    function BigDiffer (diffObj3, mergeObj, mergeColl, diffObjInColl3) {
      this.diffObj3 = diffObj3;
      this.diffObjInColl3 = diffObjInColl3;
      this.mergeObj = mergeObj;
      this.mergeColl = mergeColl;
    }]);
