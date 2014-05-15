describe('exception handler', function () {
  'use strict';

  var oldExceptionHandler;

  beforeEach(module(function($exceptionHandlerProvider) {
    $exceptionHandlerProvider.mode('log');

    oldExceptionHandler = $exceptionHandlerProvider.$get();
  }));

  var clientErrorModel;

  beforeEach(module('exception', function ($provide) {
    clientErrorModel = {
      $save: jasmine.createSpy('$save')
    };

    $provide.value('ClientErrorModel', ClientErrorModel);
    $provide.value('exceptionModal', jasmine.createSpy('exceptionModal'));

    function ClientErrorModel() { return clientErrorModel; }
  }, {
    windowUnload: { unloading: false },
    $document: [ { URL: '/foo' } ]
  }));

  var $document, $exceptionHandler, exceptionModal, windowUnload, error, cause;

  beforeEach(inject(function (_$document_, _$exceptionHandler_, _exceptionModal_, _windowUnload_) {
    error = new Error('uh oh!');
    cause = 'Something Happened!';

    $document = _$document_;
    $exceptionHandler = _$exceptionHandler_;
    exceptionModal = _exceptionModal_;
    windowUnload = _windowUnload_;
  }));

  afterEach(function () {
    windowUnload.unloading = false;
  });

  it('should not open the modal if the window is unloading', function () {
    windowUnload.unloading = true;

    $exceptionHandler(new Error('foo'), 'bar');

    expect(exceptionModal).not.toHaveBeenCalled();
  });

  describe('handling an exception', function () {
    beforeEach(function () {
      $exceptionHandler(error, cause);
    });

    it('should pass the exception to the modal', function () {
      expect(exceptionModal.mostRecentCall.args[0].resolve.exception()).toBe(error);
    });

    it('should pass the cause to the modal', function () {
      expect(exceptionModal.mostRecentCall.args[0].resolve.cause()).toBe(cause);
    });

    it('should open the modal when there is an error', function () {
      expect(exceptionModal).toHaveBeenCalled();
    });

    it('should only open the modal once', function () {
      $exceptionHandler(error, cause);

      expect(exceptionModal).toHaveBeenCalledOnce();
    });

    it('should delegate to the older $exceptionHandler', function () {
      expect(oldExceptionHandler.errors[0]).toEqual([error, cause]);
    });

    it('should call the client error model with the exception info', function () {
      expect(clientErrorModel).toEqual({
        stack: error.stack,
        message: 'uh oh!',
        cause: 'Something Happened!',
        url: $document[0].URL,
        $save: jasmine.any(Function)
      });
    });

    it('should save the client error model', function () {
      expect(clientErrorModel.$save).toHaveBeenCalledOnce();
    });
  });
});
