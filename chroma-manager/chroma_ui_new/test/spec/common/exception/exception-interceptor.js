describe('Exception interceptor', function () {
  'use strict';

  var exceptionInterceptor, exceptionHandler, response, $rootScope, error, errbackSpy;

  beforeEach(module({STATIC_URL: '/api/'}, 'exception', function ($provide) {

    $provide.value('$exceptionHandler', jasmine.createSpy('$exceptionHandler'));
  }));

  beforeEach(inject(function (_exceptionInterceptor_, _$exceptionHandler_, _$rootScope_) {
    exceptionInterceptor = _exceptionInterceptor_;
    exceptionHandler = _$exceptionHandler_;
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

      expect(exceptionHandler).toHaveBeenCalledOnceWith(error);
    });

    it('should call $exceptionHandler with a cause if passed a string.', function () {
      var errorString = 'Uh Oh!';

      exceptionInterceptor.requestError(errorString);

      expect(exceptionHandler).toHaveBeenCalledWith(null, errorString);
    });

    describe('custom error', function () {
      var strangeError, customError;

      beforeEach(function () {
        strangeError = {foo: 'bar'};

        exceptionInterceptor.requestError(strangeError);

        customError = exceptionHandler.mostRecentCall.args[0];
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
      it('should reject ' + status + ' errors', function () {
        response.status = status;

        var out = exceptionInterceptor.responseError(response);

        out.then(null, errbackSpy);

        $rootScope.$digest();

        expect(errbackSpy).toHaveBeenCalled();
      });

      it('should not call the $exceptionHandler with an error on ' + status + 's', function () {
        response.status = status;

        exceptionInterceptor.responseError(response);

        expect(exceptionHandler.callCount).toBe(0);
      });
    });

    it('should call the $exceptionHandler with an error on 0s', function () {
      response.status = 0;

      exceptionInterceptor.responseError(response);

      expect(exceptionHandler.callCount).toBe(1);
    });

    it('should reject 500 errors', function () {
      var out = exceptionInterceptor.responseError(response);

      out.then(null, errbackSpy);

      $rootScope.$digest();

      expect(errbackSpy).toHaveBeenCalled();
    });

    it('should call the $exceptionHandler with an error on 500s', function () {
      exceptionInterceptor.responseError(response);

      var error = exceptionHandler.mostRecentCall.args[0];

      expect(error).toEqual(jasmine.any(Error));
    });
  });
});
