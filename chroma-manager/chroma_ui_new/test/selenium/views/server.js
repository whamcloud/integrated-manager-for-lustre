/* jshint -W079 */

'use strict';

var format = require('util').format;
var _ = require('lodash');
var BaseView = require('./base.js').BaseView;
var modalFile = require('../views/modal');
var addServerModal = modalFile.addServerModal;
var commandModal = modalFile.commandModal;
var commandMonitor = require('../util/command-monitor');
var waitForCommands = commandMonitor.waitForCommandsToFinish;
var manager = require('../util/manager');
var longWait = manager.waitTimes.long;
var actionDropdownFactory = require('./action-dropdown');
var editMode = require('./server-edit-mode');
var isRemoved = require('../util/is-removed');
var msToSec = require('../util/time').msToSec;

BaseView.extend(Server);

/**
 * Page object for server screen
 * @constructor
 */
function Server () {
  BaseView.call(this);
  this.path = 'configure/server';
}

_.extend(Server.prototype, {
  editMode: editMode,
  ADD_SERVER_BUTTON: '.add-server-button',
  HOST_NAMES: 'item in server.servers.objects',
  get hostNames () {
    return element.all(by.repeater(Server.prototype.HOST_NAMES));
  },
  get SELECT_ALL_BTN () {
    return by.linkText('Select All');
  },
  get SELECT_NONE_BTN () {
    return by.linkText('Select None');
  },
  get INVERT_SELECTION_BTN () {
    return by.linkText('Invert Selection');
  },
  get ALL_HOSTS_UNSELECTED_BTNS_THEN () {
    return by.partialButtonText('Unselected');
  },
  get ALL_HOSTS_SELECTED_BTNS_THEN () {
    return by.partialButtonText('Selected');
  },
  get ACTIONS_MODAL_TITLE () {
    return $('h3.modal-title.ng-binding');
  },
  /**
   * Wait for the server table to appear now that the page has a spinner
   * as it resolves.
   * @param {Number} waitTime Time to wait in milliseconds.
   */
  waitForServerTable: function waitForServerTable (waitTime) {

    waitTime = waitTime || manager.waitTimes.medium;

    browser.wait(innerWaitForServerTable, waitTime,
      format('Server table[%j] not present after %d seconds',
        Server.prototype.SERVER_TABLE,
        msToSec(waitTime))
    );

    /**
     * Wait for server table element to be present.
     * @returns {Object||Promise}
     */
    function innerWaitForServerTable () {
      return browser.isElementPresent(Server.prototype.serverTable);
    }
  },
  get addServerButton () {
    return $(Server.prototype.ADD_SERVER_BUTTON);
  },
  SERVER_TABLE: '.server-table',
  DETAIL_LINK: 'a[ng-click^="server.showServerDetailModal"] span',
  get serverTable () {
    return $(Server.prototype.SERVER_TABLE);
  },
  /**
   * Get the row object or css, by number.
   * @param {Number} [rowNum]
   * @param {Boolean} [cssOnly]
   * @returns {Object|String}
   */
  getRow: function getRow (rowNum, cssOnly) {
    rowNum = rowNum || 1;

    var rowCss = format('tbody tr:nth-child(%d)', rowNum);

    return cssOnly ? rowCss : Server.prototype.serverTable.$(rowCss);
  },
  get FIRST_SERVER_DETAIL_LINK () {
    return format('%s %s %s',
      Server.prototype.SERVER_TABLE,
      Server.prototype.getRow(null, true),
      Server.prototype.DETAIL_LINK);
  },
  get firstServerDetailLink () {
    return $(Server.prototype.FIRST_SERVER_DETAIL_LINK);
  },
  get SECOND_SERVER_DETAIL_LINK () {
    return format('%s %s %s',
      Server.prototype.SERVER_TABLE,
      Server.prototype.getRow(2, true),
      Server.prototype.DETAIL_LINK);
  },
  get secondServerDetailLink () {
    return $(Server.prototype.SECOND_SERVER_DETAIL_LINK);
  },
  ROWS: '.server-table tbody tr',
  get rows () {
    return element.all(by.css(Server.prototype.ROWS));
  },
  /**
   * Wait for loading spinner to be removed.
   * @param {Number} waitTime Time to wait in milliseconds.
   */
  waitForLoadingSpinnerRemove: function waitForLoadingSpinnerRemove (waitTime) {

    if (!waitTime)
      waitTime = manager.waitTimes.medium;

    var loadingSpinnerIsRemoved = isRemoved(Server.prototype.loadingSpinner);

    browser.wait(
      loadingSpinnerIsRemoved,
      waitTime,
      format('Loading spinner[%s] still present after %d seconds',
        Server.prototype.LOADING_SPINNER,
        msToSec(waitTime))
    );

  },
  LOADING_SPINNER: '.loading-page',
  get loadingSpinner () {
    return $(Server.prototype.LOADING_SPINNER);
  },
  get LNET_STATE () {
    return format('%s tbody tr [ng-if*="lnet_up"]', Server.prototype.SERVER_TABLE);
  },
  get lnetState () {
    return element.all(by.css(Server.prototype.LNET_STATE));
  },
  ENTRIES_BUTTON: '.entries button',
  get entriesButton () {
    return $(Server.prototype.ENTRIES_BUTTON);
  },
  ENTRIES_COUNT_LIST: '.entries ul a',
  get entriesCountList () {
    return element.all(by.css(Server.prototype.ENTRIES_COUNT_LIST));
  },
  ENTRIES_NUMBER_LINK: '.entries ul a[ng-click*="server.setItemsPerPage(%d)"]'
});

