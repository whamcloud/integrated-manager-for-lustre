describe('Steps module', function () {
  'use strict';

  beforeEach(module('steps-module'));
  beforeEach(module('templates'));

  beforeEach(module(function ($provide) {
    $provide.factory('foo', function () {
      return 'bar';
    });
  }));

  var $rootScope, $templateCache, $scope, $q, $compile, $http, $httpBackend, $timeout, stepsManager, getResolvePromises;

  describe('steps module', function () {
    beforeEach(inject(function (_$rootScope_, _$templateCache_, _$compile_, _$q_, _stepsManager_,
                                _getResolvePromises_, _$http_, _$httpBackend_, _$timeout_) {
      $rootScope = _$rootScope_;
      $templateCache = _$templateCache_;
      $compile = _$compile_;
      $q = _$q_;
      $timeout = _$timeout_;
      $http = _$http_;
      $httpBackend = _$httpBackend_;
      $scope = $rootScope.$new();
      getResolvePromises = _getResolvePromises_;
      stepsManager = _stepsManager_;
    }));

    describe('step container', function () {
      var element, node;

      beforeEach(function () {
        element = angular.element('<step-container manager="manager"></step-container>');

        $scope.manager = stepsManager();

        $templateCache.put('assets/html/step', '<div>{{foo}}</div>');

        $scope.manager.addStep('step', {
          templateUrl: 'assets/html/step',
          controller: function ($scope) {
            $scope.foo = 'bar';
          },
          transition: function transition () {}
        });
      });

      describe('directive when all promises are resolved', function () {
        beforeEach(function () {
          node = $compile(element)($scope);

          $scope.$digest();
        });

        it('should start empty', function () {
          expect(node.html()).toEqual('');
        });

        it('should populate with the step on start.', function () {
          $scope.manager.start('step');

          $scope.$digest();

          expect(node.html()).toEqual('<div class="ng-binding ng-scope">bar</div>');
        });
      });


      describe('directive before all promises have resolved', function () {
        beforeEach(function () {
          $templateCache.put('assets/html/waitingStep', '<div>waiting</div>');

          $scope.manager.addWaitingStep({
            templateUrl: 'assets/html/waitingStep',
            controller: function ($scope) {
              $scope.foo = 'bar';
            },
            transition: function transition () {}
          });

          node = $compile(element)($scope);
        });

        it('should load the waiting template', function () {
          var deferred = $q.defer();
          var resolves = {
            resolve1: deferred.promise
          };

          $scope.manager.start('step', resolves);

          $scope.$digest();

          expect(node.html()).toEqual('<div class="ng-scope">waiting</div>');
        });
      });
    });

    describe('steps manager', function () {
      var stepsManagerInstance, waitingStep;

      beforeEach(function () {
        stepsManagerInstance = stepsManager();
        waitingStep = {
          templateUrl: 'iml/server/assets/html/wait-until-loaded-step.html'
        };
      });

      it('should return the expected interface', function () {
        expect(stepsManagerInstance).toEqual({
          addWaitingStep: jasmine.any(Function),
          addStep: jasmine.any(Function),
          start: jasmine.any(Function),
          transition: jasmine.any(Function),
          registerChangeListener: jasmine.any(Function),
          setState: jasmine.any(Function),
          getState: jasmine.any(Function),
          destroy: jasmine.any(Function),
          result: {
            end: {
              then: jasmine.any(Function),
              catch: jasmine.any(Function),
              finally: jasmine.any(Function)
            }
          }
        });
      });

      describe('calling addWaitingStep multiple times', function () {
        var error;
        beforeEach(function () {
          try {
            stepsManagerInstance.addWaitingStep(waitingStep)
              .addWaitingStep(waitingStep);
          } catch (e) {
            error = e;
          }
        });

        it('should throw an error when addWaitingStep is called twice', function () {
          expect(error.message).toEqual('Cannot assign the waiting step as it is already defined.');
        });
      });

      describe('interacting', function () {
        var listener, step1, step2;

        beforeEach(function () {
          listener = jasmine.createSpy('listener');

          step1 = {
            templateUrl: 'assets/html/step1',
            controller: 'Step1Ctrl',
            transition: function transition ($q, $transition) {
              var deferred = $q.defer();

              deferred.resolve({
                step: $transition.steps.step2
              });

              return deferred.promise;
            }
          };

          step2 = {
            templateUrl: 'assets/html/step2',
            controller: 'Step2Ctrl',
            transition: function transition ($q, $transition) {
              var deferred = $q.defer();

              deferred.resolve({
                step: $transition.steps.step1
              });

              return deferred.promise;
            }
          };

          stepsManagerInstance
            .addWaitingStep(waitingStep)
            .addStep('step1', step1)
            .addStep('step2', step2)
            .registerChangeListener(listener)
            .start('step1');
        });

        it('should start on step1', function () {
          expect(listener).toHaveBeenCalledOnceWith(step1, undefined, waitingStep);
        });

        it('should transition to step2', function () {
          stepsManagerInstance.transition();

          $rootScope.$digest();

          expect(listener).toHaveBeenCalledOnceWith(step2, undefined);
        });

        it('should transition back to step1', function () {
          stepsManagerInstance.transition();

          $rootScope.$digest();

          stepsManagerInstance.transition();

          $rootScope.$digest();

          expect(listener).toHaveBeenCalledOnceWith(step1, undefined, waitingStep);
          expect(listener).toHaveBeenCalledOnceWith(step1, undefined);
        });

        it('should destroy a listener', function () {
          stepsManagerInstance.destroy();

          stepsManagerInstance.transition();

          $rootScope.$digest();

          expect(listener).not.toHaveBeenCalledOnceWith(step2, undefined, waitingStep);
        });

        it('should save step state', function () {
          stepsManagerInstance.setState({ foo: 'bar' });

          stepsManagerInstance.transition();

          $rootScope.$digest();

          stepsManagerInstance.transition();

          $rootScope.$digest();

          expect(stepsManagerInstance.getState()).toEqual({ foo: 'bar' });
        });

        describe('end', function () {
          beforeEach(function () {
            spyOn(step1.transition, 'apply').andCallThrough();

            stepsManagerInstance.transition();

            $rootScope.$digest();

            step1.transition.apply.mostRecentCall.args[1][1].end({ foo: 'bar' });
          });

          it('should resolve the deferred with data', function () {
            stepsManagerInstance.result.end.then(function (data) {
              expect(data).toEqual({ foo: 'bar' });
            });

            $rootScope.$digest();
          });
        });
      });
    });

    describe('get resolve promises', function () {
      var promises, resolve, plainObjectPromises;

      beforeEach(function () {
        resolve = jasmine.createSpy('resolve');

        promises = getResolvePromises({
          baz: ['foo', resolve]
        });

        plainObjectPromises = getResolvePromises({
          baz: {name: 'netneutrality'}
        });
      });

      it('should return an object of promises', function () {
        expect(promises.baz).toEqual({
          then: jasmine.any(Function),
          catch: jasmine.any(Function),
          finally: jasmine.any(Function)
        });
      });

      it('should return an object of promises on plain object', function () {
        expect(plainObjectPromises.baz).toEqual({
          then: jasmine.any(Function),
          catch: jasmine.any(Function),
          finally: jasmine.any(Function)
        });
      });

      it('should invoke resolves with dependencies', function () {
        $q.all(promises).then(function () {
          expect(resolve).toHaveBeenCalledOnceWith('bar');
        });

        $rootScope.$digest();
      });

      it('should invoke resolves with dependencies on plain object promise', function () {
        $q.all(plainObjectPromises).then(function () {
          expect(resolve).toHaveBeenCalledOnceWith('bar');
        });

        $rootScope.$digest();
      });

      it('should resolve with plain object', function () {
        $q.all(plainObjectPromises).then(function (data) {
          expect(data).toEqual({baz: {name: 'netneutrality'}});
        });

        $rootScope.$digest();
      });
    });
  });
});
