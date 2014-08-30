describe('PDSH directive', function () {
  'use strict';

  var $scope, element, inputField, groupAddOn, node;

  beforeEach(module('pdsh-module', 'templates'));

  beforeEach(inject(function ($templateCache, $rootScope, $compile) {
    // Create an instance of the element
    element = angular.element($templateCache.get('pdsh.html'));

    $scope = $rootScope.$new();

    node = $compile(element)($scope);

    // Update the html
    $scope.$digest();

    $scope.$$childHead.pdshChange = jasmine.createSpy('pdshChange');

    inputField = element.find('.form-control');
    groupAddOn = element.find('.input-group-addon');
  }));

  describe('successful entry', function () {
    var hostnames;
    beforeEach(function () {
      inputField.val('hostname[1-3]');
      inputField.trigger('change');
      groupAddOn.click();
      hostnames = _.reduce(element.find('#hostnamesPopover li'),
        function convertHostnamesToString (prev, next) {
          var separator =  (prev === '') ? '' : ',';
          return prev + separator + next.innerHTML;
        }, '');
    });

    it('should display the popover', function () {
      expect(element.find('#hostnamesPopover')).toBeShown();
    });

    it('should contain the hostnames in the popover', function () {
      expect(hostnames).toEqual('hostname1,hostname2,hostname3');
    });

    it('should not show the error tooltip', function () {
      var tooltip = element.find('.error-tooltip li');
      expect(tooltip.length).toEqual(0);
    });

    it('should call pdshChange', function () {
      expect($scope.$$childHead.pdshChange).toHaveBeenCalled();
    });
  });

  describe('unsuccessful entry', function () {
    beforeEach(function () {
      inputField.val('hostname[1-]');
      inputField.trigger('change');
      groupAddOn.click();
    });

    it('should not display the popover', function () {
      expect(element.find('#hostnamesPopover')).toBeHidden();
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
    });

    it('should not display the popover', function () {
      expect(element.find('#hostnamesPopover')).toBeHidden();
    });

    it('should show the error tooltip', function () {
      var tooltip = element.find('.error-tooltip li');
      expect(tooltip.length).toEqual(0);
    });
  });
});