Server.prototype.openEntriesDropdown = function openEntriesDropdown () {
  Server.prototype.entriesButton.click();
};

/**
 * Click on the link for the first detail modal.
 */
Server.prototype.openFirstDetailModal = function openFirstDetailModal () {
  Server.prototype.firstServerDetailLink.click();
};

/**
 * Click on the link for the second detail modal.
 */
Server.prototype.openSecondDetailModal = function openFirstDetailModal () {
  Server.prototype.secondServerDetailLink.click();
};

/**
 * Start lnet for each of the two smoke test servers.
 */
Server.prototype.startLnetAll = function startLnetAll () {

  Server.prototype.waitForLoadingSpinnerRemove();

  getHostsAnd(startLnetAndWait)();

  /**
   * Start lnet and wait for it to complete.
   * @param {Object} [item]
   * @param {Number} idx
   */
  function startLnetAndWait (item, idx) {
    if (idx === 0)
      startLnet(Server.prototype.getRow());
    else
      startLnet(Server.prototype.getRow(2));

    commandMonitor.waitForCommandsToFinish(manager.waitTimes.long);
  }

  /**
   * Start the lnet for the specified row.
   * @param {Object} row
   */
  function startLnet (row) {
    actionDropdownFactory(row).clickAction('Start LNet');
  }
};

/**
 * HOF. Get the hosts by repeater and do something
 * with each host item.
 * @param {Function} fn
 * @returns {Function}
 */
function getHostsAnd (fn) {
  return function innerGetHostsAnd () {
    Server.prototype.hostNames
      .then(function forEachHost (hostNames) {
        hostNames.forEach(fn);
      });
  };
}

/**
 * Remove all the servers.
 */
Server.prototype.removeAll = function removeAll () {

  Server.prototype.waitForLoadingSpinnerRemove();

  browser.isElementPresent(Server.prototype.serverTable)
    .then(removeServers)
    .then(waitForCommands(longWait));

  function removeServers (isPresent) {
    if (isPresent)
      return getHostsAnd(getRow)();
  }

  function getRow () {
    return Server.prototype.getRow()
      .then(clickRemove);
  }

  function clickRemove (row) {
    return actionDropdownFactory(row).clickAction('Remove');
  }
};

/**
 * Add the smoke test servers.
 */
Server.prototype.addServers = function addServers () {

  browser.wait(function waitForAddServersButton () {
    return browser.isElementPresent(Server.prototype.addServerButton);
  }, manager.waitTimes.long);

  Server.prototype.addServerButton.click()
    .then(function enterPdshServerAddExpressionThen () {
      addServerModal.waitForModal();

      addServerModal.enterAddress();
    })
    .then(function proceed () {

      addServerModal.submitAddress();

      addServerModal.waitForProceedEnabled();

      return addServerModal.proceedButton.click();
    })
    .then(function closeCommandModal () {
      commandModal.waitForModal();

      commandModal.waitForCloseButtonToBeClickable();

      return commandModal.closeButton.click();
    })
    .then(function selectProfile () {
      commandModal.waitForModalRemove();

      addServerModal.selectProfile();

      addServerModal.submitProfile();

      addServerModal.waitForModalRemove();

      commandMonitor.waitForCommandsToFinish(manager.waitTimes.long);

    });
};

module.exports = new Server();
