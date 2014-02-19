describe('disconnect modal', function () {
  'use strict';

  beforeEach(module('exception'));

  mock.beforeEach('$modal', '$window');

  var disconnectModal, $window, $modal;

  beforeEach(inject(function (_disconnectModal_, _$window_, _$modal_) {
    disconnectModal = _disconnectModal_;
    $window = _$window_;
    $modal = _$modal_;
  }));

  it('should call the modal with the expected params', function () {
    disconnectModal();

    expect($modal.open).toHaveBeenCalledWith({
      backdrop: 'static',
      windowClass: 'disconnect-modal',
      keyboard: false,
      template: jasmine.any(String)
    });
  });

  it('should add an unload event listener to window', function () {
    expect($window.addEventListener).toHaveBeenCalledOnceWith('beforeunload', jasmine.any(Function));
  });

  it('should not open the modal if window has unloaded', function () {
    var cb = $window.addEventListener.mostRecentCall.args[1];

    cb();
    disconnectModal();

    expect($modal.open).not.toHaveBeenCalledOnce();
  });
});
