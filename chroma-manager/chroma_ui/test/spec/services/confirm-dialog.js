describe('Confirm Dialog', function() {
  'use strict';

  var options, dialog, confirmDialog, $dialog, $q, rejectedPromise;

  beforeEach(module('services', 'ui.bootstrap', {STATIC_URL: '/api/'}, function($provide) {
    rejectedPromise = {};
    $provide.value('$q', { reject: jasmine.createSpy('$q.reject').andReturn(rejectedPromise) });
  }));

  beforeEach(function () {
    options = {
      content: {
        title: 'Dismiss All',
        message: 'Do you wish to dismiss all status messages?',
        confirmText: 'Dismiss All',
      }
    };
  });
  mock.beforeEach('$dialog');

  beforeEach(inject(function (_$dialog_, _confirmDialog_, _$q_) {
    $dialog = _$dialog_;
    confirmDialog = _confirmDialog_;
    $q = _$q_;
  }));

  it('should return an object', function () {
    expect(confirmDialog).toEqual(jasmine.any(Object));
  });

  it('should return a dialog when setup called', function () {
    expect(confirmDialog.setup()).toEqual(jasmine.any(Object));
  });

  it('should return a dialog when setup given options', function () {
    expect(confirmDialog.setup(options)).toEqual(jasmine.any(Object));
  });

  describe('setup', function() {
    beforeEach(function() {
      dialog = confirmDialog.setup(options);
    });

    it('should instantiate a dialog', function() {
      expect($dialog.dialog).toHaveBeenCalledWith({
        dialogFade : true,
        backdropClick : false,
        templateUrl : '/api/partials/dialogs/confirm-dialog.html',
        controller : jasmine.any(Function)
      });
    });

    describe('opening dialog', function() {
      var spyThen, promise, anotherPromise, resolver;

      beforeEach(function() {
        anotherPromise = {};
        spyThen = jasmine.createSpy('$dialog.dialog.open.then').andReturn(anotherPromise);

        $dialog.dialog.spy.open.andCallFake(function () {
          return { then: spyThen };
        });
        promise = dialog.open();

        resolver = spyThen.mostRecentCall.args[0];

      });

      it('should open the dialog', function() {
        expect($dialog.dialog.spy.open).toHaveBeenCalled();
      });

      it('should return a promise', function() {
        expect(promise).toBe(anotherPromise);
      });

      it('should resolve the status on confirm', function() {
        expect(resolver('confirm')).toEqual('confirm');
      });

      it('should reject the status on anything else', function() {
        expect(resolver('blarg')).toBe(rejectedPromise);
      });

    });
  });

});