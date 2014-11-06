describe('action dropdown directive', function () {
  'use strict';

  var handleAction, openCommandModal, createCommandSpark;

  beforeEach(module('action-dropdown-module', 'templates', 'ui.bootstrap.dropdown', 'pasvaz.bindonce',
    function ($provide) {
      handleAction = jasmine.createSpy('handleAction').andReturn({
        then: jasmine.createSpy('then').andReturn({
          finally: jasmine.createSpy('finally')
        })
      });

      openCommandModal = jasmine.createSpy('openCommandModal');

      $provide.value('handleAction', handleAction);
      $provide.value('openCommandModal', openCommandModal);

      createCommandSpark = jasmine.createSpy('createCommandSpark')
        .andReturn({
          end: jasmine.createSpy('end')
        });
      $provide.value('createCommandSpark', createCommandSpark);
    }));

  var $scope, gen;

  beforeEach(inject(function ($compile, $rootScope) {
    $scope = $rootScope.$new();

    $scope.item = {
      available_actions: [
        {
          args: {
            host_id: 2
          },
          class_name: 'ShutdownHostJob',
          confirmation: 'Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will \
be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.',
          display_group: 2,
          display_order: 60,
          long_description: 'Initiate an orderly shutdown on the host. Any HA-capable targets running on the host will \
be failed over to a peer. Non-HA-capable targets will be unavailable until the host has been restarted.',
          verb: 'Shutdown'
        },
        {
          args: {
            host_id: 2
          },
          class_name: 'RebootHostJob',
          confirmation: null,
          display_group: 2,
          display_order: 50,
          long_description: 'Initiate a reboot on the host. Any HA-capable targets running on the host will be \
failed over to a peer. Non-HA-capable targets will be unavailable until the host has finished rebooting.',
          verb: 'Reboot'
        }
      ],
      locks: {
        write: []
      }
    };

    gen = function gen (actionsProperty, tooltipPlacement) {
      var str = '<action-dropdown record="item"></action-dropdown>'.sprintf(
        actionsProperty ? ' actions-property="%s" '.sprintf(actionsProperty) : '',
        tooltipPlacement ? ' tooltip-placement="%s" '.sprintf(tooltipPlacement) : ''
      );

      return $compile(str)($scope);
    };
  }));

  describe('layout', function () {
    var el;

    beforeEach(function () {
      el = gen();
      $scope.$digest();
    });

    it('should have an actions dropdown', function () {
      expect(el.find('button').html().trim()).toEqual('Actions <span class="caret"></span>');
    });

    it('should put the highest order last', function () {
      expect(el.find('.dropdown-menu a')[1].innerHTML).toEqual('Shutdown');
    });

    it('should put the lowest order first', function () {
      expect(el.find('.dropdown-menu a')[0].innerHTML).toEqual('Reboot');
    });

    it('should show the dropdown on click', function () {
      el.find('button')[0].click();

      expect(el.find('div').hasClass('open')).toBe(true);
    });

    it('should handle the action when clicking an item', function () {
      el.find('button')[0].click();

      el.find('li a')[0].click();

      expect(handleAction).toHaveBeenCalledOnceWith($scope.item, $scope.item.available_actions[0]);
    });
  });
});
