describe('Request animation frame', function () {
  'use strict';

  var raf, global;

  var mock = new Mock();
  var prefixes = ['moz', 'webkit', ''];

  beforeEach(module('requestAnimationFrame'));

  beforeEach(function () {
    global = {};
  });

  mock.factory(function $window() {
    return global;
  });

  mock.beforeEach('$window');

  prefixes.forEach(function (prefix) {
    describe(prefix, function () {
      var fn = _.partial(buildString, prefix),
        rafStr = fn('RequestAnimationFrame'),
        cafStr = fn('CancelAnimationFrame');

      beforeEach(function () {
        global[rafStr] = function () {};
        global[rafStr].bind = jasmine.createSpy('bind');
        global[cafStr] = function () {};
        global[cafStr].bind = jasmine.createSpy('bind');
      });

      beforeEach(inject(function (_raf_) {
        raf = _raf_;
      }));

      it('should use ' + rafStr + ' if available', function () {
        expect(global[rafStr].bind).toHaveBeenCalledOnceWith(global);
      });

      it('should use ' + cafStr + ' if available', function () {
        expect(global[cafStr].bind).toHaveBeenCalledOnceWith(global);
      });
    });
  });

  describe('polyfill', function () {
    beforeEach(inject(function (_raf_) {
      raf = _raf_;
    }));

    it('should provide a pollyfill if requestAnimationFrame is not provided', function () {
      expect(raf.requestAnimationFrame).toEqual(jasmine.any(Function));
    });

    it('should provide a pollyfill if cancelAnimationFrame is not provided', function () {
      expect(raf.cancelAnimationFrame).toEqual(jasmine.any(Function));
    });
  });

  function buildString(prefix, str) {
    var out;

    if (prefix.length) {
      out = prefix + str;
    } else {
      out = str.charAt(0).toLowerCase() + str.slice(1);
    }

    return out;
  }
});
