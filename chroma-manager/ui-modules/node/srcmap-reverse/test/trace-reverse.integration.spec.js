/* jshint node:true */
'use strict';

var srcmapRev = require('../index');
var promisedFile = require('promised-file');


describe('srcmap-reverse integration test', function () {

  var builtFilesPath;
  var sourceMapPath;
  var reversedTraceShortPathsFilePath;
  var sourceMap;
  var traceFilePath;
  var trace;
  var actual;
  var expected;

  beforeEach(function getSourceMapFile (done) {
    builtFilesPath = __dirname + '/';
    sourceMapPath = builtFilesPath + '*.map.txt';

    promisedFile.getFile(sourceMapPath)
      .then(function assignSourceMapFromFile (file) {
        sourceMap = JSON.parse(file);
        done();
      });

  });

  beforeEach(function getTrace (done) {
    traceFilePath = __dirname + '/trace.txt';

    promisedFile.getFile(traceFilePath)
      .then(function assignTrace (traceFileContents) {
        trace = traceFileContents;
        done()
      });

  });

  beforeEach(function getExpectedFile (done) {
    reversedTraceShortPathsFilePath = __dirname + '/reversed-trace-short-paths.txt';

    promisedFile.getFile(reversedTraceShortPathsFilePath)
      .then(function assignExpectedFromFile (contents) {
        expected = contents;
        done();
      });

  });

  it('should unminify a stack trace, and return line and column numbers for each line in a minified stack trace',
    function () {
      actual = srcmapRev.execute(trace, sourceMap);
      expect(actual).toEqual(expected);
    });
});
