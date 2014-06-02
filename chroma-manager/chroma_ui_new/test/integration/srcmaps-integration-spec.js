/* jshint node:true */
'use strict';

var getLastLine = require('./getLastLine');
var exec = require('child_process').exec;
var path = require('path');

describe('Compiled Javascript File', function desc () {

  // Running the gulp file like '$ gulp build'.
  // Note, the 'done' function in the callback allows for asynchronicity.
  beforeEach(function asyncGulpBuild (done) {

    var buildCommand = path.resolve(__dirname + '/../../node_modules/.bin/gulp build');

    exec(buildCommand, function handler (error) {

      if (error) throw error;

      done();

    });

  });

  it('should have src map url at the bottom.', function srcMapCheck (done) {

    getLastLine(__dirname + '/../../static/chroma_ui/built-*.js')
      .then(function runExpectation (line) {
        expect(line).toContain('//# sourceMappingURL');
      })
      .done(done);

  });

});
