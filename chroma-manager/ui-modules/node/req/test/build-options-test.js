'use strict';

var buildOptions = require('../build-options');
var agent = require('../request-agent').agent;

describe('build options', function () {
  var path, opts, result;
  beforeEach(function () {
    path = '/api/my/test/dir';
    opts = {
      qs: {
        foo: 'bar',
        baz: ['qux', 'quux']
      },
      host: 'localhost:8000',
      hostname: 'localhost',
      port: '8000',
      headers: {},
      method: 'GET',
      json: {}
    };
  });

  describe('with json', function () {
    beforeEach(function () {
      result = buildOptions(path, opts);
    });

    it('should give appropriate results', function () {
      expect(result).toEqual({
        host: 'localhost:8000',
        hostname: 'localhost',
        port: '8000',
        method: 'GET',
        agent: agent,
        headers: {
          Accept: 'application/json',
          Connection: 'keep-alive',
          'Content-Type': 'application/json; charset=UTF-8',
          'Transfer-Encoding': 'chunked'
        },
        qs: { foo: 'bar', baz: [ 'qux', 'quux' ] },
        path: '/api/my/test/dir/?foo=bar&baz=qux&baz=quux',
        json: {}
      });
    });
  });

  describe('without json', function () {
    beforeEach(function () {
      delete opts.json;
      result = buildOptions(path, opts);
    });

    it('should give appropriate results', function () {
      expect(result).toEqual({
        host: 'localhost:8000',
        hostname: 'localhost',
        port: '8000',
        agent: agent,
        method: 'GET',
        headers: {
          Connection: 'keep-alive',
          'Transfer-Encoding': 'chunked'
        },
        qs: { foo: 'bar', baz: [ 'qux', 'quux' ] },
        path: '/api/my/test/dir/?foo=bar&baz=qux&baz=quux'
      });
    });
  });
});
