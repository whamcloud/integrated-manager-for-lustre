//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.

(function () {
  'use strict';

  var fp = {};

  var __ = {};
  fp.__ = __;

  function _type (val) {
    if (val === null)
      return 'Null';
    else if (val === undefined)
      return 'Undefined';
    else
      return Object.prototype.toString
        .call(val)
        .slice(8, -1);
  }

  function curry (n, fn) {
    return function innerCurry () {
      var args = new Array(arguments.length);
      for (var i = 0, l = arguments.length; i < l; i++) {
        args[i] = arguments[i];
      }

      var gaps = n - args.length;
      gaps += args.filter(function findGaps (x) {
        return x === __;
      }).length;

      if (gaps > 0)
        return curry(gaps, function () {
          var innerArgs = new Array(arguments.length);
          for (var i = 0, l = arguments.length; i < l; i++) {
            innerArgs[i] = arguments[i];
          }

          var filledArgs = args.map(function (x) {
            if (x === __)
              return innerArgs.shift();

            return x;
          });

          return fn.apply(null, filledArgs.concat(innerArgs).slice(0, n));
        });
      else
        return fn.apply(null, args.slice(0, n));
    };
  }
  fp.curry = curry;

  var map = curry(2, function m (f, x) {
    if (x && typeof x.map === 'function')
      return x.map(fp.curry(1, f));
    else
      return f(x);
  });
  fp.map = map;

  var filter = curry(2, function filter (f, x) {
    if (Array.isArray(x))
      return x.filter(curry(1, f));

    throw new Error('fp.filter only works on arrays.');
  });
  fp.filter = filter;

  var find = curry(2, function find (f, xs) {
    return filter(f, xs)[0];
  });
  fp.find = find;

  var pluck = curry(2, function pluck (key, xs) {
    return map(function plucker (xs) {
      return xs[key];
    }, xs);
  });
  fp.pluck = pluck;

  var identity = function identity (x) { return x; };
  fp.identity = identity;

  function always (x) {
    return function innerAlways () {
      return x;
    };
  }
  fp.always = always;

  fp.true = always(true);

  function flow () {
    var args = new Array(arguments.length);

    for (var i = 0, l = arguments.length; i < l; i++) {
      args[i] = arguments[i];
    }

    return function flowInner (xs) {
      return args.reduce(function reducer (xs, fn) {
        return fn(xs);
      }, xs);
    };
  }
  fp.flow = flow;

  var difference = fp.curry(2, function difference (xs, ys) {
    return xs.reduce(function reduceDiffs (arr, x) {
      if (ys.indexOf(x) === -1)
        arr.push(x);

      return arr;
    }, []);
  });
  fp.difference = difference;

  var lens = curry(2, function lens (get, set) {
    set = curry(2, set);
    innerLens.set = set;

    innerLens.map = curry(2, function map (fn, xs) {
      return flow(get, fn, set(__, xs))(xs);
    });

    function innerLens (x) {
      return get(x);
    }

    return innerLens;
  });
  fp.lens = lens;

  fp.lensProp = function lensProp (prop) {
    return lens(
      function get (x) {
        return x[prop];
      },
      function set (val, x) {
        x[prop] = val;

        return x;
      }
    );
  };

  function flowLens () {
    var args = new Array(arguments.length);

    for (var i = 0, l = arguments.length; i < l; i++) {
      args[i] = arguments[i];
    }

    return lens(
      flow.apply(null, args),
      function set (val, xs) {
        args.reduce(function reducer (xs, l, index) {
          if (index === args.length - 1)
            return l.set(val, xs);
          else
            return l(xs);
        }, xs);

        return xs;
      }
    );
  }
  fp.flowLens = flowLens;

  function pathLens (path) {
    var pathType = _type(path);
    if (pathType !== 'Array')
      throw new TypeError('pathLens must receive the path in the form of an array. Got: ' + pathType);

    var lenses = map(fp.lensProp, path);

    return fp.lens(
      fp.safe(1, fp.flow.apply(null, lenses), undefined),
      function set (val, xs) {
        lenses.reduce(function reducer (xs, l, index) {
          if (index === lenses.length - 1)
            return l.set(val, xs);

          var x = l(xs);

          if (x != null)
            return x;

          x = {};

          l.set(x, xs);
          return x;
        }, xs);

        return xs;
      }
    );
  }

  fp.pathLens = pathLens;

  function cond () {
    var args = new Array(arguments.length);

    for (var i = 0, l = arguments.length; i < l; i++) {
      args[i] = arguments[i];
    }

    return function condInner (xs) {
      var result;

      args.some(function findTruthy (pair) {
        if (pair[0](xs))
          return (result = pair[1](xs));
      });

      return result;
    };
  }
  fp.cond = cond;

  function shallowClone (xs) {
    var type = _type(xs);

    if (type === 'Array')
      return xs.slice();
    else if (type === 'Object')
      return Object.keys(xs).reduce(function reducer (obj, key) {
        obj[key] = xs[key];

        return obj;
      }, {});

    throw new Error('shallow clone works with Array or Object. Got: ' + type);
  }
  fp.shallowClone = shallowClone;

  function not (x) {
    return !x;
  }
  fp.not = not;

  var eq = curry(2, function eq (a, b) {
    return a === b;
  });
  fp.eq = eq;

  var eqLens = curry(3, function eqLens (l, a, b) {
    return eq(l(a), l(b));
  });
  fp.eqLens = eqLens;

  var eqFn = curry(4, function eqFn (fnA, fnB, a, b) {
    return eq(fnA(a), fnB(b));
  });
  fp.eqFn = eqFn;

  var invoke = curry(2, function invoke(fn, args) {
    if (!Array.isArray(args))
      throw new Error('Error in fp.invoke - Cannot call invoke with non-array');

    return fn.apply(null, args);
  });
  fp.invoke = invoke;

  var safe = curry(3, function safe (arity, fn, def) {
    return curry(arity, function safeCheck () {
      for (var i = 0, l = arguments.length; i < l; i++) {
        if (arguments[i] == null)
          return def;
      }

      try {
        return fn.apply(null, arguments);
      } catch (e) {
        return def;
      }
    });
  });
  fp.safe = safe;

  function noop () {}
  fp.noop = noop;

  var and = fp.curry(2, function and (predicates, val) {
      return predicates.reduce(function reducer (curr, predicate) {
        return curr && predicate(val);
      }, true);
  });
  fp.and = and;

  var or = fp.curry(2, function or (predicates, val) {
      return predicates.reduce(function reducer (curr, predicate) {
        return curr || predicate(val);
      }, false);
  });
  fp.or = or;

  var bindMethod = fp.curry(2, function bindMethod (meth, obj) {
    return obj[meth].bind(obj);
  });
  fp.bindMethod = bindMethod;

  var invokeMethod = fp.curry(3, function invokeMethod (meth, args, obj) {
    return fp.flow(bindMethod(meth), invoke(__, args))(obj);
  });
  fp.invokeMethod = invokeMethod;

  /* global angular */

  if (typeof module !== 'undefined')
    module.exports = fp;
  if (typeof angular !== 'undefined')
    angular.module('fp', []).value('fp', fp);
  if (typeof window !== 'undefined')
    window.fp = fp;
}());
