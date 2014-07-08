describe('Exception interceptor', function () {
  'use strict';

  var exceptionInterceptor, exceptionHandler, response, $rootScope, error, errbackSpy, disconnectHandler;

  beforeEach(module({STATIC_URL: '/api/'}, function ($exceptionHandlerProvider) {
    $exceptionHandlerProvider.mode('log');

    exceptionHandler = $exceptionHandlerProvider.$get();
  }, 'exception', function ($provide) {
    disconnectHandler = { add: jasmine.createSpy('add') };

    $provide.value('disconnectHandler', disconnectHandler);
  }));

  beforeEach(inject(function (_exceptionInterceptor_, _$rootScope_) {
    exceptionInterceptor = _exceptionInterceptor_;
    $rootScope = _$rootScope_;
    errbackSpy = jasmine.createSpy('errbackSpy');
    error = new Error('Test Error!');

    response = {
      data: {},
      status: 500,
      headers: jasmine.createSpy('headers').andCallFake(function () {
        return {};
      }),
      config: {
        method: 'GET',
        url: '/foo'
      }
    };
  }));

  describe('request error', function () {
    it('should call $exceptionHandler with the same error that was passed in', function () {
      exceptionInterceptor.requestError(error);

      expect(exceptionHandler.errors[0][0]).toBe(error);
    });

    it('should call $exceptionHandler with a cause if passed a string.', function () {
      var errorString = 'Uh Oh!';

      exceptionInterceptor.requestError(errorString);

      expect(exceptionHandler.errors[0][1]).toBe(errorString);
    });

    describe('custom error', function () {
      var strangeError, customError;

      beforeEach(function () {
        strangeError = {foo: 'bar'};

        exceptionInterceptor.requestError(strangeError);

        customError = exceptionHandler.errors[0][0];
      });

      it('should call $exceptionHandler with a custom error', function () {
        expect(customError).toEqual(jasmine.any(Error));
      });

      it('should add the rejection as a property to the custom error', function () {
        expect(customError.rejection).toEqual(strangeError);
      });
    });
  });

  describe('response error', function ( ) {
    var passThroughs = [400, 403];

    passThroughs.forEach(function testStatus (status) {
      it('should reject ' + status +  ' errors', function () {
        response.status = status;

        var out = exceptionInterceptor.responseError(response);

        out.then(null, errbackSpy);

        $rootScope.$digest();

        expect(errbackSpy).toHaveBeenCalled();
      });

      it('should not call the $exceptionHandler with an error on ' + status + 's', function () {
        response.status = status;

        exceptionInterceptor.responseError(response);

        expect(exceptionHandler.errors.length).toBe(0);
      });
    });

    it('should not call the $exceptionHandler with an error on 0s', function () {
      response.status = 0;

      exceptionInterceptor.responseError(response);

      expect(exceptionHandler.errors.length).toBe(0);
    });

    it('should call the disconnectHandler on a 0', function () {
      response.status = 0;

      exceptionInterceptor.responseError(response);

      expect(disconnectHandler.add).toHaveBeenCalled();
    });

    it('should not call the disconnectHandler on a 0 replay', function () {
      response.status = 0;
      response.config.UI_REPLAY = true;

      exceptionInterceptor.responseError(response);

      expect(disconnectHandler.add).not.toHaveBeenCalled();
    });

    it('should reject 500 errors', function () {
      var out = exceptionInterceptor.responseError(response);

      out.then(null, errbackSpy);

      $rootScope.$digest();

      expect(errbackSpy).toHaveBeenCalled();
    });

    it('should call the $exceptionHandler with an error on 500s', function () {
      exceptionInterceptor.responseError(response);

      var error = exceptionHandler.errors[0][0];

      expect(error).toEqual(jasmine.any(Error));
    });
  });
});
