describe('disconnect dialog', function () {
  'use strict';

  beforeEach(module('exception'));

  mock.beforeEach('$dialog');

  it('should call the dialog with the expected params', inject(function (disconnectDialog, $dialog) {
    expect($dialog.dialog).toHaveBeenCalledWith({
      dialogFade: true,
      backdropClick: false,
      dialogClass: 'modal disconnect-dialog',
      keyboard: false,
      template: jasmine.any(String)
    });
  }));
});
