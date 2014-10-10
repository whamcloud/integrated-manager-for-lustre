describe('wait until add server resolves complete', function () {
  'use strict';

  beforeEach(module('server'));

  var waitUntilLoadedStep, controller, scope, $rootScope;
  beforeEach(inject(function inject (_waitUntilLoadedStep_, $controller, _$rootScope_) {
    waitUntilLoadedStep = _waitUntilLoadedStep_;
    $rootScope = _$rootScope_;
    scope = $rootScope.$new();

    controller = $controller('WaitUntilLoadedCtrl', {
      $scope: scope
    });
  }));

  describe('Wait Until Loaded Controller', function () {
    it('should emit the closeModal event', function () {
        var closeModalCalled = false;
        $rootScope.$on('addServerModal::closeModal', function updateCloseStatus () {
          closeModalCalled = true;
        });

        scope.wait.close();
        scope.$digest();
        expect(closeModalCalled).toEqual(true);
    });
  });

  describe('initialize waitUntilLoadedStep', function () {
    it('should have the templateUrl', function () {
      expect(waitUntilLoadedStep.templateUrl).toEqual('iml/server/assets/html/wait-until-loaded-step.html');
    });

    it('should have the controller specified', function () {
      expect(waitUntilLoadedStep.controller).toEqual('WaitUntilLoadedCtrl');
    });
  });
});
