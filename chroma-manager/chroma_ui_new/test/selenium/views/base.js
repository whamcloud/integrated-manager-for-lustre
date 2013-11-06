(function () {
  'use strict';

  var inherits = require('util').inherits;

  /**
   * The base view that subclass views inherit from.
   * @constructor
   */
  function BaseView() {
    var that = this;

    this.ptor = protractor.getInstance();

    if (this.one) {
      var props = Object.keys(this.one).reduce(function (obj, prop) {
        if (that.hasOwnProperty(prop)) return obj;

        obj[prop] = {
          get: function () {
            return that.ptor.findElement(that.one[prop]);
          }
        };

        return obj;
      }, {});

      Object.defineProperties(this, props);
    }
  }

  /**
   * Navigates to the path specified by a subclass
   * @throws {error} Throws an error if path was not set.
   */
  BaseView.prototype.navigate = function () {
    if (this.path == null) throw new Error('Cannot navigate path is not defined!');

    if (this.path !== '') this.path += '/';

    this.ptor.get(this.path);
  };

  /**
   * Tells if the browser url is the same as the one expected on this page.
   * @returns {boolean}
   */
  BaseView.prototype.onPage = function () {
    if (!this.path) throw new Error('Path not set!');

    var re = new RegExp(this.path + '/$'),
      currentUrl = this.ptor.getCurrentUrl();

    return re.test(currentUrl);
  };

  BaseView.extend = function (SubClass) {
    inherits(SubClass, BaseView);
  };

  exports.BaseView = BaseView;

}());
