'use strict';

var format = require('util').format;
var server = require('../views/server');

describe('server screen', function () {
  beforeEach(function () {
    server.navigate();
  });

  describe('add servers', function () {
    beforeEach(function () {
      server.removeAll();
      server.addServers();
    });

    it('should have added two servers', function () {
      expect(server.rows.count()).toBe(2);
    });
  });

  describe('wait for server table', function () {
    beforeEach(function () {
      server.waitForServerTable();
    });

    it('should result in two servers in lnet up state', function () {
      expect(server.lnetState.count()).toBe(2);
    });

    [
      {
        number: 'first',
        name: 'kp-ss-storage-appliance-1'
      },
      {
        number: 'second',
        name: 'kp-ss-storage-appliance-2'
      }
    ].forEach(function runServerDetailModalTest (modal) {
        describe(modal.number + ' detail modal', function () {
          beforeEach(function () {
            server[format('open%sDetailModal', modal.number[0].toUpperCase() + modal.number.slice(1))]();
          });
          it('should have title of ' + modal.name, function () {
            expect(server[format('%sServerDetailLink', modal.number)].getText()).toBe(modal.name);
          });
        });
      });

    describe('entries button', function () {

      beforeEach(function () {
        server.openEntriesDropdown();
      });

      it('should default to 10 entries', function () {
        server.entriesButton.getText()
          .then(function expectTenText (text) {
            expect(text).toContain('10');
          });
      });

      [25, 50, 100].forEach(function expectEntry (entryNumber) {
        it('should change the number of entries to ' + entryNumber, function () {
          $(format(server.ENTRIES_NUMBER_LINK, entryNumber)).click();

          server.entriesButton.getText()
            .then(function expectTextToContainANumber (text) {
              expect(text).toContain(entryNumber);
            });
        });
      });

    });

    ['detectFileSystems', 'rewriteTargetConfiguration', 'installUpdates']
      .forEach(function testEditModes (editModeName) {
        describe('edit mode' + ' ' + editModeName, function () {
          beforeEach(function () {
            server.editMode[editModeName]();
          });

          it('should default to a disabled go button', function () {
            expect(browser.isElementPresent(server.editMode[editModeName + 'EditModeButtonDisabled'])).toBe(true);
          });

          describe('when select all is clicked', function () {
            beforeEach(function () {
              server.editMode.selectAllButton.click();
            });
            it('should display 2 selected buttons', function () {
              expect(server.editMode.selectedButtons.count()).toBe(2);
            });

            it('should enable the go button', function () {
              expect(browser.isElementPresent(server.editMode[editModeName + 'EditModeButton'])).toBe(true);
            });
          });
        });
      });

    describe('remove servers', function () {
      beforeEach(function () {
        server.removeAll();
      });

      it('should remove servers', function () {
        expect(server.rows.count()).toBe(0);
      });
    });

  });

});
