describe('exception modal', function () {
  'use strict';

  beforeEach(module('exception'));

  mock.beforeEach('$modal');

  it('should call the modal with the expected params', inject(function (exceptionModal, $modal) {
    exceptionModal();

    expect($modal.open).toHaveBeenCalledWith({
      backdrop: 'static',
      windowClass: 'exception-modal',
      keyboard: false,
      controller: 'ExceptionModalCtrl',
      template: jasmine.any(String)
    });
  }));
});
