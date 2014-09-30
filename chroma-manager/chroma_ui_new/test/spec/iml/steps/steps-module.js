describe('Steps module', function () {
  'use strict';

  beforeEach(module('steps-module'));
  beforeEach(module('templates'));

  beforeEach(module(function ($provide) {
    $provide.factory('foo', function () {
      return 'bar';
    });
  }));

  var $rootScope, $templateCache, $scope, $q, $compile, $http, $httpBackend, $timeout, stepsManager;

  beforeEach(inject(function (_$rootScope_, _$templateCache_, _$compile_, _$q_, _stepsManager_,
                              _$http_, _$httpBackend_, _$timeout_) {
    $rootScope = _$rootScope_;
    $templateCache = _$templateCache_;
    $compile = _$compile_;
    $q = _$q_;
    $timeout = _$timeout_;
    $http = _$http_;
    $httpBackend = _$httpBackend_;
    $scope = $rootScope.$new();
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
        controller: function controller ($scope) {
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
          controller: function controller ($scope) {
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
        onEnter: jasmine.any(Function),
        end: jasmine.any(Function),
        transition: jasmine.any(Function),
        registerChangeListener: jasmine.any(Function),
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
          transition: function transition (steps) {
            return steps.step2;
          }
        };

        step2 = {
          templateUrl: 'assets/html/step2',
          controller: 'Step2Ctrl',
          transition: function transition (steps) {
            return steps.step1;
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
    });
  });
});
