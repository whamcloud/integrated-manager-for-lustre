describe('popover', function () {
  'use strict';

  var template, $scope, popover, button, $window;

  beforeEach(module('iml-popover', 'templates'));

  beforeEach(inject(function ($templateCache, $rootScope, $compile, _$window_) {
    template = angular.element($templateCache.get('popover.html'));

    $scope = $rootScope.$new();

    $scope.workFn = jasmine.createSpy('workFn');

    $compile(template)($scope);

    $scope.$digest();

    $window = _$window_;

    popover = template.find('.popover');
    button = template.find('a');
  }));

  afterEach(function () {
    popover.remove();
  });

  it('should be hidden to start', function () {
    expect(popover).not.toHaveClass('in');
  });

  it('should display when the button is clicked', function () {
    button.click();

    expect(popover).toHaveClass('in');
  });

  it('should hide when button is clicked twice', function () {
    button.click().click();

    expect(popover).not.toHaveClass('in');
  });

  it('should hide when window is clicked', function () {
    button.click();

    angular.element($window).click();

    expect(popover).not.toHaveClass('in');
  });

  it('should not hide when the popover is clicked', function () {
    button.click();

    popover.appendTo(document.body);

    popover.click();

    expect(popover).toHaveClass('in');
  });

  it('should not hide when a child of the popover is clicked', function () {
    button.click();

    popover.appendTo(document.body);

    popover.find('button').click();

    expect(popover).toHaveClass('in');
  });

  it('should provide a work function', function () {
    expect($scope.workFn).toHaveBeenCalledWith(jasmine.any(Object));
  });
});
