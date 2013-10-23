describe('Exception modal controller', function () {
  'use strict';

  var $scope, createController, getMessage, plainError, responseError;

  beforeEach(module('exception'));

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();

    plainError = new Error('Error');

    responseError = new Error('Response Error');

    responseError.response = {
      status: 500,
      headers: {},
      data: {
        error_message: '',
        traceback: ''
      },
      config: {
        method:  'POST',
        url: '/api/foo/bar/',
        headers: {},
        data: {}
      }
    };

    createController = function createController(deps) {
      deps = _.extend({$scope: $scope}, deps);

      $controller('ExceptionModalCtrl', deps);
    };

    getMessage = function getMessage(name) {
      return $scope.exceptionModal.messages.filter(function (message) {
        return message.name === name;
      }).pop();
    };
  }));

  it('should convert a string cause to a message', function () {
    createController({
      cause: 'fooz',
      exception: plainError
    });

    expect(getMessage('cause')).toEqual({name: 'cause', value: 'fooz'});
  });

  it('should return the expected messages for a plain error', function () {
    //Patch the stack as it becomes inconsistent as it's moved around.
    plainError.stack = 'ERROOR!';

    // Note this does not take IE into account as we (currently) do not run automated tests there.
    createController({cause: null, exception: plainError});

    expect($scope.exceptionModal.messages).toEqual([
      {name: 'name', value: 'Error'},
      {name: 'message', value: 'Error'},
      {name: 'Client Stack Trace', value: 'ERROOR!'}
    ]);
  });

  it('should return the expected messages for a response error', function () {
    //Patch the stack as it becomes inconsistent as it's moved around.
    responseError.stack = 'ERROOR!';

    // Note this does not take IE into account as we (currently) do not run automated tests there.
    createController({cause: null, exception: responseError});

    expect($scope.exceptionModal.messages).toEqual([
      {name: 'Response Status', value: 500},
      {name: 'Response Headers', value: '{}'},
      {name: 'method', value: 'POST'},
      {name: 'url', value: '/api/foo/bar/'},
      {name: 'Request Headers', value: '{}'},
      {name: 'data', value: '{}'},
      {name: 'name', value: 'Error'},
      {name: 'message', value: 'Response Error'},
      {name: 'Client Stack Trace', value: 'ERROOR!'}
    ]);
  });

  it('should not throw when handling a plain error', function () {
    function create () {
      createController({cause: null, exception: plainError});
    }

    expect(create).not.toThrow();
  });

  describe('handling non-strings when expecting multiline', function () {
    var create;

    beforeEach(function () {
      responseError.stack = 5;

      create = function () {
        createController({cause: null, exception: responseError});
      };
    });

    it('should handle non-strings when expecting a multiline one', function () {
      expect(create).not.toThrow();
    });

    it('should print the string representation of the value', function () {
      create();

      expect(getMessage('Client Stack Trace')).toEqual({name: 'Client Stack Trace', value: '5'});
    });
  });

  describe('circular references', function () {
    beforeEach(function () {
      responseError.response.config.data.foo = responseError.response;
    });

    it('should not throw when handling a circular reference', function () {
      function create () {
        createController({cause: null, exception: responseError});
      }

      expect(create).not.toThrow();
    });

    it('should return the string representation of the cyclic structure', function () {
      createController({cause: null, exception: responseError});

      expect(getMessage('data')).toEqual({name: 'data', value: '[object Object]'});
    });
  });
});
