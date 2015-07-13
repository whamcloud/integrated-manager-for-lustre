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


(function () {
  'use strict';

  angular.module('steps-module', [])
    .directive('stepContainer', ['$q', '$controller', '$http', '$templateCache', '$compile',
      function stepContainerDirective ($q, $controller, $http, $templateCache, $compile) {
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
             * @param {Object} [resolves]
             * @param {Object} [waitingStep]
             */
            scope.manager.registerChangeListener(function onChanges (step, resolves, waitingStep) {
              if (!resolvesFinished && waitingStep && waitingStep.templateUrl) {
                // Create new scope
                innerScope = scope.$new();

                getTemplatePromise(waitingStep.templateUrl)
                  .then(function loadUntilTemplate (template) {
                    // Make sure the resolves haven't finished before loading the template
                    if (!resolvesFinished)
                      loadUpSteps({ $scope: innerScope }, el, template, waitingStep.controller);
                  });
              }

              resolves = scope.manager.onEnter(resolves);
              resolves.template = getTemplatePromise(step.templateUrl);

              $q.all(resolves)
                .then(function (results) {
                  var template = results.template;
                  delete results.template;

                  // Indicate that resolves are complete so the untilTemplate isn't loaded
                  resolvesFinished = true;

                  if (innerScope)
                    innerScope.$destroy();

                  results.$scope = innerScope = scope.$new();
                  results.$stepInstance = {
                    transition: scope.manager.transition,
                    end: scope.manager.end
                  };

                  loadUpSteps(results, el, template, step.controller);
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
          return $http.get(templateUrl, { cache: $templateCache })
            .then(function (result) {
              return result.data;
            });
        }
      }
    ])
    .factory('stepsManager', ['$q', '$injector',
      function stepManagerFactory ($q, $injector) {
        return function stepManager () {
          var currentStep, listener, pending;
          var steps = {};
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
              currentStep = steps[stepName];

              if (listener)
                listener(steps[stepName], extraResolves, steps.waitingStep);
              else
                pending = {
                  step: steps[stepName],
                  extraResolves: extraResolves
                };

              return this;
            },
            end: function end (data) {
              endDeferred.resolve(data);
            },
            /**
             * Called before entering a new step.
             * Has the ability to pend until the step is ready.
             * @param {Object} [resolves]
             * @returns {Object} A promise.
             */
            onEnter: function onEnter (resolves) {
              resolves = resolves || {};

              if (currentStep.onEnter)
                return $injector.invoke(currentStep.onEnter, null, resolves);
              else
                return resolves;
            },
            /**
             * Performs a transition from one step to another
             * @param {String} action
             * @param {Object} resolves
             */
            transition: function transition (action, resolves) {
              if (!currentStep)
                return;

              var nextStep = currentStep.transition(steps, action);

              if (nextStep) {
                currentStep = nextStep;
                listener(nextStep, resolves);
              }
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
             * Cleans all references.
             */
            destroy: function destroy () {
              listener = steps = currentStep = pending = null;
            },
            result: {
              end: endDeferred.promise
            }
          };
        };
      }
    ]);
}());
