describe('pathMaxLength Filter', function() {
  'use strict';

  var pathMaxLengthFilter, cache;

  beforeEach(module('filters'));

  beforeEach(inject(function($filter) {
    pathMaxLengthFilter = $filter('pathMaxLength');
  }));

  beforeEach(inject(function($cacheFactory) {
    cache = $cacheFactory.get('pathMaxLength');
  }));

  var testCases = {
    '/yay/fun.txt': [
      { maxLength: 60, result: '/yay/fun.txt', msg: 'should leave this path alone', cached: false },
      { maxLength: 10, result: '...', msg: 'should reduce this to just ...', cached: true }
    ],
    '/foo/remove_me/baz/fun.txt': [
      { maxLength: 20, result: '/foo/.../baz/fun.txt', msg: 'should be exactly 20 chars', cached: true },
      { maxLength: 16, result: '/foo/.../fun.txt', msg: 'should prefer left to right side', cached: true },
      { maxLength: 15, result: '/.../fun.txt', msg: 'should be only the filename and ... dir', cached: true }
    ],
    '/foo/remove_me/bark/baz/fun.txt': [
      { maxLength: 30, result: '/foo/remove_me/.../baz/fun.txt', cached: true },
      { maxLength: 29, result: '/foo/.../baz/fun.txt', cached: true },
      { maxLength: 17, result: '/foo/.../fun.txt', cached: true },
      { maxLength: 13, result: '/.../fun.txt', cached: true }
    ],
    '/foo/bar/really_long_file_name_here.txt': [
      { maxLength: 39, result: '/foo/bar/really_long_file_name_here.txt', cached: false },
      { maxLength: 35, result: '/.../really_long_file_name_here.txt', cached: true },
      { maxLength: 34, result: '...', cached: true }
    ],
    'no/leading/slash/file.txt': [
      { maxLength: 25, result: 'no/leading/slash/file.txt', msg: 'should remain unchanged', cached: false },
      { maxLength: 20, result: 'no/.../file.txt', cached: true },
      { maxLength: 12, result: '.../file.txt', cached: true },
      { maxLength: 10, result: '...', cached: true }
    ]
  };

  Object.keys(testCases).forEach(function(path) {

    testCases[path].forEach(function(test) {
      var msg = test.msg ? test.msg : 'should change %s to %s'.sprintf(path, test.result),
          cacheKey = test.maxLength + path;


      describe('for path ' + path + ' at length ' + test.maxLength, function() {
        var result, cachedResult;

        beforeEach(function() {
          result = pathMaxLengthFilter(path, test.maxLength);
          cachedResult = cache.get(cacheKey);
        });

        it(msg, function() {
          expect(result).toEqual(test.result);
        });

        if (test.cached) {
          it('should be cached', function() {
            expect(cachedResult).toEqual(test.result);
          });
        } else {
          it('should not be cached', function() {
            expect(cachedResult).toBeUndefined();
          });
        }
      });
    });
  });
});
