describe('disconnect modal', function () {
  'use strict';

  beforeEach(module('exception', {
    windowUnload: { unloading: false }
  }));

  mock.beforeEach('$modal');

  var $modal, disconnectModal, windowUnload;

  beforeEach(inject(function (_$modal_, _disconnectModal_, _windowUnload_) {
    $modal = _$modal_;
    disconnectModal = _disconnectModal_;
    windowUnload = _windowUnload_;
  }));

  afterEach(function () {
    windowUnload.unloading = false;
  });

  it('should call the modal with the expected params', function () {
    disconnectModal();

    expect($modal.open).toHaveBeenCalledWith({
      backdrop: 'static',
      windowClass: 'disconnect-modal',
      keyboard: false,
      template: jasmine.any(String)
    });
  });


  it('should not open the modal if window has unloaded', function () {
    windowUnload.unloading = true;
    disconnectModal();

    expect($modal.open).not.toHaveBeenCalledOnce();
  });
});
