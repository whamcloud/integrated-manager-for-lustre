describe('override action click', function () {
  'use strict';

  var record, action, ADD_SERVER_STEPS, openAddServerModal, overrideActionClick, spark,
    overrideActionClickService, $scope;

  beforeEach(module('server', function ($provide) {
    ADD_SERVER_STEPS = {
      ADD: 'add',
      STATUS: 'status',
      SELECT_PROFILE: 'select profile'
    };
    $provide.constant('ADD_SERVER_STEPS', ADD_SERVER_STEPS);

    openAddServerModal = jasmine.createSpy('openAddServerModal');
    $provide.value('openAddServerModal', openAddServerModal);
    $provide.decorator('openAddServerModal', function ($q, $delegate) {
      return $delegate.andReturn({
        result: $q.when()
      });
    });
  }));

  beforeEach(inject(function (_overrideActionClick_, $rootScope) {
    $scope = $rootScope.$new();
    overrideActionClick = _overrideActionClick_;

    record = {
      state: 'undeployed',
      install_method: 'root_password'
    };

    action = {
      state: 'deployed'
    };

    spark = jasmine.createSpy('spark');

    overrideActionClickService = overrideActionClick(spark);
  }));

  it('should be a function', function () {
    expect(overrideActionClickService).toEqual(jasmine.any(Function));
  });

  it('should fallback without an action state', function () {
    overrideActionClickService(record, {}).then(function (resp) {
      expect(resp).toEqual('fallback');
    });

    $scope.$digest();
  });

  [
    // add step
    {
      record: {
        state: 'undeployed',
        install_method: 'root_password'
      },
      action: {
        state: 'deployed'
      },
      step: 'add'
    },
    // server status step
    {
      record: {
        state: 'undeployed',
        install_method: 'existing_keys_choice'
      },
      action: {
        state: 'deployed'
      },
      step: 'status'
    },
    // select profile
    {
      record: {
        state: 'pending',
        install_method: 'existing_keys_choice',
        server_profile: {
          initial_state: 'unconfigured'
        }
      },
      action: {
        state: 'deployed'
      },
      step: 'select profile'
    }
  ].forEach(function testStep (data) {
    describe('openAddServerModal based on step', function () {
      it('should open the add server modal when needed', function () {
        overrideActionClickService(data.record, data.action).then(function () {
          expect(openAddServerModal).toHaveBeenCalledOnceWith(spark, data.record, data.step);
        });

        $scope.$digest();
      });
    });
  });
});
