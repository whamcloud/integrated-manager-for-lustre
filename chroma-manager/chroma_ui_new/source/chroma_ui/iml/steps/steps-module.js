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

  angular.module('steps-module', [])
    .directive('stepContainer', ['$q', '$controller', '$http', '$templateCache', '$compile', 'getResolvePromises',
      function stepContainerDirective ($q, $controller, $http, $templateCache, $compile, getResolvePromises) {
        return {
          restrict: 'E',
          scope: {
            manager: '='
          },
          link: function link (scope, el) {
            var innerScope, resolvesFinished;

            /**
             * Listens for changes and updates the view.
             * @param {Object} step
             * @param {Object} [extraResolves]
             * @param {Object} [waitingStep]
             */
            scope.manager.registerChangeListener(function onChanges (step, extraResolves, waitingStep) {
              var resolves = _.extend({}, step.resolve, extraResolves);
              var promises = getResolvePromises(resolves);
              promises.template = getTemplatePromise(step.templateUrl);

              if (!resolvesFinished && waitingStep && waitingStep.templateUrl) {
                // Create new scope
                innerScope = scope.$new();

                getTemplatePromise(waitingStep.templateUrl)
                  .then(function loadUntilTemplate(template) {
                    // Make sure the resolves haven't finished before loading the template
                    if (!resolvesFinished) {
                      loadUpSteps({$scope: innerScope}, el, template, waitingStep.controller);
                    }
                  });
              }

              $q.all(promises)
                .then(function (resolves) {
                  // Indicate that resolves are complete so the untilTemplate isn't loaded
                  resolvesFinished = true;

                  var template = resolves.template;
                  delete resolves.template;

                  if (innerScope)
                    innerScope.$destroy();

                  resolves.$scope = innerScope = scope.$new();
                  resolves.$stepInstance = {
                    transition: scope.manager.transition,
                    end: scope.manager.end,
                    setState: scope.manager.setState,
                    getState: scope.manager.getState
                  };

                  loadUpSteps(resolves, el, template, step.controller);
                });

              /**
               * Loads the steps
               * @param {Object} resolves
               * @param {Object} el
               * @param {String} template
               * @param {Object} controller
               */
              function loadUpSteps (resolves, el, template, controller) {
                if (controller)
                  $controller(controller, resolves);

                el.html(template);

                $compile(el.children())(resolves.$scope);
              }
            });

            scope.$on('$destroy', function onDestroy () {
              scope.manager.destroy();

              if (innerScope)
                innerScope.$destroy();
            });
          }
        };

        function getTemplatePromise (templateUrl) {
          return $http.get(templateUrl, {cache: $templateCache})
            .then(function (result) {
              return result.data;
            });
        }
      }
    ])
    .factory('stepsManager', ['$q', '$injector', 'getResolvePromises',
      function stepManagerFactory ($q, $injector, getResolvePromises) {
        return function stepManager () {
          var currentStep, listener, pending;
          var steps = {};
          var states = {};
          var endDeferred = $q.defer();

          return {
            /**
             * Adds the waiting step.
             * @param {Object} step
             * @throws
             * @returns {*}
             */
            addWaitingStep: function addWaitingStep (step) {
              if (steps.waitingStep)
                throw new Error('Cannot assign the waiting step as it is already defined.');

              steps.waitingStep = step;

              return this;
            },
            /**
             * Adds a step to the manager.
             * @param {String} stepName
             * @param {Object} step
             * @returns {Object}
             */
            addStep: function addStep (stepName, step) {
              steps[stepName] = step;

              return this;
            },
            /**
             * Starts the step process.
             * @param {String} stepName
             * @param {Object} [extraResolves] Any extra resolves to pass in.
             * @returns {Object}
             */
            start: function start (stepName, extraResolves) {
              if (listener)
                listener(steps[stepName], extraResolves, steps.waitingStep);
              else
                pending = {
                  step: steps[stepName],
                  extraResolves: extraResolves
                };

              currentStep = steps[stepName];

              return this;
            },
            /**
             * Performs a transition from one step to another
             * @param {String} action
             * @param {Object} [extraResolves]
             */
            transition: function transition (action, extraResolves) {
              if (!currentStep)
                return;

              $q.all(getResolvePromises(extraResolves))
                .then(function (resolves) {
                  resolves.$transition = {
                    action: action,
                    steps: steps,
                    /**
                     * End the steps.
                     * @param {*} data
                     */
                    end: function end (data) {
                      endDeferred.resolve(data);
                    }
                  };

                  return $injector.invoke(currentStep.transition, null, resolves);
                })
                .then(function (next) {
                  if (next) {
                    currentStep = next.step;
                    listener(next.step, next.resolve);
                  }
                });
            },
            /**
             * Adds a change listener that gets called when a step changes.
             * @param {Function} changeListener
             * @returns {Object}
             */
            registerChangeListener: function registerChangeListener (changeListener) {
              listener = changeListener;

              if (pending) {
                listener(pending.step, pending.extraResolves, steps.waitingStep);
                pending = null;
              }

              return this;
            },
            /**
             * Sets state for the current step.
             * @param {*} state
             */
            setState: function setState (state) {
              var name = _.findKey(steps, currentStep);

              states[name] = state;
            },
            /**
             * Gets state for the current step.
             * @returns {*}
             */
            getState: function getState () {
              var name = _.findKey(steps, currentStep);

              return states[name];
            },
            /**
             * Cleans all references.
             */
            destroy: function destroy () {
              listener = steps = currentStep = states = pending = null;
            },
            result: {
              end: endDeferred.promise
            }
          };
        };
      }
    ])
    .factory('getResolvePromises', ['$q', '$injector', function ($q, $injector) {
      /**
       * Takes an object of resolves and invokes them all.
       * The result of invoking them is used as a promise
       * so we can wait on all dependencies to load.
       * @param {Object} resolves
       * @returns {Object}
       */
      return function getResolvePromises (resolves) {
        resolves = resolves || {};

        return Object.keys(resolves).reduce(function promisfyResolves (obj, key) {
          var value = resolves[key];

          var isAngularAnnotation = (Array.isArray(value) && typeof _.last(value) === 'function');

          if (typeof value === 'function' || isAngularAnnotation)
            obj[key] = $q.when($injector.invoke(value));
          else if (_.isPlainObject(value) || Array.isArray(value))
            obj[key] = $q.all(value);

          return obj;
        }, {});
      };
    }]);
}());

