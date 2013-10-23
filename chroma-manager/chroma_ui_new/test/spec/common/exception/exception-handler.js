describe('exception handler', function () {
  'use strict';

  var $exceptionHandler, $document, oldExceptionHandler, exceptionModal,
    error, cause, clientErrorModel, clientErrorModelInstance;

  beforeEach(module(function($exceptionHandlerProvider) {
    $exceptionHandlerProvider.mode('log');

    oldExceptionHandler = $exceptionHandlerProvider.$get();
  }));

  beforeEach(module('exception', function ($provide) {
    exceptionModal = jasmine.createSpy('exceptionModal');

    clientErrorModelInstance = {
      $save: jasmine.createSpy('$save')
    };

    clientErrorModel = function ClientErrorModel() {
      return clientErrorModelInstance;
    };

    $document = [{
      URL: '/foo'
    }];

    $provide.value('exceptionModal', exceptionModal);
    $provide.value('ClientErrorModel', clientErrorModel);
    $provide.value('$document', $document);
  }));

  beforeEach(inject(function (_$exceptionHandler_) {
    error = new Error('uh oh!');
    cause = 'Something Happened!';

    $exceptionHandler = _$exceptionHandler_;

    $exceptionHandler(error, cause);
  }));

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
    expect(clientErrorModelInstance).toEqual({
      stack: error.stack,
      message: 'uh oh!',
      cause: 'Something Happened!',
      url: $document[0].URL,
      $save: jasmine.any(Function)
    });
  });

  it('should save the client error model', function () {
    expect(clientErrorModelInstance.$save).toHaveBeenCalledOnce();
  });
});
