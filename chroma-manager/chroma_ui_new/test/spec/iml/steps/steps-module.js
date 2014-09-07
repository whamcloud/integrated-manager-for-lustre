describe('Steps module', function () {
  'use strict';

  beforeEach(module('steps-module'));

  describe('step container', function () {
    var $scope, element, node;

    beforeEach(module('templates'));

    beforeEach(inject(function ($rootScope, $compile, $templateCache, _stepsManager_) {
      element = angular.element('<step-container manager="manager"></step-container>');

      $scope = $rootScope.$new();

      $scope.manager = _stepsManager_();

      $templateCache.put('assets/html/step', '<div>{{foo}}</div>');

      $scope.manager.addStep('step', {
        templateUrl: 'assets/html/step',
        controller: function ($scope) {
          $scope.foo = 'bar';
        },
        transition: function transition () {}
      });

      node = $compile(element)($scope);

      $scope.$digest();
    }));

    it('should start empty', function () {
      expect(node.html()).toEqual('');
    });

    it('should populate with the step on start.', function () {
      $scope.manager.start('step');

      $scope.$digest();

      expect(node.html()).toEqual('<div class="ng-binding ng-scope">bar</div>');
    });
  });

  describe('steps manager', function () {
    var stepsManager, $rootScope;

    beforeEach(inject(function (_$rootScope_, _stepsManager_) {
      stepsManager = _stepsManager_();
      $rootScope = _$rootScope_;
    }));

    it('should return the expected interface', function () {
      expect(stepsManager).toEqual({
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

        stepsManager
          .addStep('step1', step1)
          .addStep('step2', step2)
          .registerChangeListener(listener)
          .start('step1');
      });

      it('should start on step1', function () {
        expect(listener).toHaveBeenCalledOnceWith(step1, undefined);
      });

      it('should transition to step2', function () {
        stepsManager.transition();

        $rootScope.$digest();

        expect(listener).toHaveBeenCalledOnceWith(step2, undefined);
      });

      it('should transition back to step1', function () {
        stepsManager.transition();

        $rootScope.$digest();

        stepsManager.transition();

        $rootScope.$digest();

        expect(listener).toHaveBeenCalledTwiceWith(step1, undefined);
      });

      it('should destroy a listener', function () {
        stepsManager.destroy();

        stepsManager.transition();

        $rootScope.$digest();

        expect(listener).not.toHaveBeenCalledOnceWith(step2, undefined);
      });

      it('should save step state', function () {
        stepsManager.setState({ foo: 'bar' });

        stepsManager.transition();

        $rootScope.$digest();

        stepsManager.transition();

        $rootScope.$digest();

        expect(stepsManager.getState()).toEqual({ foo: 'bar' });
      });

      describe('end', function () {
        beforeEach(function () {
          spyOn(step1.transition, 'apply').andCallThrough();

          stepsManager.transition();

          $rootScope.$digest();

          step1.transition.apply.mostRecentCall.args[1][1].end({ foo: 'bar' });
        });

        it('should resolve the deferred with data', function () {
          stepsManager.result.end.then(function (data) {
            expect(data).toEqual({ foo: 'bar' });
          });

          $rootScope.$digest();
        });
      });
    });
  });

  describe('get resolve promises', function () {
    var getResolvePromises;

    beforeEach(module(function ($provide) {
      $provide.factory('foo', function () {
        return 'bar';
      });
    }));

    var $rootScope, $q, promises, resolve, plainObjectPromises;

    beforeEach(inject(function (_$q_, _$rootScope_, _getResolvePromises_) {
      $q = _$q_;
      $rootScope = _$rootScope_;
      getResolvePromises = _getResolvePromises_;

      resolve = jasmine.createSpy('resolve');

      promises = getResolvePromises({
        baz: ['foo', resolve]
      });

      plainObjectPromises = getResolvePromises({
        baz: {name: 'netneutrality'}
      });
    }));

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
