describe('Format bytes', function () {
  'use strict';

  var tests, formatBytes;

  beforeEach(module('charts'));

  beforeEach(inject(function (_formatBytes_) {
    formatBytes = _formatBytes_;

    tests = [
      {
        in: [320, 3],
        out: '320 B'
      },
      {
        in: [200000],
        out: '195.3 kB'
      },
      {
        in: [3124352],
        out: '2.980 MB'
      },
      {
        in: [432303020202, 6],
        out: '402.614 GB'
      },
      {
        in: [5323330102372, 3],
        out: '4.84 TB'
      },
      {
        in: ['5323330102372', '3'],
        out: '4.84 TB'
      }
    ];
  }));

  it('should determine the best size and suffix to display', function () {
    tests.forEach(function (test) {
      expect(formatBytes.apply(null, test.in)).toEqual(test.out);
    });
  });
});
