describe('exception handler', function () {
  'use strict';

  var $exceptionHandler, $document, oldExceptionHandler, exceptionDialog,
    error, cause, clientErrorModel, clientErrorModelInstance;

  beforeEach(module(function($exceptionHandlerProvider) {
    $exceptionHandlerProvider.mode('log');

    oldExceptionHandler = $exceptionHandlerProvider.$get();
  }));

  beforeEach(module('exception', function ($provide) {
    exceptionDialog = {
      options: {},
      open: jasmine.createSpy('open')
    };

    clientErrorModelInstance = {
      $save: jasmine.createSpy('$save')
    };

    clientErrorModel = function ClientErrorModel() {
      return clientErrorModelInstance;
    };

    $document = [{
      URL: '/foo'
    }];

    $provide.value('exceptionDialog', exceptionDialog);
    $provide.value('ClientErrorModel', clientErrorModel);
    $provide.value('$document', $document);
  }));

  beforeEach(inject(function (_$exceptionHandler_) {
    error = new Error('uh oh!');
    cause = 'Something Happened!';

    $exceptionHandler = _$exceptionHandler_;

    $exceptionHandler(error, cause);
  }));

  it('should pass the exception to the dialog', function () {
    expect(exceptionDialog.options.resolve.exception()).toBe(error);
  });

  it('should pass the cause to the dialog', function () {
    expect(exceptionDialog.options.resolve.cause()).toBe(cause);
  });

  it('should open the dialog when there is an error', function () {
    expect(exceptionDialog.open).toHaveBeenCalled();
  });

  it('should only open the dialog once', function () {
    $exceptionHandler(error, cause);

    expect(exceptionDialog.open).toHaveBeenCalledTimes(1);
  });

  it('should delegate to the older $exceptionHandler', function () {
    expect(oldExceptionHandler.errors[0]).toEqual([error, cause]);
  });

  it('should call the client error model with the exception info', function () {
    expect(clientErrorModelInstance).toEqual({
      stack: error.stack,
      message: 'uh oh!',
      cause: 'Something Happened!',
      url: $document[0].URL,
      $save: jasmine.any(Function)
    });
  });

  it('should save the client error model', function () {
    expect(clientErrorModelInstance.$save).toHaveBeenCalledTimes(1);
  });
});
