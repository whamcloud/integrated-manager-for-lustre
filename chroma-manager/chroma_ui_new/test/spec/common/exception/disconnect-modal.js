describe('disconnect modal', function () {
  'use strict';

  beforeEach(module('exception'));

  mock.beforeEach('$modal');

  it('should call the modal with the expected params', inject(function (disconnectModal, $modal) {
    disconnectModal();

    expect($modal.open).toHaveBeenCalledWith({
      backdrop: 'static',
      windowClass: 'disconnect-modal',
      keyboard: false,
      template: jasmine.any(String)
    });
  }));
});
