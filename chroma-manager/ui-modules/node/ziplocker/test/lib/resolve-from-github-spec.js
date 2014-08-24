'use strict';

var resolveFromGithubModule = require('../../lib/resolve-from-github').wiretree;
var util = require('util');
var Promise = require('promise');

describe('Resolve from GitHub', function () {
  var resolveFromGithub, requests, parseGithubUrl, url, promise;

  beforeEach(function () {
    url = 'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3';

    parseGithubUrl = jasmine.createSpy('parseGithubUrl').and.returnValue(Promise.resolve({
      path: 'michaelficarra/CoffeeScriptRedux.git',
      commitIsh: '9895cd1641fdf3a2424e662ab7583726bb0e35b3'
    }));

    requests = {
      requestThen: jasmine.createSpy('requestThen').and.returnValue(Promise.resolve({
        body: {
          dependencies: {
            foo: '1.0.0'
          }
        }
      }))
    };

    resolveFromGithub = resolveFromGithubModule(requests, util, parseGithubUrl);
    promise = resolveFromGithub(url);
  });

  it('should be a function', function () {
    expect(resolveFromGithub).toEqual(jasmine.any(Function));
  });

  it('should handle a url', function () {
    expect(parseGithubUrl).toHaveBeenCalledWith(url);
  });

  pit('should make a request with the raw url', function () {
    var rawUrl = 'https://raw.githubusercontent.com/michaelficarra/CoffeeScriptRedux/\
9895cd1641fdf3a2424e662ab7583726bb0e35b3/package.json';

    return promise.then(function assertRequestCall () {
      expect(requests.requestThen).toHaveBeenCalledWith(rawUrl);
    });
  });

  pit('should return the response object', function () {
    return promise.then(function assertResponseObject (response) {
      expect(response).toEqual({
        response: {
          dependencies: {
            foo: '1.0.0'
          }
        },
        value: url
      });
    });
  });
});
