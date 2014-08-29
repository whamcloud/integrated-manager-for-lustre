/*jshint node: true*/
'use strict';

/**
 * A logger factory that returns a logger suitable for the environment.
 * @param {Logger} bunyan
 * @param {Object} path
 * @param {Object} config
 * @returns {Logger}
 */
exports.wiretree = function loggerFactory(bunyan, path, config) {
  var logPath = config.logger.logPath;
  var level = config.logger.level;

  var streams = {
    stdout: {
      type: 'stream',
      level: level,
      stream: process.stdout
    },
    file: {
      type: 'file',
      level: level,
      path: path.join(logPath, config.logName + '.log')
    }
  };

  // Map out the streams needed for the current environment.
  var envStreams = config.logger.streams
    .map(function filterStreams(streamType) {
      return streams[streamType];
  });

  /**
   * @returns {Logger}
   */
  return bunyan.createLogger({
    name: config.logName,
    serializers: {
      err: bunyan.stdSerializers.err
    },
    streams: envStreams
  });
};
