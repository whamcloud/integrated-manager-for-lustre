'use strict';

var format = require('util').format;

var editMode;

module.exports = editMode = {
  ACTIONS_BUTTONS: '.action-buttons button',
  get DETECT_FILE_SYSTEMS_ACTIONS_BUTTON () {
    return format('%s[tooltip^="Detect an existing file system"]', editMode.ACTIONS_BUTTONS);
  },
  get detectFileSystemsActionsButton () {
    return $(editMode.DETECT_FILE_SYSTEMS_ACTIONS_BUTTON);
  },
  detectFileSystems: function detectFileSystems () {
    editMode.detectFileSystemsActionsButton.click();
  },

  EDIT_MODE_BUTTONS: '.edit-buttons',
  get TOP_BUTTONS () {
    return format('%s a', editMode.EDIT_MODE_BUTTONS);
  },
  get SELECT_ALL_BUTTON () {
    return format('%s[btn-radio="\'all\'"]', editMode.TOP_BUTTONS);
  },
  get selectAllButton () {
    return $(editMode.SELECT_ALL_BUTTON);
  },
  get SELECT_NONE_BUTTON () {
    return format('%s[btn-radio="\'none\'"]', editMode.TOP_BUTTONS);
  },
  get selectNoneButton () {
    return $(editMode.SELECT_NONE_BUTTON);
  },
  get INVERT_BUTTON () {
    return format('%s[btn-radio="\'invert\'"]', editMode.TOP_BUTTONS);
  },
  get EDIT_MODE_BIG_BUTTONS () {
    return format('%s button', editMode.EDIT_MODE_BUTTONS);
  },
  getDisabledEditModeButton: function getDisabledEditModeButton (buttonSelector) {
    return $(format('%s[disabled="disabled"]', buttonSelector));
  },
  get DETECT_FILE_SYSTEMS_EDIT_MODE_BUTTON () {
    return format('%s[tooltip-html-unsafe^="Ensure that all storage servers"]', editMode.EDIT_MODE_BIG_BUTTONS);
  },
  get detectFileSystemsEditModeButton () {
    return $(editMode.DETECT_FILE_SYSTEMS_EDIT_MODE_BUTTON);
  },
  get detectFileSystemsEditModeButtonDisabled () {
    return editMode.getDisabledEditModeButton(editMode.DETECT_FILE_SYSTEMS_EDIT_MODE_BUTTON);
  },


  get REWRITE_TARGET_CONFIG_ACTIONS_BUTTON () {
    return format('%s[tooltip^="Update each target with the"]', editMode.ACTIONS_BUTTONS);
  },
  get rewriteTargetConfigurationActionsButton () {
    return $(editMode.REWRITE_TARGET_CONFIG_ACTIONS_BUTTON);
  },
  rewriteTargetConfiguration: function rewriteTargetConfiguration () {
    editMode.rewriteTargetConfigurationActionsButton.click();
  },
  get REWRITE_TARGET_CONFIG_EDIT_MODE_BUTTON () {
    return format('%s[tooltip-html-unsafe^="Select all servers for which"]', editMode.EDIT_MODE_BIG_BUTTONS);
  },
  get rewriteTargetConfigurationEditModeButton () {
    return $(editMode.REWRITE_TARGET_CONFIG_EDIT_MODE_BUTTON);
  },
  get rewriteTargetConfigurationEditModeButtonDisabled () {
    return editMode.getDisabledEditModeButton(editMode.REWRITE_TARGET_CONFIG_EDIT_MODE_BUTTON);
  },


  get INSTALL_UPDATES_ACTIONS_BUTTON () {
    return format('%s[tooltip^="Install updated software on "]', editMode.ACTIONS_BUTTONS);
  },
  get installUpdatesActionsButton () {
    return $(editMode.INSTALL_UPDATES_ACTIONS_BUTTON);
  },
  installUpdates: function installUpdates () {
    editMode.installUpdatesActionsButton.click();
  },
  get INSTALL_UPDATES_EDIT_MODE_BUTTON () {
    return format('%s[tooltip-html-unsafe^="Installs updated software on"]', editMode.EDIT_MODE_BIG_BUTTONS);
  },
  get installUpdatesEditModeButton () {
    return $(editMode.INSTALL_UPDATES_EDIT_MODE_BUTTON);
  },
  get installUpdatesEditModeButtonDisabled () {
    return editMode.getDisabledEditModeButton(editMode.INSTALL_UPDATES_EDIT_MODE_BUTTON);
  },


  get selectedButtons () {
    return element.all(by.partialButtonText('Selected'));
  },
  get unselectedButtons () {
    return element.all(by.partialButtonText('Unselected'));
  }
};
