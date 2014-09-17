describe('Override Directive', function () {
  'use strict';

  beforeEach(module('server', 'templates', 'ui.bootstrap.dropdown'));

  var $scope, element;

  beforeEach(inject(function ($rootScope, $compile) {
    var markup = '<override-button overridden="overridden" is-valid="isValid" on-change="onChange(message)" \
is-disabled="disabled"></override-button>';

    $scope = $rootScope.$new();

    $scope.onChange = jasmine.createSpy('onChange');

    element = angular.element(markup);
    $compile(element)($scope);

    $scope.$digest();
  }));

  it('should start with the override button', function () {
    expect(element.find('button').text().trim()).toEqual('Override');
  });

  it('should transition to proceed after clicking override', function () {
    element.find('button')[0].click();

    expect(element.find('button').eq(0).text().trim()).toEqual('Proceed');
  });

  it('should have a link to skip the command view', function () {
    element.find('button')[0].click();
    element.find('button').eq(1)[0].click();

    element.find('.dropdown-menu a')[0].click();

    expect($scope.onChange).toHaveBeenCalledOnceWith('proceed and skip');
  });

  it('should not override if valid', function () {
    $scope.isValid = true;
    $scope.$digest();

    expect(element.find('button').eq(0)).toHaveClass('btn-success');
  });

  it('should tell that override was clicked', function () {
    element.find('button')[0].click();

    expect($scope.onChange).toHaveBeenCalledOnceWith('override');
  });

  it('should tell that proceed was clicked', function () {
    element.find('button')[0].click();
    element.find('button').eq(0)[0].click();

    expect($scope.onChange).toHaveBeenCalledOnceWith('proceed');
  });

  it('should be disabled after proceeding', function () {
    element.find('button')[0].click();
    element.find('button').eq(0)[0].click();

    expect(element.find('button').text().trim()).toEqual('Working');
  });
});
