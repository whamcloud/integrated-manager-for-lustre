describe('Full Screen Module', function () {
  'use strict';

  var $scope, $fullScreenController, fullScreenContainer, button, icon, body, spy;

  beforeEach(module('fullScreen', 'templates'));

  beforeEach(inject(function ($rootScope, $templateCache, $compile) {
    $scope = $rootScope.$new();

    fullScreenContainer = angular.element($templateCache.get('full-screen.html'));

    $compile(fullScreenContainer)($scope);
    $scope.$digest();

    $fullScreenController = fullScreenContainer.inheritedData('$fullScreenController');

    spy = jasmine.createSpy('listener');

    button = fullScreenContainer.find('button');
    icon = button.find('i');
    body = angular.element('body');

    $fullScreenController.addListener(spy);
  }));

  it('should show the open icon', function () {
    expect(icon).toHaveClass('fa-expand');
  });

  it('should show the open text', function () {
    expect(button.text().trim()).toEqual('Full Screen');
  });

  it('should expose a controller method to remove the listener', function () {
    $fullScreenController.removeListener(spy);

    button.click();
    $scope.$digest();

    expect(spy.callCount).toBe(0);
  });

  describe('entering full screen', function () {
    beforeEach(function () {
      button.click();
      $scope.$digest();
    });

    it('should show the close icon', function () {
      expect(icon).toHaveClass('fa-compress');
    });

    it('should show the close text', function () {
      expect(button.text().trim()).toEqual('Exit Full Screen');
    });

    it('should add the active class to the container', function () {
      expect(fullScreenContainer).toHaveClass('active');
    });

    it('should call the listener with true', function () {
      expect(spy).toHaveBeenCalledOnceWith(true);
    });

    it('should add the full screen class to the body', function () {
      expect(body).toHaveClass('full-screen-container');
    });

    describe('exiting full screen', function () {
      beforeEach(function () {
        button.click();
        $scope.$digest();
      });

      it('should show the open icon', function () {
        expect(icon).toHaveClass('fa-expand');
      });

      it('should show the open text', function () {
        expect(button.text().trim()).toEqual('Full Screen');
      });

      it('should not have the active class on the container', function () {
        expect(fullScreenContainer).not.toHaveClass('active');
      });

      it('should call the listener with false', function () {
        expect(spy).toHaveBeenCalledWith(false);
      });

      it('should remove the full screen class to the body', function () {
        expect(body).not.toHaveClass('full-screen-container');
      });
    });
  });
});
