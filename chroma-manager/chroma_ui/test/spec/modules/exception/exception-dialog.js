describe('exception dialog', function () {
  'use strict';

  beforeEach(module('exception'));

  mock.beforeEach('$dialog');

  it('should call the dialog with the expected params', inject(function (exceptionDialog, $dialog) {
    expect($dialog.dialog).toHaveBeenCalledWith({
      dialogFade: true,
      backdropClick: false,
      dialogClass: 'modal exception-dialog',
      keyboard: false,
      controller: 'ExceptionDialogCtrl',
      template: jasmine.any(String)
    });
  }));
});
