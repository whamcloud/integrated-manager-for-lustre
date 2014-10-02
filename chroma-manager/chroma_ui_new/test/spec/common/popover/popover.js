describe('popover', function () {
  'use strict';

  var $window, $timeout, $scope, template, popover, button;

  beforeEach(module('iml-popover', 'templates'));

  beforeEach(inject(function ($templateCache, $rootScope, $compile, _$window_, _$timeout_) {
    $timeout = _$timeout_;

    template = angular.element($templateCache.get('popover.html'));

    $scope = $rootScope.$new();

    $scope.workFn = jasmine.createSpy('workFn');
    $scope.onToggle = jasmine.createSpy('onToggle');

    $compile(template)($scope);

    $scope.$digest();

    $window = _$window_;

    button = template.find('a');
  }));

  it('should be not render before opening', function () {
    expect(template.find('.popover').length).toBe(0);
  });

  describe('open', function () {
    beforeEach(function () {
      button.click();
      $timeout.flush();

      popover = template.find('.popover');
    });

    afterEach(function () {
      popover.remove();
    });

    it('should display when the button is clicked', function () {
      expect(popover).toHaveClass('in');
    });

    it('should call scope.onToggle and set state to open', function () {
      expect($scope.onToggle).toHaveBeenCalledOnceWith('opened');
    });

    it('should hide when button is clicked twice', function () {
      button.click();
      $timeout.flush();

      expect(popover).not.toHaveClass('in');
    });

    it('should call scope.onToggle and set the state to closed', function () {
      button.click();
      $timeout.flush();

      expect($scope.onToggle).toHaveBeenCalledOnceWith('closed');
    });

    it('should hide when window is clicked', function () {
      angular.element($window).click();
      $timeout.flush();

      expect(popover).not.toHaveClass('in');
    });

    it('should not hide when the popover is clicked', function () {
      popover.appendTo(document.body);

      popover.click();

      expect(popover).toHaveClass('in');
    });

    it('should not hide when a child of the popover is clicked', function () {
      popover.appendTo(document.body);

      popover.find('button').click();

      expect(popover).toHaveClass('in');
    });

    it('should provide a work function', function () {
      expect($scope.workFn).toHaveBeenCalledWith(jasmine.any(Object));
    });
  });
});
