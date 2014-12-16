/* jshint node:true */
'use strict';

var getLastLine = require('./util/getLastLine');
var execFile = require('child_process').execFile;
var path = require('path');

describe('Javascript Srcmaps', function desc () {

  describe('before being built', function () {
    it('should error if the compiled javascript file does not exist.', function srcMapCheck (done) {

      getLastLine(__dirname + '/../../static/chroma_ui/doesntExist-*.js')
        .catch(function handleErr (err) {
          expect(err.message).toBe('Glob failed to find a match.');
        })
        .done(done);

    });
  });

  describe('after being built', function () {
    var gulpFile, gulpTask, gulpTimeout;

    // Running the gulp file like '$ gulp build'.
    // Note, the 'done' function in the callback allows for asynchronicity.
    beforeEach(function asyncGulpBuild (done) {
      gulpFile = path.resolve(__dirname + '/../node_modules/.bin/gulp');

      gulpTask = 'default';
      gulpTimeout = 600000;

      execFile(gulpFile, [gulpTask, '--env', 'production'], {timeout: gulpTimeout}, function handler (error, stdout) {

        if (stdout) console.log('\n### stdout: \n', stdout);

        if (error) throw error;

        done();
      });
    });

    it('should have src map url at the bottom of the built file.', function srcMapCheck (done) {
      var staticDir = __dirname + '/../../../chroma_ui/static/chroma_ui/';

      getLastLine(staticDir + 'built-*.js')
        .then(function runExpectation (line) {
          expect(line).toContain('//# sourceMappingURL');
        })
        .done(done);
    });
  });
});
