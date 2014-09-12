'use strict';

var format = require('util').format;
var isRemoved = require('./is-removed');

var commandMonitor = {
  COMMAND_IN_PROGRESS: '.command-in-progress',
  get commandInProgress () {
    return $(commandMonitor.COMMAND_IN_PROGRESS);
  },
  /**
   * Waits for the spinny to stop spinning.
   * @param {Number} waitTime
   */
  waitForCommandsToFinish: function waitForCommandsToFinish (waitTime) {

    browser.wait(
      isRemoved(commandMonitor.commandInProgress),
      waitTime,
      format('Timeout after %s seconds waiting for commands to complete', waitTime)
    );

  }
};

module.exports = commandMonitor;
