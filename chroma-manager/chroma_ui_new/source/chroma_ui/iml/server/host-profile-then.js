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


angular.module('server')
  .factory('getHostProfiles', ['throwIfError', 'CACHE_INITIAL_DATA',
    function getHostProfilesFactory (throwIfError, CACHE_INITIAL_DATA) {
    'use strict';

    /**
     * Fetches host profiles and formats them nicely
     * @param {Function} flint
     * @param {Array} hosts
     * @returns {Object}
     */
    return function getHostProfiles (flint, hosts) {
      var spark = flint('hostProfile');

      spark.sendGet('/host_profile', {
        qs: {
          id__in: _.pluck(hosts, 'id'),
          server_profile__user_selectable: true,
          limit: 0
        }
      });

      return spark
        .addPipe(throwIfError(_.identity))
        .addPipe(_.pluckPath('body.objects'))
        .addPipe(_.fmapProp('host_profiles'))
        .addPipe(function (hosts) {
          // Pull out the profiles and flatten them.
          var profiles = [{}]
            .concat(_.pluck(hosts, 'profiles'))
            .concat(function concatArrays (a, b) {
              return _.isArray(a) ? a.concat(b) : undefined;
            });
          var merged = _.merge.apply(_, profiles);

          return Object.keys(merged).reduce(function buildStructure (arr, profileName) {
            var item = {
              name: profileName,
              uiName: _.find(CACHE_INITIAL_DATA.server_profile, { name: profileName }).ui_name,
              invalid: merged[profileName].some(didProfileFail)
            };

            item.hosts = hosts.map(function setHosts (host) {
              var profiles = host.profiles[profileName];

              return {
                address: host.address,
                invalid: profiles.some(didProfileFail),
                problems: profiles,
                uiName: item.uiName
              };
            });

            arr.push(item);

            return arr;
          }, []);
        });


      /**
       * Predicate. Did the given profile fail it's checks.
       * @param {Object} profile The profile to check.
       * @returns {boolean}
       */
      function didProfileFail (profile) {
        return !profile.pass;
      }
    };
}
  ])
  .factory('createHostProfiles', ['requestSocket', 'waitForCommandCompletion',
    function createHostProfilesFactory (requestSocket, waitForCommandCompletion) {
      'use strict';

      return function createHostProfiles (serverSpark, profile, showCommands) {
        var spark = requestSocket();

        var wasServerSpecified = _.partialRight(
          _.checkCollForValue(['fqdn', 'nodename', 'address']),
          _.pluck(profile.hosts, 'address')
        );

        var createHostProfilesPromise = serverSpark.onceValueThen('data')
          .then(_.pluckPath('body.objects'))
          .then(_.ffilter(function limitToUnconfigured (server) {
            return server.server_profile && server.server_profile.initial_state === 'unconfigured';
          }))
          .then(_.ffilter(wasServerSpecified))
          .then(_.fmap(function (server) {
            return {
              host: server.id,
              profile: profile.name
            };
          }))
          .then(_.if(_.size, function (hostProfiles) {
            return spark.sendPost('/host_profile', {
              json: { objects: hostProfiles }
            }, true)
              .then(_.unwrapResponse(_.fmap(function (obj) {
                return { command: obj.commands[0]} ;
              })))
              .then(waitForCommandCompletion(showCommands));
          }))
          .catch(function throwError (response) {
            throw response.error;
          });

          createHostProfilesPromise.finally(function snuffSpark () {
            spark.end();
          });

          return createHostProfilesPromise;
      };
  }]);
