describe('disconnect dialog', function () {
  'use strict';

  var disconnectDialog, $dialog, $window, dialogOpen;

  beforeEach(module('exception', function ($provide) {
    $window = {
      addEventListener: jasmine.createSpy('$window.addEventListener')
    };

    $provide.value('$window', $window);

    dialogOpen = jasmine.createSpy('$dialog.dialog.open');

    $dialog = {
      dialog: jasmine.createSpy('$dialog.dialog').and.returnValue({
        open: dialogOpen
      })
    };

    $provide.value('$dialog', $dialog);
  }));

  beforeEach(inject(function (_disconnectDialog_, _$dialog_) {
    disconnectDialog = _disconnectDialog_;
    $dialog = _$dialog_;
  }));

  it('should call the dialog with the expected params', function () {
    expect($dialog.dialog).toHaveBeenCalledWith({
      dialogFade: false,
      backdropFade: false,
      backdropClick: false,
      dialogClass: 'modal disconnect-modal',
      keyboard: false,
      template: jasmine.any(String)
    });
  });

  it('should add an unload event listener to window', function () {
    expect($window.addEventListener).toHaveBeenCalledWith('beforeunload', jasmine.any(Function));
  });

  it('should call the original open listener', function () {
    disconnectDialog.open();

    expect(dialogOpen).toHaveBeenCalledTimes(1);
  });

  it('should not open the modal if window has unloaded', function () {
    var cb = $window.addEventListener.calls.mostRecent().args[1];

    cb();
    disconnectDialog.open();

    expect(dialogOpen).not.toHaveBeenCalledTimes(1);
  });
});
