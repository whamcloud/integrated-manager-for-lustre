'use strict';

var resolveFromTgzModule = require('../../lib/resolve-from-tgz').wiretree;
var zlib = require('zlib');
var tar = require('tar');
var Promise = require('promise');
var fs = require('fs');
var dirname = require('path').dirname;

describe('resolve from tgz', function () {
  var resolveFromTgz, requests;

  beforeEach(function () {
    requests = {
      requestPipe: jasmine.createSpy('requestPipe')
    };

    resolveFromTgz = resolveFromTgzModule(requests, Promise, zlib, tar);
  });

  it('should call request pipe with the url', function () {
    resolveFromTgz('https://foo.bar.com');

    expect(requests.requestPipe).toHaveBeenCalledWith('https://foo.bar.com');
  });

  pit('should extract the package.json', function () {
    var fooTarGz = dirname(__dirname) + '/foo.tar.gz';
    requests.requestPipe.and.returnValue(fs.createReadStream(fooTarGz));

    return resolveFromTgz('https://foo.bar.com').then(function (resp) {
      expect(resp).toEqual({
        response: {
          name: 'foo',
          version: '1.0.0',
          main: 'index.js',
          dependencies: {}
        },
        value: 'https://foo.bar.com'
      });
    });
  });
});
