describe('fancy select', function () {
  'use strict';

  var $scope, node, button, buttonGroup, ul, customSelected;
  beforeEach(module('fancy-select', 'templates', 'ui.bootstrap.dropdown'));

  describe('fancy select without data', function () {
    beforeEach(inject(function ($rootScope, $compile) {
      buttonGroup = angular.element('<fancy-select-box on-selected="customOnSelected(item)"></fancy-select-box>');

      $scope = $rootScope.$new();

      node = $compile(buttonGroup)($scope);

      $scope.$digest();
    }));

    it('should not have any li tags', function () {
      expect(buttonGroup.find('ul li').length).toEqual(0);
    });
  });

  describe('fancy select with data', function () {
    beforeEach(inject(function ($rootScope, $compile) {
      buttonGroup = angular
        .element('<fancy-select-box data="myData" on-selected="customOnSelected(item)"></fancy-select-box>');

      $scope = $rootScope.$new();

      $scope.myData = [
        {
          id: 1,
          labelType: 'label-default',
          label: 'Incompatible',
          caption: 'Managed Storage Server'
        },
        {
          id: 2,
          caption: 'Robinhood Policy Engine Server'
        },
        {
          id: 3,
          caption: 'Monitored Storage Server'
        },
        {
          id: 4,
          caption: 'POSIX HSM Agent Node'
        }
      ];

      $scope.customOnSelected = function (item) {
        customSelected = item.caption;
      };

      node = $compile(buttonGroup)($scope);

      $scope.$digest();

      button = buttonGroup.find('button');
      ul = buttonGroup.find('ul');
    }));

    it('should contain a button to open the drop down', function () {
      expect(button).toBeShown();
    });

    it('should contain an invisible list', function () {
      expect(buttonGroup.hasClass('open')).toEqual(false);
    });

    it('should initially select the first item', function () {
      expect(customSelected).toEqual($scope.myData[0].caption);
    });

    describe('open and closing drop down', function () {
      beforeEach(function () {
        button.trigger('click');
      });

      it('should display the drop down', function () {
        expect(buttonGroup.hasClass('open')).toEqual(true);
      });

      it('should close the drop down after clicking the button while it is open', function () {
        button.trigger('click');
        expect(buttonGroup.hasClass('open')).toEqual(false);
      });

      it('should close the drop down after clicking outside the drop down', function () {
        $('body').trigger('click');
        expect(buttonGroup.hasClass('open')).toEqual(false);
      });

      describe('selecting an item', function () {
        var expected;
        beforeEach(function () {
          customSelected = '';
          expected = 'Robinhood Policy Engine Server';
          buttonGroup.find('ul li a').eq(1).trigger('click');
        });

        it('should close the drop down after selecting the second item', function () {
          expect(buttonGroup.hasClass('open')).toEqual(false);
        });

        it('should have the content of the second item selected in the button', function () {
          expect(button.find('span').html()).toEqual(expected);
        });

        it('should call the onSelected behavior binding', function () {
          expect(customSelected).toEqual(expected);
        });
      });
    });
  });
});
