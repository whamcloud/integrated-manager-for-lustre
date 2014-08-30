describe('Usage picker', function () {
  'use strict';

  var $scope, template, changeUsageButton, submitButton, input, rangeAlert, requiredAlert;

  beforeEach(module('charts', 'templates'));

  beforeEach(inject(function ($templateCache, $rootScope, $compile) {
    template = angular.element($templateCache.get('usage-picker.html'));

    $scope = $rootScope.$new();
    $scope.test = {
      onUpdate: jasmine.createSpy('onUpdate')
    };

    $compile(template)($scope);

    $scope.$digest();

    changeUsageButton = template.find('.activate-popover');
    input = template.find('input');
    rangeAlert = template.find('.alert.alert-range');
    requiredAlert = template.find('.alert.alert-required');
    submitButton = template.find('.btn-success');

    changeUsageButton.click();
  }));

  it('should default to 0%', function () {
    expect(input.val()).toEqual('0');
  });

  it('should not show the range alert by default', function () {
    expect(rangeAlert).toBeHidden();
  });

  it('should not show the required alert by default', function () {
    expect(requiredAlert).toBeHidden();
  });

  it('should not allow a value greater than 100', function () {
    setInput('101');

    expect(rangeAlert).toBeShown();
  });

  it('should not allow a value less than 0', function () {
    setInput('-1');

    expect(rangeAlert).toBeShown();
  });

  it('should not allow an empty input', function () {
    setInput('');

    expect(requiredAlert).toBeShown();
  });

  it('should call the onUpdate method when the form is submitted', function () {
    setInput('50');

    submitButton.click();

    expect($scope.test.onUpdate).toHaveBeenCalledWith(50);
  });

  function setInput (value) {
    input.val(value);
    input.trigger('input');
  }
});
