describe('PDSH directive', function () {
  'use strict';

  var $scope, $timeout, element, inputField, groupAddOn, help, node;

  beforeEach(module('pdsh-module', 'templates', 'ui.bootstrap', function initialize ($provide) {
    help = {
      get: jasmine.createSpy('get').andReturn('Enter hostname / hostlist expression.')
    };

    $provide.value('help', help);
  }));

  describe('General operation', function () {

    beforeEach(inject(function ($templateCache, $rootScope, $compile, _$timeout_) {
      $timeout = _$timeout_;

      // Create an instance of the element
      element = angular.element($templateCache.get('pdsh.html'));

      $scope = $rootScope.$new();
      $scope.pdshChange = jasmine.createSpy('pdshChange');

      node = $compile(element)($scope);

      // Update the html
      $scope.$digest();

      inputField = element.find('.form-control');
      groupAddOn = element.find('.input-group-addon');
    }));

    describe('successful entry', function () {
      var hostnames;

      beforeEach(function () {
        runs(function () {
          inputField.val('hostname[1-3]');
          inputField.trigger('input');
        });

        waitsFor(function () {
          return element.scope().pdshForm.pdsh.$viewValue === 'hostname[1-3]' &&
            element.scope().pdshForm.pdsh.$valid === true;
        }, 'The view value isn\'t hostname[1-3] or element is not valid yet due to async call.', 1000);
      });

      it('should not show the error tooltip', function () {
        expect(element.find('.error-tooltip li').length).toEqual(0);
      });

      it('should call pdshChange', function () {
        expect($scope.pdshChange).toHaveBeenCalled();
      });

      describe('expression popover', function () {
        var popover;
        beforeEach(function () {
          groupAddOn.click();
          $timeout.flush();

          popover = element.find('.popover li');
          hostnames = _.reduce(popover,
            function convertHostnamesToString (prev, next) {
              var separator = (prev === '') ? '' : ',';
              return prev + separator + next.innerHTML;
            }, '');
        });

        it('should display the popover', function () {
          expect(popover).toBeShown();
        });

        it('should contain the hostnames in the popover', function () {
          expect(hostnames).toEqual('<span bo-text="hostname"></span>');
        });
      });
    });

    describe('unsuccessful entry', function () {

      beforeEach(function () {
        runs(function () {
          inputField.val('hostname[1-]');
          inputField.trigger('change');
        });

        waitsFor(function () {
          return element.scope().pdshForm.pdsh.$viewValue === 'hostname[1-]';
        }, 'The expression should have changed', 1000);
      });

      describe('group add on', function () {
        beforeEach(function () {
          groupAddOn.click();
          $timeout.flush();
        });

        it('should not display the popover', function () {
          expect(element.find('.popover')).toBeHidden();
        });

        it('should show the error tooltip', function () {
          var tooltip = element.find('.error-tooltip li');
          expect(tooltip.length).toEqual(1);
        });
      });
    });

    describe('empty entry', function () {
      beforeEach(function () {
        runs(function () {
          inputField.val('');
          inputField.trigger('input');
          groupAddOn.click();
        });

        waitsFor(function () {
          return $scope.pdshChange.calls.length === 3;
        }, 'The expression should have changed', 1000);
      });

      it('should not display the popover', function () {
        expect(element.find('.popover')).toBeHidden();
      });

      it('should show the error tooltip', function () {
        var tooltip = element.find('.error-tooltip li');
        expect(tooltip.length).toEqual(0);
      });

      it('should have a placeholder', function () {
        expect(inputField.attr('placeholder')).toEqual('placeholder text');
      });
    });

    describe('initial entry', function () {
      it('should have an initial value of \'invalid[\'', function () {
        expect(node.find('input').val()).toEqual('invalid[');
      });

      it('should display the error tooltip', function () {
        expect(node.find('.error-tooltip')).toBeShown();
      });
    });
  });

  describe('pdsh initial change', function () {

    var initialValue;

    beforeEach(module('pdsh-module', 'templates'));

    beforeEach(inject(function ($rootScope, $compile) {
      initialValue = 'storage0.localdomain';

      // Create an instance of the element
      element = angular.element('<form name="pdshForm"><pdsh pdsh-initial="\'' + initialValue + '\'" ' +
        'pdsh-change="pdshChange(pdsh, hostnames)"></pdsh></form>');

      $scope = $rootScope.$new();
      $scope.pdshChange = jasmine.createSpy('pdshChange');

      node = $compile(element)($scope);

      // Update the html
      $scope.$digest();

      inputField = element.find('.form-control');
    }));

    it('should call help.get', function () {
      expect(help.get).toHaveBeenCalledOnceWith('pdsh_placeholder');
    });

    it('should have a placeholder', function () {
      expect(inputField.attr('placeholder')).toEqual('Enter hostname / hostlist expression.');
    });

    it('should trigger a change for the initial value', function () {
      expect($scope.pdshChange).toHaveBeenCalledWith(initialValue, [initialValue]);
    });

    describe('modify existing value after throttle', function () {
      beforeEach(function () {
        var flag = false;
        waitsFor(function () {
          setTimeout(function () {
            inputField.val('storage[1-10].localdomain');
            inputField.trigger('input');
            flag = true;
          }, 600);

          return flag;

        }, 'The expression should have changed', 5000);
      });

      it('should call pdshChange with storage[1-10].localdomain', function () {
        expect($scope.pdshChange.calls[$scope.pdshChange.calls.length - 1].args[0])
          .toEqual('storage[1-10].localdomain');
      });
    });
  });
});
