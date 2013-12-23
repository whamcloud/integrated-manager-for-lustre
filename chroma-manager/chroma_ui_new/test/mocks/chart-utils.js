mock.decorator(function chartUtils($delegate) {
  'use strict';

  return Mock.spyInstance($delegate);
});