'use strict';

var util = require('util');
var Promise = require('promise');
var saveRepoThenModule = require('../../lib/save-repo-then').wiretree;
var parseGithubUrl = require('../../lib/parse-github-url').wiretree(Promise);

describe('Save repo then', function () {
  var saveRepoThen, execThen, delThen, url, fullPath, promise;

  beforeEach(function () {
    url = 'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3';
    fullPath = '/foo/bar';

    execThen = jasmine.createSpy('execThen').and.returnValue(Promise.resolve());

    delThen = jasmine.createSpy('delThen').and.returnValue(Promise.resolve());

    saveRepoThen = saveRepoThenModule(parseGithubUrl, execThen, delThen, util);

    promise = saveRepoThen(url, fullPath);
  });

  pit('should clone the repo', function () {
    return promise.then(function assertClone () {
      expect(execThen).toHaveBeenCalledWith('git clone git@github.com:michaelficarra/CoffeeScriptRedux.git /foo/bar');
    });
  });

  pit('should reset the repo', function () {
    return promise.then(function assertReset () {
      expect(execThen).toHaveBeenCalledWith('git -C "/foo/bar" reset --hard 9895cd1641fdf3a2424e662ab7583726bb0e35b3');
    });
  });

  pit('should clean the repo', function () {
    return promise.then(function assertClean () {
      expect(execThen).toHaveBeenCalledWith('git -C "/foo/bar" clean -f -d');
    });
  });

  pit('should delete dotfiles', function () {
    return promise.then(function assertDelete () {
      expect(delThen).toHaveBeenCalledWith(
        [
          '/foo/bar/**/.git',
          '/foo/bar/**/.gitignore',
          '/foo/bar/**/.npmignore'
        ],
        { force: true }
      );
    });
  });
});
