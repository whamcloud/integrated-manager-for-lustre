(function () {
  'use strict';

  var config = require('../config');

  /**
   * Represents a manager from the config.
   * Although chroma_managers is a list we only use the first one at this point.
   * @constructor
   */
  function Manager () {
    var manager = config.chroma_managers.getFirst();

    Object.keys(manager).forEach(function (prop) {
      if (!this.hasOwnProperty(prop)) this[prop] = manager[prop];
    }, this);

    this.uiPath = config.uiPath;
  }

  /**
   * Finds the first user that is a superuser.
   * @throws Error Throws if a superuser was not found.
   */
  Manager.prototype.getSuperuser = function getSuperuser() {
    return this.users.get(function (user) { return user.is_superuser === true; });
  };

  module.exports = new Manager();
}());
