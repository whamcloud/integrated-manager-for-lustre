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

  angular.module('status')
  /**
   * Constant representing the state directive size. The size specified will affect what is rendered on the view.
   */
    .constant('STATE_SIZE', {
      SMALL: 'small',
      MEDIUM: 'medium',
      LARGE: 'large'
    })
  /**
   * Job monitor factory sets up a spark and sends a get request to the /job API. The sparksend function is
   * overriden such that it will set the spark to null after it ends. Include this service in a controller and make
   * sure to call the end method when the controller is destroyed:
   * $scope.$on('$destroy', function onDestroy () {
   *    jobMonitor().end();
   *  });
   *  @param {String} jobMonitor - The service name
   *  @param {Array} Dependencies and the actual service HOF being returned.
   */
    .factory('jobMonitor', ['requestSocket',
      /**
       * Returns a function that returns a spark, which listens on the /job API.
       * @param {Object} requestSocket
       * @returns {Function}
       */
      function jobMonitorFactory (requestSocket) {
        var extendedSpark;

        /**
         * The job monitor Service
         * @return {Object} The extended spark object
         */
        return function innerJobMonitorFactory () {
          if (extendedSpark)
            return extendedSpark;

          var spark = requestSocket();
          extendedSpark = Object.create(spark);
          extendedSpark.end = function end () {
            spark.end();
            spark = null;
            extendedSpark = null;
          };

          // Get the list of pending and tasked jobs
          extendedSpark.sendGet('/job/', {
            qs: {
              limit: 0,
              state__in: ['pending', 'tasked']
            }
          });

          return extendedSpark;
        };
      }])

  /**
   * Alert monitor factory sets up a spark and sends a get request to the /alert API. The sparksend function is
   * overriden such that it will set the spark to null after it ends. Include this service in a controller and make
   * sure to call the end method when the controller is destroyed:
   * $scope.$on('$destroy', function onDestroy () {
   *    alertMonitor().end();
   *  });
   *  @param {String} The alertMonitor service
   *  @param {Array} The alert monitor dependencies and function
   */
    .factory('alertMonitor', ['requestSocket',

      /**
       * Returns a function that returns a spark, which listens on the /alert API.
       * @param {Object} requestSocket
       * @returns {Function}
       */
      function alertMonitorFactory (requestSocket) {
        var extendedSpark;

        /**
         * The alert monitor Service
         * @return {Object} The extended spark object
         */
        return function innerAlertMonitorFactory () {
          if (extendedSpark)
            return extendedSpark;

          var spark = requestSocket();
          extendedSpark = Object.create(spark);
          extendedSpark.end = function end () {
            spark.end();
            spark = null;
            extendedSpark = null;
          };

          // Get the list of pending and tasked jobs
          extendedSpark.sendGet('/alert/', {
            qs: {
              limit: 0,
              active: true
            }
          });

          return extendedSpark;
        };
      }])

  /**
   * Job status directive. This directive will show a lock icon if there is a job running for the specified record id.
   * When rolling over the icon a tooltip will appear indicating how many messages there are in total for both read
   * and write locks. Additionally, if you click the lock icon, it will display a popover with one or two accordions.
   * These accordions can be expanded to list the background jobs. As the jobs complete, they are crossed out. You can
   * close the popover by clicking anywhere outside its region. Note that the lock icon and the popover will remain
   * visible, even if all the jobs finish.
   */
    .directive('jobStatus', ['jobMonitor', function jobStatus (jobMonitor) {

      // record contains a resource uri which maps to the write_locks[0]locked_item_uri
      return {
        scope: {
          recordId: '='
        },
        restrict: 'E',
        replace: true,
        templateUrl: 'common/status/assets/html/job-status.html',

        /**
         * The link function
         * @param {Object} scope
         * @param {Object} element
         */
        link: function (scope, element) {
          var jobs = [];
          var readMessages = [];
          var writeMessages = [];
          var readMessageRecord = [];
          var readMessageDifference = [];
          var writeMessageRecord = [];
          var writeMessageDifference = [];

          /**
           * Called whenever there is a data change on the jobMonitor spark.
           * @param {Object} response The response returned by the spark
           */
          jobMonitor().onValue('data', function onValueData (response) {
            if (!response.body)
              return; // Do I need to throw an error here?

            readMessages = [];
            writeMessages = [];

            jobs = response.body.objects.filter(function mapJobs (job) {
              var foundMatch = false;
              if (doesMatch(job.write_locks)) {
                writeMessages.push(job.description);
                foundMatch = true;
              }
              if (doesMatch(job.read_locks)) {
                readMessages.push(job.description);
                foundMatch = true;
              }

              return foundMatch;
            });

            readMessageRecord = _.uniq(readMessageRecord.concat(readMessages));
            readMessageDifference = _.difference(readMessageRecord, readMessages);
            writeMessageRecord = _.uniq(writeMessageRecord.concat(writeMessages));
            writeMessageDifference = _.difference(writeMessageRecord, writeMessages);
          });

          /**
           * Watches for the directive's popover to become visible or hidden. When it detects a change it
           * clears the message records.
           */
          scope.$watch(function () {
            return element.find('.popover.in').html();
          },
            /**
             * Clears the message records if the status of the popover has changed.
             * @param {String} newVal
             * @param {String} oldVal
             */
            function (newVal, oldVal) {
            if (newVal !== oldVal && newVal == null) {
              scope.jobStatus.clearMessageRecords();
            }
          });

          /**
           * Determines if any of the joblocks matche the record id of this directive.
           * @param {Array} jobLocks
           * @returns {Boolean}
           */
          function doesMatch (jobLocks) {
            if (jobLocks == null)
              return false;

            return jobLocks.some(function matchesRecordId (lock) {
              return lock.locked_item_uri === scope.recordId;
            });
          }

          scope.jobStatus = {
            closeOthers: false,
            openWrite: true,
            openRead: true,
            /**
             * Getter that returns if there are any job messages for this directive.
             * @returns {Boolean}
             */
            containsJobMessages: function containsJobMessages () {
              return jobs.length > 0;
            },
            /**
             * Getter that returns the read messages.
             * @returns {Array}
             */
            getReadMessages: function getReadMessages () {
              return readMessages;
            },
            /**
             * Getter that returns the read message record.
             * @returns {Array}
             */
            getReadMessageRecord: function getReadMessageRecord () {
              return readMessageRecord;
            },
            /**
             * Gets the difference between the current read list of messages and the total list of read messages that
             * have occurred since the command started.
             * @returns {Array}
             */
            getReadMessageDifference: function getReadMessageDifference () {
              return readMessageDifference;
            },
            /**
             * Gets the list of write messages.
             * @returns {Array}
             */
            getWriteMessages: function getWriteMessages () {
              return writeMessages;
            },
            /**
             * Gets the total list of write messages that have occurred since the command started.
             * @returns {Array}
             */
            getWriteMessageRecord: function getWriteMessageRecord () {
              return writeMessageRecord;
            },
            /**
             * Gets the difference between the current list of write messages and the total list of write messages that
             * have occurred since the command started.
             * @returns {Array}
             */
            getWriteMessageDifference: function getWriteMessageDifference () {
              return writeMessageDifference;
            },
            /**
             * Clears all message records and differences for both write and read locks.
             */
            clearMessageRecords: function clearMessageRecords () {
              readMessageRecord = [];
              readMessageDifference = [];
              writeMessageRecord = [];
              writeMessageDifference = [];
            },
            /**
             * Indicates if the lock icon should be visible. In this case, it is displayed if there are either
             * write or read messages OR if the popover is still open. This is important because if there are no more
             * messages, the user may still be reading through the messages that have been crossed out (they've been
             * removed from the current list but still exist in the message record). While reading through these
             * messages the lock icon should still be visible.
             * @returns {boolean}
             */
            shouldShowLockIcon: function shouldShowLockIcon () {
              return writeMessages.length + readMessages.length > 0 || element.find('.popover.in').html() != null;
            },
            /**
             * Returns the tooltip message for the lock icon based on the write and read message lengths.
             * @returns {String}
             */
            getLockTooltipMessage: function getLockTooltipMessage () {
              var message = '';
              var writeMessageMap, readMessageMap;

              if (writeMessages.length > 0 && readMessages.length > 0) {
                writeMessageMap = {
                  '1': 'There is 1 ongoing write lock operation and ',
                  'other': 'There are {} ongoing write lock operations and '
                };
                var writeMessage = _.pluralize(writeMessages.length, writeMessageMap);

                readMessageMap = {
                  '1': '1 pending read lock operation.',
                  'other': '{} pending read lock operations.'
                };
                var readMessage = _.pluralize(readMessages.length, readMessageMap);

                message = writeMessage + readMessage + ' Click to review details.';

              } else if (writeMessages.length > 0) {
                writeMessageMap = {
                  '1': '1 ongoing write lock operation.',
                  'other': '{} ongoing write lock operations.'
                };
                message = _.pluralize(writeMessages.length, writeMessageMap) + ' Click to review details.';
              } else if (readMessages.length > 0) {
                readMessageMap = {
                  '1': 'Locked by 1 pending operation.',
                  'other': 'Locked by {} pending operations.'
                };
                message = _.pluralize(readMessages.length, readMessageMap) + ' Click to review details.';
              }

              return message;
            }
          };
        }
      };
    }])

  /**
   * Record state directive. This directive will show a lock icon if there is an alert for the specified record id.
   * When rolling over the icon a tooltip will appear indicating how many alerts there are in total. Additionally,
   * if you click the state icon, it will display a popover with one accordion. This accordion can be expanded to
   * display the list of alerts. As the number of alerts is reduced, they are crossed out. You can close the popover
   * by clicking anywhere outside its region.
   */
    .directive('recordState', ['alertMonitor', 'STATE_SIZE', function recordState (alertMonitor, STATE_SIZE) {

      // record contains a resource uri which maps to the write_locks[0]locked_item_uri
      return {
        scope: {
          recordId: '=',
          displayType: '='
        },
        restrict: 'E',
        replace: true,
        templateUrl: 'common/status/assets/html/record-state.html',
        link: function (scope, element) {
          var alerts = [];
          var messageRecord = [];
          var messageDifference = [];

          /**
           * Called whenever there is a data change on the alertMonitor spark.
           * @param {Object} response The response returned by the spark
           */
          alertMonitor().onValue('data', function onValueData (response) {
            if (!response.body)
              return;

            alerts = _.pluck(response.body.objects.filter(function mapAlerts (alert) {
              return alert.alert_item === scope.recordId;
            }), 'message');

            messageRecord = _.uniq(messageRecord.concat(alerts));

            // After receiving the alerts we need to compare the new alert list to the current alert list and take the
            // difference.
            messageDifference = _.difference(messageRecord, alerts);
          });

          /**
           * Watches for the directive's popover to become visible or hidden. When it detects a change it
           * clears the message records.
           */
          scope.$watch(function () {
            return element.find('.popover.in').html();
          },
            /**
             * Clears the message records if the status of the popover has changed.
             * @param {String} newVal
             * @param {String} oldVal
             */
            function (newVal, oldVal) {
            if (newVal !== oldVal && newVal == null)
              scope.recordState.clearMessageRecord();
          });

          scope.recordState = {
            /**
             * Indicates if the command contains alerts (the directive is in an alert state).
             * @returns {Boolean}
             */
            isInErrorState: function isInErrorState () {
              return alerts.length > 0;
            },
            /**
             * Returns the list of alerts.
             * @returns {Array}
             */
            getAlerts: function getAlerts () {
              return alerts;
            },
            /**
             * Returns the list of message records.
             * @returns {Array}
             */
            getMessageRecord: function getMessageRecord () {
              return messageRecord;
            },
            /**
             * Returns the difference between the current set of alerts and the alerts that have occurred since the
             * start of the command.
             * @returns {Array}
             */
            getMessageDifference: function getMessageDifference () {
              return messageDifference;
            },
            /**
             * Clears the message record and difference arrays.
             */
            clearMessageRecord: function clearMessageRecord () {
              messageDifference = [];
              messageRecord = [];
            },
            /**
             * Retrieves the tool tip message based on the number of alerts.
             * @returns {String}
             */
            getTooltipMessage: function getTooltipMessage () {
              var messageMap = {
                '0': 'No alerts.',
                '1': '1 alert message. Click to review details.',
                'other': '{} alert messages. Click to review details.'
              };

              return _.pluralize(alerts.length, messageMap);
            },
            showLabel: function showLabel () {
              return scope.displayType === STATE_SIZE.MEDIUM;
            }
          };
        }
      };
    }]);
})();


