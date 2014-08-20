'use strict';

var router = require('../lib/router');

describe('Router', function () {
  afterEach(function () {
    router.reset();
  });

  it('should have a method to add a route', function () {
    expect(router.route).toEqual(jasmine.any(Function));
  });

  it('should have a method to go to an action', function () {
    expect(router.go).toEqual(jasmine.any(Function));
  });

  it('should go to a matched route', function () {
    var action = jasmine.createSpy('action');

    router.route('/foo/').get(action);
    router.go('/foo/', 'get', {});

    expect(action).toHaveBeenCalledOnce();
  });

  it('should call a matched route with a request object and response object', function () {
    var action = jasmine.createSpy('action');

    router.route('/foo/').get(action);
    router.go('/foo/', 'get', {}, { bar: 'baz' });

    var matches = ['/foo/'];
    matches.index = 0;
    matches.input = '/foo/';

    expect(action).toHaveBeenCalledOnceWith(
      {
        params: {},
        matches: matches,
        verb: 'get',
        data: { bar: 'baz' }
      },
      {
        spark: {},
        ack: undefined
      });
  });

  it('should handle named parameters', function () {
    var action = jasmine.createSpy('action');

    router.route('/host/:id').get(action);
    router.go('/host/1/', 'get', {});

    var matches = ['/host/1/', '1'];
    matches.index = 0;
    matches.input = '/host/1/';

    expect(action).toHaveBeenCalledOnceWith({
      params: { id: '1' },
      matches: matches,
      verb: 'get',
      data: undefined
    }, {
      spark: {},
      ack: undefined
    });
  });

  it('should handle regexp parameters', function () {
    var action = jasmine.createSpy('action');

    router.route(/^\/host\/(\d+)$/).get(action);
    router.go('/host/1', 'get', {});

    var matches = ['/host/1', '1'];
    matches.index = 0;
    matches.input = '/host/1';

    expect(action).toHaveBeenCalledOnceWith({
      params: { 0: '1' },
      matches: matches,
      verb: 'get',
      data: undefined
    }, {
      spark: {},
      ack: undefined
    });
  });

  it('should have an all method', function () {
    var action = jasmine.createSpy('action');

    router.route('/foo/bar').all(action);
    router.go('/foo/bar', 'post', {}, {});

    expect(action).toHaveBeenCalledOnce();
  });

  it('should match a route with a trailing slash', function () {
    var action = jasmine.createSpy('action');

    router.route('/foo/bar').get(action);
    router.go('/foo/bar/', 'get', {});

    expect(action).toHaveBeenCalledOnce();
  });

  it('should match a wildcard route', function () {
    var action = jasmine.createSpy('action');

    router.route('/(.*)').get(action);
    router.go('/foo/bar/', 'get', {});

    expect(action).toHaveBeenCalledOnce();
  });

  it('should throw if route does not match', function () {
    expect(shouldThrow).toThrow(new Error('Route: /foo/bar/ does not match provided routes.'));

    function shouldThrow () {
      router.go('/foo/bar/', 'get', {});
    }
  });

  it('should throw if method is not set', function () {
    router.route('/foo/bar/').get(function () {});

    expect(shouldThrow).toThrow(new Error('Route: /foo/bar/ does not have verb post'));

    function shouldThrow () {
      router.go('/foo/bar/', 'post', {}, {});
    }
  });

  var allVerbs = Object.keys(router.verbs).map(function getVerbs (key) {
    return router.verbs[key];
  }).concat('all');
  allVerbs.forEach(function testVerb (verb) {
    it('should have a convenience for ' + verb, function () {
      var action = jasmine.createSpy('action');

      router[verb]('/foo/bar/', action);

      router.go('/foo/bar/', verb, {}, {});

      expect(action).toHaveBeenCalledOnce();
    });
  });

  it('should return router from get', function () {
    var r = router.get('/foo/bar/', function () {});

    expect(r).toBe(router);
  });

  it('should place an ack on the response if one is provided', function () {
    var action = jasmine.createSpy('action');

    router.route('/host/:id').get(action);
    router.go('/host/1/', 'get', {}, null, function () {});

    var matches = ['/host/1/', '1'];
    matches.index = 0;
    matches.input = '/host/1/';

    expect(action).toHaveBeenCalledOnceWith({
      params: { id: '1' },
      matches: matches,
      verb: 'get',
      data: null
    }, {
      spark: {},
      ack: jasmine.any(Function)
    });
  });

  describe('the all method', function () {
    var action, getAction;

    beforeEach(function () {
      action = jasmine.createSpy('action');
      getAction = jasmine.createSpy('getAction');

      router.route('/foo/bar')
        .get(getAction)
        .all(action);
      router.go('/foo/bar', 'post', {}, {});
    });

    it('should not call the get method with post', function () {
      expect(getAction).not.toHaveBeenCalledOnce();
    });

    it('should call the all method with post', function () {
      expect(action).toHaveBeenCalledOnce();
    });
  });

  describe('routing in order', function () {
    var fooAction, wildcardAction;

    beforeEach(function () {
      fooAction = jasmine.createSpy('fooAction');
      wildcardAction = jasmine.createSpy('wildcardAction');

      router.route('/foo/bar/').get(fooAction);
      router.route('/(.*)').get(wildcardAction);

      router.go('/foo/bar/', 'get', {});
    });

    it('should call the first match', function () {
      expect(fooAction).toHaveBeenCalledOnce();
    });

    it('should not call the other match', function () {
      expect(wildcardAction).not.toHaveBeenCalled();
    });
  });

  describe('overwriting routes', function () {
    var fooAction1, fooAction2;

    beforeEach(function () {
      fooAction1 = jasmine.createSpy('fooAction1');
      fooAction2 = jasmine.createSpy('fooAction2');

      router.route('/foo/bar/').get(fooAction1);
      router.route('/foo/bar/').get(fooAction2);
      router.go('/foo/bar/', 'get', {});
    });

    it('should ignore the old route', function () {
      expect(fooAction1).not.toHaveBeenCalled();
    });

    it('should call the new route', function () {
      expect(fooAction2).toHaveBeenCalledOnce();
    });
  });
});
