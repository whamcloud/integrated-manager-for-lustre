describe('step modal', function () {
  'use strict';

  beforeEach(module('command'));

  describe('step modal controller', function () {

    var $scope, $modalInstance, stepModal, steps, job;

    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();

      spyOn($scope, '$on').andCallThrough();

      $modalInstance = {
        close: jasmine.createSpy('close')
      };

      steps = {
        end: jasmine.createSpy('end'),
        onValue: jasmine.createSpy('onValue')
      };

      job = {
        end: jasmine.createSpy('end'),
        onValue: jasmine.createSpy('onValue')
      };

      $controller('StepModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        steps: steps,
        job: job
      });

      stepModal = $scope.stepModal;
    }));

    it('should listen for destroy', function () {
      expect($scope.$on).toHaveBeenCalledOnceWith('$destroy', jasmine.any(Function));
    });

    describe('destroy', function () {
      beforeEach(function () {
        $scope.$on.mostRecentCall.args[1]();
      });

      it('should end steps', function () {
        expect(steps.end).toHaveBeenCalledOnce();
      });

      it('should end job', function () {
        expect(job.end).toHaveBeenCalledOnce();
      });
    });

    it('should have a list of steps', function () {
      expect(stepModal.steps).toEqual([]);
    });

    it('should open the first accordion', function () {
      expect(stepModal.accordion0).toBe(true);
    });

    it('should close the modal', function () {
      stepModal.close();

      expect($modalInstance.close).toHaveBeenCalledOnceWith('close');
    });

    var states = {
      'waiting to run': {
        state: 'pending'
      },
      running: {
        state: 'tasked'
      },
      cancelled: {
        cancelled: true,
        state: 'complete'
      },
      failed: {
        errored: true,
        state: 'complete'
      },
      succeeded: {
        state: 'complete'
      }
    };

    Object.keys(states).forEach(function assertState (state) {
      it('should return the adjective ' + state + ' for the given job', function () {
        var result = stepModal.getJobAdjective(states[state]);

        expect(result).toEqual(state);
      });
    });

    it('should listen for job data', function () {
      expect(job.onValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
    });

    it('should listen for step data', function () {
      expect(steps.onValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
    });
  });

  describe('open step modal', function () {
    var $modal;

    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('open')
      };

      $provide.value('$modal', $modal);
    }));

    var openStepModal, requestSocket, job;

    beforeEach(inject(function (_openStepModal_) {
      openStepModal = _openStepModal_;

      job = {
        id: '1',
        steps: [
          '/api/step/1/'
        ]
      };

      requestSocket = jasmine.createSpy('requestSocket').andReturn({
        setLastData: jasmine.createSpy('setLastData'),
        sendGet: jasmine.createSpy('sendGet')
      });

      openStepModal(job);
    }));

    it('should open the modal with the expected object', function () {
      expect($modal.open).toHaveBeenCalledOnceWith({
        templateUrl: 'iml/command/assets/html/step-modal.html',
        controller: 'StepModalCtrl',
        windowClass: 'step-modal',
        resolve: {
          job: ['requestSocket', jasmine.any(Function)],
          steps: ['requestSocket', jasmine.any(Function)]
        }
      });
    });

    describe('get a job', function () {
      beforeEach(function () {
        $modal.open.mostRecentCall.args[0].resolve.job[1](requestSocket);
      });

      it('should set last data', function () {
        expect(requestSocket.plan().setLastData).toHaveBeenCalledOnceWith({ body: job });
      });

      it('should get the job', function () {
        expect(requestSocket.plan().sendGet).toHaveBeenCalledOnceWith('/job/1');
      });
    });

    describe('get steps', function () {
      beforeEach(function () {
        $modal.open.mostRecentCall.args[0].resolve.steps[1](requestSocket);
      });

      it('should get the steps', function () {
        expect(requestSocket.plan().sendGet).toHaveBeenCalledOnceWith('/step', {
          qs: {
            id__in: ['1'],
            limit: 0
          }
        });
      });
    });
  });
});
