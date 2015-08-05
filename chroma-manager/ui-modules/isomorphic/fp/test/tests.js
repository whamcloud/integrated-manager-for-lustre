'use strict';

var fp = require('../index');

describe('the fp module', function () {
  var _;

  beforeEach(function () {
    _ = fp.__;
  });

  describe('has a curry method', function () {
    var toArray;

    beforeEach(function () {
      toArray = function toArray () {
        return [].slice.call(arguments);
      };
    });

    it('should exist on fp', function () {
      expect(fp.curry).toEqual(jasmine.any(Function));
    });

    describe('with 1 arg', function () {
      var curry1;

      beforeEach(function () {
        curry1 = fp.curry(1, toArray);
      });

      it('should return a function if not satisfied', function () {
        expect(curry1()).toEqual(jasmine.any(Function));
      });

      it('should return the value', function () {
        expect(curry1(1)).toEqual([1]);
      });

      it('should work with placeholders', function () {
        expect(curry1(_)(1)).toEqual([1]);
      });
    });

    describe('with 3 args', function () {
      var curry3, _;

      beforeEach(function () {
        _ = fp.__;

        curry3 = fp.curry(3, toArray);
      });

      it('should return a function if not satisfied', function () {
        expect(curry3(1, 2)).toEqual(jasmine.any(Function));
      });

      it('should be satisfied with all placeholders', function () {
        expect(curry3(_, _, _)(1, 2, 3)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with one call', function () {
        expect(curry3(1, 2, 3)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with a starting placeholder', function () {
        expect(curry3(_, 2, 3)(1)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with two placeholders', function () {
        expect(curry3(_, _, 3)(1)(2)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with two placeholders and two calls', function () {
        expect(curry3(_, _, 3)(1, 2)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with start and end placeholders', function () {
        expect(curry3(_, 2, _)(1, 3)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with two initial args', function () {
        expect(curry3(_, 2)(1)(3)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with two initial args and two calls', function () {
        expect(curry3(_, 2)(1, 3)).toEqual([1, 2, 3]);
      });

      it('should be satisfied with placeholders in later calls', function () {
        expect(curry3(_, 2)(_, 3)(1)).toEqual([1, 2, 3]);
      });
    });

    describe('with a placeholder', function () {
      var curry1;

      beforeEach(function () {
        curry1 = fp.curry(2, toArray)(_, 2);
      });

      it('should be immutable', function () {
        curry1(3);

        expect(curry1(1)).toEqual([1, 2]);
      });

      it('should be immutable with a right placeholder', function () {
        curry1 = fp.curry(2, toArray)(1, _);

        curry1(4);
        curry1(5);

        expect(curry1(2)).toEqual([1, 2]);
      });
    });
  });

  describe('has a map method', function () {
    var add1;

    beforeEach(function () {
      add1 = function add1 (n) {
        return n + 1;
      };
    });

    it('should exist on fp', function () {
      expect(fp.map).toEqual(jasmine.any(Function));
    });

    it('should be curried', function () {
      expect(fp.map(fp.identity)).toEqual(jasmine.any(Function));
    });

    it('should map a list', function () {
      expect(fp.map(add1, [1, 2, 3])).toEqual([2, 3, 4]);
    });

    it('should map a value', function () {
      expect(fp.map(add1, 1)).toEqual(2);
    });

    it('should work with a placeholder', function () {
      expect(fp.map(_, 1)(add1)).toEqual(2);
    });

    it('should be unary\'d', function () {
      var spy = jasmine.createSpy('unary');
      fp.map(spy, [1]);
      expect(spy).toHaveBeenCalledWith(1);
    });
  });

  describe('has a filter method', function () {
    it('should exist on fp', function () {
      expect(fp.filter).toEqual(jasmine.any(Function));
    });

    it('should filter a list', function () {
      expect(fp.filter(fp.eq(3), [1, 2, 3]))
        .toEqual([3]);
    });

    it('should be curried', function () {
      expect(fp.filter(fp.eq(1))([1, 2, 3]))
        .toEqual([1]);
    });

    it('should take placeholders', function () {
      expect(fp.filter(_, [1, 2, 3])(fp.eq(2)))
        .toEqual([2]);
    });
  });

  describe('has a find method', function () {
    it('should exist on fp', function () {
      expect(fp.find).toEqual(jasmine.any(Function));
    });

    it('should find a value', function () {
      expect(fp.find(fp.eq(3), [1, 2, 3]))
        .toEqual(3);
    });

    it('should be curried', function () {
      expect(fp.find(fp.eq(1))([1, 2, 3]))
        .toEqual(1);
    });

    it('should take placeholders', function () {
      expect(fp.find(_, [1, 2, 3])(fp.eq(2)))
        .toEqual(2);
    });

    it('should return undefined on no match', function () {
      expect(fp.find(fp.eq(10), [1, 2, 3]))
        .toBe(undefined);
    });
  });

  describe('has a pluck method', function () {
    it('should exist on fp', function () {
      expect(fp.pluck).toEqual(jasmine.any(Function));
    });

    it('should pluck from a collection', function () {
      expect(fp.pluck('foo', [{ foo: 'bar' }, { foo: 'baz' }])).toEqual(['bar', 'baz']);
    });

    it('should pluck from a value', function () {
      expect(fp.pluck('foo', { foo: 'bar' })).toEqual('bar');
    });

    it('should be curried', function () {
      expect(fp.pluck('foo')).toEqual(jasmine.any(Function));
    });

    it('should work with a placeholder', function () {
      expect(fp.pluck(_, { foo: 'bar' })('foo')).toEqual('bar');
    });
  });

  describe('has an identity method', function () {
    it('should exist on fp', function () {
      expect(fp.identity).toEqual(jasmine.any(Function));
    });

    it('should return it\'s value', function () {
      expect(fp.identity(1)).toEqual(1);
    });
  });

  describe('has an always method', function () {
    it('should exist on fp', function () {
      expect(fp.always).toEqual(jasmine.any(Function));
    });

    it('should always return it\'s value', function () {
      expect(fp.always('foo')()).toEqual('foo');
    });
  });

  describe('has a true method', function () {
    it('should exist on fp', function () {
      expect(fp.true).toEqual(jasmine.any(Function));
    });

    it('should always return true', function () {
      expect(fp.true()).toEqual(true);
    });
  });

  describe('has a flow method', function () {
    it('should exist on fp', function () {
      expect(fp.flow).toEqual(jasmine.any(Function));
    });

    it('should return a function', function () {
      expect(fp.flow(fp.identity)).toEqual(jasmine.any(Function));
    });

    it('should compose fns', function () {
      function add1 (x) {
        return x + 1;
      }

      function mult2 (x) {
        return x * 2;
      }

      expect(fp.flow(add1, mult2)(3)).toEqual(8);
    });
  });

  describe('has a difference method', function () {
    it('should exist on fp', function () {
      expect(fp.difference).toEqual(jasmine.any(Function));
    });

    it('should calculate differences', function () {
      expect(fp.difference([1, 2, 3], [1, 2])).toEqual([3]);
    });

    it('should work with placeholders', function () {
      expect(fp.difference(_, [1, 2])([1, 2, 3, 4])).toEqual([3, 4]);
    });

    it('should be curried', function () {
      expect(fp.difference([1, 2, 3])([1, 2])).toEqual([3]);
    });

    it('should work with empty arrays', function () {
      expect(fp.difference([], [])).toEqual([]);
    });
  });

  describe('has a lens method', function () {
    var headLens;

    beforeEach(function () {
      headLens = fp.lens(
        function get(arr) { return arr[0]; },
        function set(val, arr) { return [val].concat(arr.slice(1)); }
      );
    });

    it('should exist on fp', function () {
      expect(fp.lens).toEqual(jasmine.any(Function));
    });

    it('should retrieve a value', function () {
      expect(headLens([10, 20, 30, 40])).toEqual(10);
    });

    it('should set a new value', function () {
      expect(headLens.set('mu', [10, 20, 30, 40])).toEqual(['mu', 20, 30, 40]);
    });

    it('should provide a mapper', function () {
      expect(headLens.map(function add1 (x) { return x + 1; }, [10, 20, 30, 40]))
        .toEqual([11, 20, 30, 40]);
    });

    it('should be curried', function () {
      expect(fp.lens(fp.identity)).toEqual(jasmine.any(Function));
    });

    it('should take placeholders', function () {
      expect(fp.lens(_, fp.identity)(function get (arr) {
        return arr[0];
      })([10, 20, 30, 40]))
        .toEqual(10);
    });
  });

  describe('has a lensProp method', function () {
    var getX;

    beforeEach(function () {
      getX = fp.lensProp('x');
    });

    it('should exist on fp', function () {
      expect(fp.lensProp).toEqual(jasmine.any(Function));
    });

    it('should retrieve a value', function () {
      expect(getX({ x: 10 })).toEqual(10);
    });

    it('should set a new value', function () {
      expect(getX.set('mu', { x: 10 })).toEqual({ x: 'mu' });
    });

    it('should provide a mapper', function () {
      expect(getX.map(function add10 (x) {
        return x + 10;
      }, { x: 10 })).toEqual({ x: 20 });
    });
  });

  describe('has a flowLens method', function () {
    var lens, obj;

    beforeEach(function () {
      lens = fp.flowLens(fp.lensProp('foo'), fp.lensProp('bar'));

      obj = {
        foo: {
          bar: 'baz'
        }
      };
    });

    it('should exist on fp', function () {
      expect(fp.flowLens)
        .toEqual(jasmine.any(Function));
    });

    it('should get a nested value', function () {
      expect(lens(obj)).toEqual('baz');
    });

    it('should set a nested value', function () {
      expect(lens.set('bap', obj))
        .toEqual({foo: { bar: 'bap' } });
    });
  });

  describe('has a pathLens method', function () {
    var pl;

    beforeEach(function () {
      pl = fp.pathLens(['foo', 'bar', 'baz']);
    });

    it('should exist on fp', function () {
      expect(fp.pathLens).toEqual(jasmine.any(Function));
    });

    it('should pluck the value for the given path', function () {
      var obj = {
        foo: {
          bar: {
            baz: 7,
            other: 'test'
          }
        }
      };

      expect(pl(obj)).toEqual(7);
    });

    it('should throw an error if the path is not an array', function () {
      expect(function () { fp.pathLens('foo')({foo: 'bar'}); }).toThrow(
        new TypeError('pathLens must receive the path in the form of an array. Got: String'));
    });

    it('should not error when path does not exist', function () {
      expect(pl({})).toBe(undefined);
    });

    it('should not error when path is undefined', function () {
      expect(pl(undefined)).toBe(undefined);
    });

    it('should set a nested path when it does not exist', function () {
      expect(pl.set('bap', {})).toEqual({
        foo: {
          bar: {
            baz: 'bap'
          }
        }
      });
    });

    it('should set a nested path when it does exist', function () {
      expect(pl.set('bap', {foo: {bar: {}}})).toEqual({
        foo: {
          bar: {
            baz: 'bap'
          }
        }
      });
    });

    it('should get a nested array path', function () {
      expect(fp.pathLens([0, 1, 2, 3])([[0, [0, 1, [0, 1, 2, 3]]]])).toEqual(3);
    });
  });

  describe('has a cond method', function () {
    var cond;

    beforeEach(function () {
      cond = fp.cond(
        [function (x) { return x === 0; }, fp.always('water freezes at 0°C')],
        [function (x) { return x === 100; }, fp.always('water boils at 100°C')],
        [fp.true, function (temp) { return 'nothing special happens at ' + temp + '°C'; }]
      );
    });

    it('should exist on fp', function () {
      expect(fp.cond).toEqual(jasmine.any(Function));
    });

    it('should freeze at 0', function () {
      expect(cond(0)).toEqual('water freezes at 0°C');
    });

    it('should boil at 100', function () {
      expect(cond(100)).toEqual('water boils at 100°C');
    });

    it('should do nothing special at 50', function () {
      expect(cond(50)).toEqual('nothing special happens at 50°C');
    });
  });

  describe('has a shallow clone method', function () {
    it('should exist on fp', function () {
      expect(fp.shallowClone).toEqual(jasmine.any(Function));
    });

    it('should clone an object', function () {
      expect(fp.shallowClone({ x: 'foo', y: ['bar'] }))
        .toEqual({ x: 'foo', y: ['bar'] });
    });

    it('should clone an array', function () {
      expect(fp.shallowClone(['foo', 'bar']))
        .toEqual(['foo', 'bar']);
    });
  });

  describe('has a not method', function () {
    it('should exist on fp', function () {
      expect(fp.not).toEqual(jasmine.any(Function));
    });

    it('should negate a value', function () {
      expect(fp.not(true)).toEqual(false);
    });
  });

  describe('has an eq method', function () {
    it('should exist on fp', function () {
      expect(fp.eq).toEqual(jasmine.any(Function));
    });

    it('should check for equality', function () {
      expect(fp.eq(1, 1)).toBe(true);
    });

    it('should check by reference', function () {
      expect(fp.eq({}, {})).toBe(false);
    });
  });

  describe('has a eqLens method', function () {
    it('should exist on fp', function () {
      expect(fp.eqLens).toEqual(jasmine.any(Function));
    });

    it('should check for equality', function () {
      var obj1 = {
        a: 1
      };
      var obj2 = {
        a: 1
      };

      var aLens = fp.lensProp('a');

      expect(fp.eqLens(aLens)(obj1, obj2)).toBe(true);
    });
  });

  describe('has an invoke method', function () {
    var spy, error;
    beforeEach(function () {
      spy = jasmine.createSpy('spy');
      error = new Error('Error in fp.invoke - Cannot call invoke with non-array');
    });

    it('should exist on fp', function () {
      expect(fp.invoke).toEqual(jasmine.any(Function));
    });

    it('should throw if args are null', function () {
      expect(function () { fp.invoke(spy, null); }).toThrow(error);
    });

    it('should throw an error if a non array is passed in', function () {
      expect(function () { fp.invoke(spy, 'some items'); }).toThrow(error);
    });

    it('should invoke the function with an array of items', function () {
      var items = ['some', 'array', 'of', 'items', 7, {key: 'val'}];
      fp.invoke(spy, items);

      expect(spy).toHaveBeenCalledOnceWith('some', 'array', 'of', 'items', 7, {key: 'val'});
    });

    it('should invoke with a placeholder', function () {
      var spy1 = jasmine.createSpy('spy1');
      var spy2 = jasmine.createSpy('spy2');
      var x = {
        fn: spy1
      };
      var y = {
        fn: spy2
      };

      fp.pluck('fn', [x, y])
        .forEach(fp.invoke(_, ['arg1', 2]));

      expect(spy1).toHaveBeenCalledOnceWith('arg1', 2);
      expect(spy2).toHaveBeenCalledOnceWith('arg1', 2);
    });
  });

  describe('has a safe method', function () {
    var spy;

    beforeEach(function () {
      spy = jasmine.createSpy('spy');
    });

    it('should exist on fp', function () {
      expect(fp.safe).toEqual(jasmine.any(Function));
    });

    it('should return the default if unsafe', function () {
      expect(fp.safe(1, spy, {})(null))
        .toEqual({});
    });

    it('should call the fn if safe', function () {
      fp.safe(1, spy, {})('bar');

      expect(spy)
        .toHaveBeenCalledWith('bar');
    });

    it('should call the fn with multiple args', function () {
      fp.safe(2, spy, {})('foo', 'bar');

      expect(spy)
        .toHaveBeenCalledWith('foo', 'bar');
    });

    it('should call the default if any args are unsafe', function () {
      expect(fp.safe(2, spy, {})('foo', null))
        .toEqual({});
    });
  });

  describe('has a eqFn method', function () {
    it('should exist on fp', function () {
      expect(fp.eqFn).toEqual(jasmine.any(Function));
    });

    it('should allow for custom methods to determine equality', function () {
      var objA = {
        foo: {
          bar: 'baz'
        }
      };

      var objB = {
        bar: 'baz'
      };

      var fooLens = fp.lensProp('foo');
      var barLens = fp.lensProp('bar');

      expect(fp.eqFn(fp.flowLens(fooLens, barLens), barLens, objA, objB))
        .toBe(true);
    });
  });

  describe('has a noop method', function () {
    it('should exist on fp', function () {
      expect(fp.noop).toEqual(jasmine.any(Function));
    });

    it('should return undefined', function () {
      expect(fp.noop()).toBe(undefined);
    });
  });

  describe('has an or method', function () {
    var is5Or6;

    beforeEach(function () {
      is5Or6 = fp.or([
        fp.eq(5),
        fp.eq(6)
      ]);
    });

    it('should exist on fp', function () {
      expect(fp.or).toEqual(jasmine.any(Function));
    });

    it('should return a function after seeding', function () {
      expect(is5Or6).toEqual(jasmine.any(Function));
    });

    it('should work with gaps', function () {
      var baap  = 'baap';
      var isNoWayOr4Chars = fp.or(_, baap);
      expect(isNoWayOr4Chars([
        fp.eq('no way'),
        fp.eqFn(fp.identity, fp.lensProp('length'), 4)
      ])).toBe(true);
    });

    [5,6].forEach(function (val) {
      it('should return true for ' + val, function () {
        expect(is5Or6(val)).toBe(true);
      });
    });

    it('should return false if or is false', function () {
      expect(is5Or6(7)).toBe(false);
    });
  });

  describe('has an and method', function () {
    var isFooAnd3Chars;

    beforeEach(function () {
      isFooAnd3Chars = fp.and([
        fp.eq('foo'),
        fp.eqFn(fp.identity, fp.lensProp('length'), 3)
      ]);
    });

    it('should exist on fp', function () {
      expect(fp.and).toEqual(jasmine.any(Function));
    });

    it('should return a function after seeding', function () {
      expect(isFooAnd3Chars).toEqual(jasmine.any(Function));
    });

    it('should work with gaps', function () {
      var baap  = 'baap';
      var isBaapAnd4Chars = fp.and(_, baap);
      expect(isBaapAnd4Chars([
        fp.eq(baap),
        fp.eqFn(fp.identity, fp.lensProp('length'), 4)
      ])).toBe(true);
    });

    it('should return true if all true', function () {
      expect(isFooAnd3Chars('foo')).toBe(true);
    });

    it('should return false if any false', function () {
      expect(isFooAnd3Chars('zoo')).toBe(false);
    });
  });

  describe('has a bindMethod method', function () {
    var indexOf, indexOfABC;

    it('should exist on fp', function () {
      expect(fp.bindMethod).toEqual(jasmine.any(Function));
    });

    it('should be curried', function () {
      expect(fp.bindMethod(fp.identity)).toEqual(jasmine.any(Function));
    });

    it('should return a bound method as a free floating function', function () {
      indexOf = fp.bindMethod('indexOf');
      indexOfABC = indexOf('abc');

      expect(indexOfABC('b')).toBe(1);
    });
  });

  describe('has a invokeMethod method', function () {
    var indexOfB;

    it('should exist on fp', function () {
      expect(fp.invokeMethod).toEqual(jasmine.any(Function));
    });

    it('should be curried', function () {
      expect(fp.invokeMethod(fp.identity)).toEqual(jasmine.any(Function));
    });

    it('should return a function that is bound and invoke that function', function () {
      indexOfB = fp.invokeMethod('indexOf', ['b']);
      expect(indexOfB('abc')).toBe(1);
    });
  });
});
