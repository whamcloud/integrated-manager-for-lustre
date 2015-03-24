'use strict';

var format = require('util').format;
var _ = require('lodash-mixins');
var rewire = require('rewire');
var dirp = rewire('../index');

describe('dirp test', function () {
  var directory, files, result, requireFile, revert, readDirSync, statSync;
  beforeEach(function () {
    requireFile = jasmine.createSpy('requireFile').and.callFake(function (name) {
      return {name: name};
    });

    directory = '/some/known/directory';
    files = [
      'its-a-big-one.json',
      '.DS_Name',
      'index.js',
      'node_modules',
      'filename-1.json',
      'its-a-small-1-now.js',
      'package.json',
      'ziplock.json'
    ];

    readDirSync = jasmine.createSpy('readDirSync').and.returnValue([
        'its-a-big-one', 'filename-1', 'its-a-small-1-now'
    ]);

    statSync = jasmine.createSpy('statSync').and.callFake(function (name) {
      return (name !== 'node_modules' ? isFile(true) : isFile(false));

      function isFile (file) {
        return {
          isFile: jasmine.createSpy('statSync.isFile').and.returnValue(file)
        };
      }
    });

    revert = dirp.__set__({
      readDirSync: readDirSync,
      statSync: statSync
    });

    result = dirp(directory, requireFile);
  });

  afterEach(function () {
    revert();
  });

  ['its-a-big-one', 'filename-1', 'its-a-small-1-now']
    .forEach(function (key) {
      it(format('should contain the path and name for %s', key), function () {
        expect(result[_.camelCase(key)]).toEqual({name: format('%s/%s', directory, key)});
      });
    });
});
