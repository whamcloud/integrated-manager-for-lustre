(function () {
  'use strict';

  function Selectors() {
    this.EULA = '.eula-modal';

    this.WELL = this.EULA + ' .well';

    this.ACCEPT = this.EULA + ' .btn-success';

    this.REJECT = this.EULA + ' .btn-danger';
  }

  var selectors = Object.freeze(new Selectors());

  function Locators() {
    this.WELL = protractor.By.css(selectors.WELL);

    this.ACCEPT = protractor.By.css(selectors.ACCEPT);

    this.REJECT = protractor.By.css(selectors.REJECT);
  }

  exports.selectors = selectors;
  exports.locators = Object.freeze(new Locators());
}());
