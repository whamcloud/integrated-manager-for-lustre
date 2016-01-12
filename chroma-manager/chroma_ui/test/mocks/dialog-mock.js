mock.register({name: '$dialog', type: 'decorator', setup: function ($delegate) {
  'use strict';

  //Patch up the $dialog with a spy.
  var dialog = $delegate.dialog();
  var Dialog = dialog.constructor;
  Dialog.prototype = Object.getPrototypeOf(dialog);

  window.spyOn(Dialog.prototype, 'open');
  window.spyOn(Dialog.prototype, 'isOpen');
  window.spyOn(Dialog.prototype, 'close');

  $delegate.dialog = jasmine.createSpy('$dialog.dialog').and.callFake(function (opts) {
    return new Dialog(opts);
  });

  $delegate.dialog.spy = Dialog.prototype;

  return $delegate;
}});
