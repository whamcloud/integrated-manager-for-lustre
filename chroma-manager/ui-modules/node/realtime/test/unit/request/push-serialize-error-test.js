'use strict';

var rewire = require('rewire');
var pushSerializeError = rewire('../../../request/push-serialize-error');

describe('push serialize error', function () {
  var revert, err, push, serializeError, serializedError;
  beforeEach(function () {
    err = new Error('im an error');
    push = jasmine.createSpy('push');
    serializedError = { error: 'im an error' };
    serializeError = jasmine.createSpy('serializeError').and.returnValue(serializedError);

    revert = pushSerializeError.__set__({
      serializeError: serializeError
    });

    pushSerializeError(err, push);
  });

  afterEach(function () {
    revert();
  });

  it('should push', function () {
    expect(push).toHaveBeenCalledOnceWith(null, serializedError);
  });

  it('should invoke serializeError with the error', function () {
    expect(serializeError).toHaveBeenCalledOnceWith(err);
  });
});
