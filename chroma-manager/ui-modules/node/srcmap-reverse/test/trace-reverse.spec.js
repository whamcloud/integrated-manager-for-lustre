/* jshint node:true */
'use strict';

var srcmapRev = require('../index');
var promisedFile = require('promised-file');


describe('srcmap-reverse unit test', function () {

  var builtFilesPath;
  var sourceMapPath;
  var traceFilePath;
  var reversedTraceFilePath;
  var reversedTraceFileContents;
  var reversedTraceShortPathsFilePath;
  var reversedTraceShortPathsFileContents;
  var sourceMap;
  var traceCollection;
  var expectedFinalOutput;

  beforeEach(function (done) {
    builtFilesPath = __dirname + '/';
    sourceMapPath = builtFilesPath + '*.map.txt';

    promisedFile.getFile(sourceMapPath)
      .then(function assignSourceMap (file) {
        sourceMap = JSON.parse(file);
        done();
      });

  });

  beforeEach(function (done) {
    traceFilePath = __dirname + '/trace.txt';

    promisedFile.getFile(traceFilePath)
      .then(function getTraceCollection (traceFileContents) {
        traceCollection = srcmapRev.buildTraceCollection(traceFileContents);
        done();
      });

  });

  beforeEach(function (done) {
    reversedTraceFilePath = __dirname + '/reversed-trace.txt';

    promisedFile.getFile(reversedTraceFilePath)
      .then(function assignReversedTraceFileContents (contents) {
        reversedTraceFileContents = contents;
        done();
      });

  });

  beforeEach(function (done) {
    reversedTraceShortPathsFilePath = __dirname + '/reversed-trace-short-paths.txt';

    promisedFile.getFile(reversedTraceShortPathsFilePath)
      .then(function assignReversedTraceShortPathsFileContents (contents) {
        reversedTraceShortPathsFileContents = contents;
        done();
      });

  });

  beforeEach(function () {
    expectedFinalOutput = reversedTraceFileContents;
  });

  it('should produce a source code location, a line and column number.', function () {

    var actual;
    var expected = {line: 161, column: 14};

    actual = srcmapRev.reverseSourceMap(traceCollection[0], sourceMap);
    expect(actual.line).toEqual(expected.line);
    expect(actual.column).toEqual(expected.column);

  });

  it('should rebuild the trace collection.', function () {
    var actual;
    var reversedCollection;

    // reverse every line in traceCollection
    reversedCollection = traceCollection.map(function (traceLine) {
      return srcmapRev.reverseSourceMap(traceLine, sourceMap);
    });

    actual = srcmapRev.flattenTraceCollection(reversedCollection);

    expect(actual).toBe(expectedFinalOutput);
  });

  it('should strip the long paths.', function () {
    var actual;
    var reversedCollection;

    // reverse every line in traceCollection
    reversedCollection = traceCollection.map(function (traceLine) {
      return srcmapRev.reverseSourceMap(traceLine, sourceMap);
    });

    actual = srcmapRev.stripLongPaths(srcmapRev.flattenTraceCollection(reversedCollection));

    expect(actual).toBe(reversedTraceShortPathsFileContents);
  });
});
