mock.decorator(function raf($delegate) {
  'use strict';

  var rafMock = Mock.spyInstance($delegate);

  var queue = [];

  rafMock.requestAnimationFrame.andCallFake(function raf(func) {
    queue.push(func);

    return '1';
  });

  rafMock.requestAnimationFrame.flush = function flush() {
    while (queue.length) {
      queue.shift()();
    }
  };

  return rafMock;
});
