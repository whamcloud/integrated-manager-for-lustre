describe('PDSH directive', function () {
  'use strict';

  var $scope, $timeout, element, inputField, groupAddOn, help, node, throttleParseExpression;

  beforeEach(module('pdsh-module', 'templates', 'ui.bootstrap', function initialize ($provide) {
    help = {
      get: jasmine.createSpy('get').andReturn('Enter hostname / hostlist expression.')
    };

    throttleParseExpression = jasmine.createSpy('throttleExpression');

    _.throttle = jasmine.createSpy('throttle').andReturn(throttleParseExpression);

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
        inputField.val('hostname[1-3]');
        inputField.trigger('change');

        $scope.$$childHead.pdsh.parseExpression('hostname[1-3]');
        $scope.$digest();

        groupAddOn.click();
        $timeout.flush();
        hostnames = _.reduce(element.find('.popover li'),
          function convertHostnamesToString (prev, next) {
            var separator = (prev === '') ? '' : ',';
            return prev + separator + next.innerHTML;
          }, '');
      });

      it('should call _.throttle', function () {
        expect(_.throttle).toHaveBeenCalledWith(jasmine.any(Function), 500);
      });

      it('should call throttleParseExpression', function () {
        expect(throttleParseExpression).toHaveBeenCalled();
      });

      it('should display the popover', function () {
        expect(element.find('.popover')).toBeShown();
      });

      it('should contain the hostnames in the popover', function () {
        expect(hostnames).toEqual('<span bo-text="hostname"></span>');
      });

      it('should not show the error tooltip', function () {
        var tooltip = element.find('.error-tooltip li');
        expect(tooltip.length).toEqual(0);
      });

      it('should call pdshChange', function () {
        expect($scope.pdshChange).toHaveBeenCalled();
      });
    });

    describe('unsuccessful entry', function () {
      beforeEach(function () {
        inputField.val('hostname[1-]');
        inputField.trigger('change');
        $scope.$$childHead.pdsh.parseExpression('hostname[1-]');
        $scope.$digest();

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

    describe('empty entry', function () {
      beforeEach(function () {
        inputField.val('');
        inputField.trigger('change');
        groupAddOn.click();
        $timeout.flush();
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

      $scope.$$childHead.pdsh.parseExpression(initialValue);

      inputField = element.find('.form-control');
    }));

    it('should call help.get', function () {
      expect(help.get).toHaveBeenCalledOnceWith('pdsh_placeholder');
    });

    it('should have a placeholder', function () {
      expect(inputField.attr('placeholder')).toEqual('Enter hostname / hostlist expression.');
    });

    it('should trigger a change for the initial value', function () {
      expect($scope.pdshChange).toHaveBeenCalledOnceWith(initialValue, [initialValue]);
    });
  });
});
