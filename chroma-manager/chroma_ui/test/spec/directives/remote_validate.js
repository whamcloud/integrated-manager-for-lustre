describe('Remote Validate Directive', function () {
  'use strict';

  var controller;
  var locals;
  var formControllerSpy;
  var templateLocation = 'test/templates/remote-validate.html';

  function createComponent(name) {
    return jasmine.createSpyObj(name, ['$setValidity']);
  }

  beforeEach(module('services', templateLocation, 'directives'));

  beforeEach(inject(function ($controller, $rootScope, remoteValidateFormService) {
    locals = {
      $scope: $rootScope.$new(),
      $element: {
        controller: function () {
          formControllerSpy = createComponent('formController');
          return formControllerSpy;
        }
      }
    };

    controller = $controller(remoteValidateFormService.controller, locals);
  }));

  describe('Remote validate form directive', function () {
    it('should return a configuration object', inject(function (remoteValidateFormService) {
      expect(remoteValidateFormService).toEqual(jasmine.any(Object));
      expect(remoteValidateFormService.link).toEqual(jasmine.any(Function));
      expect(remoteValidateFormService.controller).toBeDefined();
    }));

    describe('testing the controller', function () {
      it('should register components', function () {
        expect(controller.registerComponent).toEqual(jasmine.any(Function));

        var obj = {};
        controller.registerComponent('foo', obj);

        expect(controller.components.foo).toBe(obj);
      });

      it('should get components', function () {
        expect(controller.getComponent).toEqual(jasmine.any(Function));

        var obj = {};
        controller.registerComponent('foo', obj);

        expect(controller.getComponent('foo')).toBe(obj);
        expect(controller.getComponent('bar')).toBeUndefined();
      });

      it('should reset components validity', function () {
        expect(controller.resetComponentsValidity).toEqual(jasmine.any(Function));

        locals.$scope.serverValidationError = {
          foo: ['bar']
        };

        var obj = createComponent('obj');
        controller.registerComponent('foo', obj);

        controller.resetComponentsValidity();

        expect(formControllerSpy.$setValidity).toHaveBeenCalledWith('server', true);

        expect(obj.$setValidity).toHaveBeenCalledWith('server', true);
        expect(locals.$scope.serverValidationError.foo).toBeUndefined();
      });

      it('should have the form registered as a component', function () {
        expect(controller.getComponent('__all__')).toBe(formControllerSpy);
      });
    });

    describe('testing the linking function', function () {
      var deferred;

      beforeEach(inject(function ($q, remoteValidateFormService) {
        deferred = $q.defer();

        controller.registerComponent('foo', createComponent('foo'));
        controller.registerComponent('bar', createComponent('bar'));

        remoteValidateFormService.link(locals.$scope, locals.$element, {remoteThen: 'then'}, controller);

        // Make sure the $watch fires.
        locals.$scope.$apply();

        locals.$scope.then = deferred.promise.then;
      }));

      it('should mark components with validation errors', function () {
        expect(controller.getComponent('foo').$setValidity).not.toHaveBeenCalled();
        expect(controller.getComponent('bar').$setValidity).not.toHaveBeenCalled();

        deferred.reject({
          data: {
            foo: ['Required Field']
          }
        });

        locals.$scope.$apply();

        expect(controller.getComponent('foo').$setValidity).toHaveBeenCalledWith('server', false);
        expect(locals.$scope.serverValidationError.foo).toEqual(['Required Field']);

        expect(controller.getComponent('bar').$setValidity).not.toHaveBeenCalledWith('server', false);
      });

      it('should reset validity when the component has no errors', function () {
        expect(controller.getComponent('foo').$setValidity).not.toHaveBeenCalled();

        locals.$scope.serverValidationError.foo = ['blah'];

        deferred.resolve();

        locals.$scope.$apply();

        expect(controller.getComponent('foo').$setValidity).toHaveBeenCalledWith('server', true);
        expect(locals.$scope.serverValidationError.foo).toBeUndefined();
      });

      it('should map the __all__ property to the form itself', function () {
        expect(formControllerSpy.$setValidity).not.toHaveBeenCalled();

        deferred.reject({
          data: {
            __all__: 'Missing some info.'
          }
        });
        locals.$scope.$apply();

        expect(formControllerSpy.$setValidity).toHaveBeenCalledWith('server', true);
        expect(locals.$scope.serverValidationError.__all__).toEqual(['Missing some info.']);
      });
    });
  });

  describe('Remote validate form component directive', function () {
    it('should return a configuration object', inject(function (remoteValidateComponentService) {
      expect(remoteValidateComponentService).toEqual(jasmine.any(Object));
      expect(remoteValidateComponentService.link).toEqual(jasmine.any(Function));
    }));

    it('should register it\'s model onto the form controller',
      inject(function (remoteValidateComponentService, $rootScope) {
        var controllers = [controller, jasmine.createSpy('ngModel')];
        var scope = $rootScope.$new();
        var attrs = {name: 'foo'};

        remoteValidateComponentService.link(scope, {}, attrs, controllers);

        expect(controller.getComponent('foo')).toBe(controllers[1]);
      })
    );
  });

  describe('testing the directive set', function () {
    var scope;
    var form;
    var getDeferred;

    beforeEach(inject(function ($rootScope, $compile, $templateCache, $q) {
      form = angular.element($templateCache.get(templateLocation));

      scope = $rootScope.$new();
      $compile(form)(scope);
      scope.$digest();

      getDeferred = function () {
        var deferred = $q.defer();
        scope.then = deferred.promise.then;

        return deferred;
      };

    }));

    it('should validate fields', function () {
      getDeferred().reject({
        data: {
          __all__: 'uh-oh',
          foo: 'Missing some info.',
          bar: 'Missing some info.'
        }
      });
      scope.$apply();

      expect(form).toBeInvalid();
      expect(form).toHaveClass('ng-invalid-server');

      expect(form.find('ul')).not.toBe('');

      expect(form.find('ul').find('li').length).toBe(1);
      expect(form.find('ul').find('li').html()).toEqual('uh-oh');

      expect(form.find('input')).toBeInvalid();
      expect(form.find('input')).toHaveClass('ng-invalid-server');

      expect(form.find('select')).toBeInvalid();
      expect(form.find('select')).toHaveClass('ng-invalid-server');

      getDeferred().resolve();
      scope.$apply();

      expect(form).toBeValid();

      expect(form.find('ul').length).toBe(0);

      expect(form.find('input')).toBeValid();
      expect(form.find('input')).not.toHaveClass('ng-invalid-server');

      expect(form.find('select')).toBeValid();
      expect(form.find('select')).not.toHaveClass('ng-invalid-server');
    });
  });
});

