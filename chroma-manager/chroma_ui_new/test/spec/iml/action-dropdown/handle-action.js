describe('handle action', function () {
  'use strict';

  var requestSocket, openConfirmActionModal,
    openConfirmActionModalDeferred, sendPutDeferred, sendPostDeferred;

  beforeEach(module('action-dropdown-module', function ($provide) {
    requestSocket = jasmine.createSpy('requestSocket');

    $provide.value('requestSocket', requestSocket);
    $provide.decorator('requestSocket', function ($q, $delegate) {
      sendPutDeferred = $q.defer();
      sendPostDeferred = $q.defer();

      return $delegate.andReturn({
        sendPut: jasmine.createSpy('sendPut').andReturn(sendPutDeferred.promise),
        sendPost: jasmine.createSpy('sendPost').andReturn(sendPostDeferred.promise)
      });
    });

    openConfirmActionModal = jasmine.createSpy('openConfirmActionModal');

    $provide.value('openConfirmActionModal', openConfirmActionModal);
    $provide.decorator('openConfirmActionModal', function ($q, $delegate) {
      openConfirmActionModalDeferred = $q.defer();

      return $delegate.andReturn({
        result: openConfirmActionModalDeferred.promise
      });
    });
  }));

  var $rootScope, handleAction;

  beforeEach(inject(function (_$rootScope_, _handleAction_) {
    $rootScope = _$rootScope_;
    handleAction = _handleAction_;
  }));

  describe('job', function () {
    var record, action;

    beforeEach(function () {
      record = {
        label: 'foo bar'
      };

      action = {
        verb: 'foo',
        class_name: 'bar',
        args: {
          some: 'stuff'
        },
        confirmation: 'Are you sure you want to foo bar?'
      };
    });

    it('should open the confirm modal if there is confirmation', function () {
      handleAction(record, action);

      expect(openConfirmActionModal)
        .toHaveBeenCalledOnceWith('foo(foo bar)', [ 'Are you sure you want to foo bar?' ]);
    });

    it('should not open the confirm modal without confirmation', function () {
      delete action.confirmation;

      handleAction(record, action);

      expect(openConfirmActionModal).not.toHaveBeenCalled();
    });

    it('should send the job after confirmation', function () {
      handleAction(record, action);

      openConfirmActionModalDeferred.resolve();

      $rootScope.$digest();

      expect(requestSocket.plan().sendPost).toHaveBeenCalledOnceWith('/command', {
        json: {
          jobs: [{
            class_name: 'bar',
            args: {
              some: 'stuff'
            }
          }],
          message: 'foo(foo bar)'
        }
      }, true);
    });
  });

  describe('conf param', function () {
    var record, action;

    beforeEach(function () {
      record = {};
      action = {
        param_key: 'some',
        param_value: 'value',
        mdt: {
          resource: 'target',
          id: '1',
          conf_params: []
        }
      };

      handleAction(record, action);
    });

    it('should put the new param', function () {
      expect(requestSocket.plan().sendPut).toHaveBeenCalledOnceWith('/target/1', {
        json: {
          resource: 'target',
          id: '1',
          conf_params: []
        }
      }, true);
    });
  });

  describe('state change', function () {
    var record, action;

    beforeEach(function () {
      record = {
        resource_uri: '/api/target/2'
      };

      action = {
        state: 'stopped'
      };

      handleAction(record, action);
    });

    it('should perform a dry run', function () {
      expect(requestSocket.plan().sendPut).toHaveBeenCalledOnceWith(record.resource_uri, {
        json: {
          dry_run: true,
          state: 'stopped'
        }
      }, true);
    });

    describe('dry run', function () {
      var response;

      beforeEach(function () {
        response = {
          body: {
            transition_job: {
              description: 'It\'s gonna do stuff!'
            },
            dependency_jobs: [
              {
                requires_confirmation: true,
                description: 'This will do stuff'
              }
            ]
          }
        };

        sendPutDeferred.resolve(response);

        $rootScope.$digest();
      });

      it('should open the confirm action modal', function () {
        expect(openConfirmActionModal)
          .toHaveBeenCalledOnceWith('It\'s gonna do stuff!', ['This will do stuff']);
      });

      it('should send the new state after confirm', function () {
        openConfirmActionModalDeferred.resolve();

        $rootScope.$digest();

        expect(requestSocket.plan().sendPut).toHaveBeenCalledOnceWith('/api/target/2', {
          json: {
            state: 'stopped'
          }
        }, true);
      });
    });
  });
});
