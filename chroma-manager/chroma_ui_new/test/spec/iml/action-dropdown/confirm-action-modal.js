describe('confirm action modal', function () {
  'use strict';

  beforeEach(module('action-dropdown-module'));

  describe('confirm action modal', function () {
    var $modalInstance, confirmAction, title, confirmPrompts;

    beforeEach(inject(function ($rootScope, $controller) {
      var $scope = $rootScope.$new();

      $modalInstance = {
        close: jasmine.createSpy('close'),
        dismiss: jasmine.createSpy('dismiss')
      };

      title = 'The Title';
      confirmPrompts = [];

      $controller('ConfirmActionModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        confirmPrompts: confirmPrompts,
        title: title
      });

      confirmAction = $scope.confirmAction;
    }));

    it('should have a title property', function () {
      expect(confirmAction.title).toEqual('The Title');
    });

    it('should set the confirmPrompts', function () {
      expect(confirmAction.confirmPrompts).toEqual([]);
    });

    it('should have a confirm method', function () {
      expect(confirmAction.confirm).toEqual(jasmine.any(Function));
    });

    it('should close the modal when confirming', function () {
      confirmAction.confirm(true);

      expect($modalInstance.close).toHaveBeenCalledOnceWith(true);
    });

    it('should have a cancel method', function () {
      expect(confirmAction.cancel).toEqual(jasmine.any(Function));
    });

    it('should dismiss the modal on cancel', function () {
      confirmAction.cancel();

      expect($modalInstance.dismiss).toHaveBeenCalledOnceWith('cancel');
    });
  });

  describe('open confirm action modal', function () {
    var $modal, openConfirmActionModal;

    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('open')
      };

      $provide.value('$modal', $modal);
    }));

    var title, confirmPrompts;

    beforeEach(inject(function (_openConfirmActionModal_) {
      title = 'The title';
      confirmPrompts = [];

      openConfirmActionModal = _openConfirmActionModal_;
      openConfirmActionModal(title, confirmPrompts);
    }));

    it('should open the modal as expected', function () {
      expect($modal.open).toHaveBeenCalledOnceWith({
        templateUrl: 'iml/action-dropdown/assets/html/confirm-action-modal.html',
        controller: 'ConfirmActionModalCtrl',
        windowClass: 'confirm-action-modal',
        backdrop: 'static',
        resolve: {
          title: jasmine.any(Function),
          confirmPrompts: jasmine.any(Function)
        }
      });
    });

    describe('resolves', function () {
      var resolve;

      beforeEach(function () {
        resolve = $modal.open.mostRecentCall.args[0].resolve;
      });

      it('should set the title', function () {
        expect(resolve.title()).toEqual(title);
      });

      it('should set the confirm prompts', function () {
        expect(resolve.confirmPrompts()).toEqual([]);
      });
    });
  });
});
