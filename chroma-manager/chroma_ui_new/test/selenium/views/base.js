(function () {
  'use strict';

  var inherits = require('util').inherits;

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

  BaseView.prototype.navigate = function () {
    if (!this.path) throw new Error('cannot navigate path is falsy!');

    this.ptor.get(this.path + '/');
  };


  BaseView.extend = function (SubClass) {
    inherits(SubClass, BaseView);
  };

  exports.BaseView = BaseView;

}());

