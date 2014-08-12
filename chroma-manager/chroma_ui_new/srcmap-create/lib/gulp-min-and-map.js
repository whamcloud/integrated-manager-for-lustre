/* jshint node:true, strict:false */

var through = require('through');
var gutil = require('gulp-util');
var PluginError = gutil.PluginError;
var File = gutil.File;
var Buffer = require('buffer').Buffer;
var UglifyJS = require('uglify-js');
var fs = require('fs');
var format = require('util').format;
var plugName = 'gulp-min-and-map';

/**
 * Minifies and source maps in a gulp stream.
 * @param {String} fileName
 */
module.exports = function gulpMinAndMap (fileName) {

  if (!fileName) throw new PluginError(plugName, 'Missing fileName option for gulp-min-and-map');

  var mapFileName = fileName + '.map';
  var files = [];

  /**
   * Buffer up the files for later.
   * @param {Object} file Gulp vinyl file.
   */
  function bufferContents (file) {
    if (file.isNull()) return; // ignore
    if (file.isStream()) return this.emit('error', new PluginError(plugName, 'Streaming not supported'));

    files.push(file);
  }

  /**
   * Manipulate the files and add them to the stream.
   */
  function endStream () {
    var concatVinyl;
    var sourceMapVinyl;
    var concatResult;

    concatResult = minify(files, {
      compress: {
        drop_debugger: true,
        drop_console: true
      },
      outSourceMap: mapFileName,
      output: { beautify: false },
      mangle: false,
      sourceMapIncludeSources: true,
      sourceRoot: '/source/'
    });

    concatVinyl = new File({
      path: fileName,
      contents: new Buffer(concatResult.code)
    });
    this.emit('data', concatVinyl);

    sourceMapVinyl = new File({
      path: mapFileName,
      contents: new Buffer(concatResult.map)
    });
    this.emit('data', sourceMapVinyl);

    this.emit('end');
  }

  return through(bufferContents, endStream);
};

/**
 * Tiny bootleg of UglifyJS, modded for Vinyl files.
 * @param {Array} files List of Vinyl files.
 * @param {Object} options
 * @returns {{code: string, map: string}}
 */
var minify = function minify (files, options) {
  /*jshint maxcomplexity:13 */
  options = UglifyJS.defaults(options, {
    spidermonkey: false,
    outSourceMap: null,
    sourceRoot: null,
    inSourceMap: null,
    fromString: false,
    warnings: false,
    mangle: {},
    output: null,
    compress: {}
  });
  UglifyJS.base54.reset();

  // 1. parse
  var toplevel = null,
    sourcesContent = {};

  if (options.spidermonkey) {
    toplevel = UglifyJS.AST_Node.from_mozilla_ast(files);
  } else {
    if (typeof files === 'string')
      files = [ files ];
    files.forEach(function (file) {

      var code = file.contents + '';
      // TODO: Add whitelist
      if (file.path.indexOf('primus') === -1)
        code = format('(function(){ %s }())', code);

      sourcesContent[file.path] = code;
      toplevel = UglifyJS.parse(code, {
        filename: file.path,
        toplevel: toplevel
      });
    });
  }

  // 2. compress
  if (options.compress) {
    var compress = { warnings: options.warnings };
    UglifyJS.merge(compress, options.compress);
    toplevel.figure_out_scope();
    var sq = UglifyJS.Compressor(compress);
    toplevel = toplevel.transform(sq);
  }

  // 3. mangle
  if (options.mangle) {
    toplevel.figure_out_scope();
    toplevel.compute_char_frequency();
    toplevel.mangle_names(options.mangle);
  }

  // 4. output
  var inMap = options.inSourceMap;
  var output = {};
  if (typeof options.inSourceMap === 'string') {
    inMap = fs.readFileSync(options.inSourceMap, 'utf8');
  }
  if (options.outSourceMap) {
    output.source_map = UglifyJS.SourceMap({
      file: options.outSourceMap,
      orig: inMap,
      root: options.sourceRoot
    });
    if (options.sourceMapIncludeSources) {
      for (var file in sourcesContent) {
        if (sourcesContent.hasOwnProperty(file)) {
          output.source_map.get().setSourceContent(file, sourcesContent[file]);
        }
      }
    }

  }
  if (options.output) {
    UglifyJS.merge(output, options.output);
  }
  var stream = UglifyJS.OutputStream(output);
  toplevel.print(stream);

  return {
    code: stream + '',
    map: output.source_map + ''
  };
};
