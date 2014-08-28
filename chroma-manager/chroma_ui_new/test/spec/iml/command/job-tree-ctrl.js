describe('job tree', function () {
  'use strict';

  beforeEach(module('command'));

  describe('job tree ctrl', function () {

    var $scope, jobTree, getJobSpark, GROUPS, openStepModal, job;

    beforeEach(inject(function ($rootScope, $controller) {
      getJobSpark = jasmine.createSpy('getJobSpark').andReturn({
        sendGet: jasmine.createSpy('sendGet'),
        sendPut: jasmine.createSpy('sendPut'),
        onValue: jasmine.createSpy('onValue'),
        end: jasmine.createSpy('end')
      });

      GROUPS = {};

      openStepModal = jasmine.createSpy('openStepModal');

      $scope = $rootScope.$new();

      $scope.command = {
        jobIds: []
      };

      spyOn($scope, '$on').andCallThrough();

      job = {
        id: '2',
        resource_uri: '/api/job/2/',
        available_transitions: [{}]
      };

      $controller('JobTreeCtrl', {
        $scope: $scope,
        getJobSpark: getJobSpark,
        GROUPS: GROUPS,
        openStepModal: openStepModal
      });

      jobTree = $scope.jobTree;
    }));

    it('should have a groups property', function () {
      expect(jobTree.GROUPS).toBe(GROUPS);
    });

    it('should have a jobs property', function () {
      expect(jobTree.jobs).toEqual([]);
    });

    it('should have a method to open the step modal', function () {
      jobTree.openStep(job);

      expect(openStepModal).toHaveBeenCalledOnceWith(job);
    });

    it('should tell if the job should show it\'s transition', function () {
      expect(jobTree.showTransition(job)).toBe(true);
    });

    it('should get the job', function () {
      expect(getJobSpark.plan().sendGet).toHaveBeenCalledOnceWith('/job', {
        qs: {
          id__in: [],
          limit: 0
        }
      });
    });

    it('should listen for jobs', function () {
      expect(getJobSpark.plan().onValue).toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    it('should set the jobs', function () {
      var response = {
        body: [job]
      };

      getJobSpark.plan().onValue.mostRecentCall.args[1](response);

      expect(jobTree.jobs).toEqual([job]);
    });

    it('should listen for destroy', function () {
      expect($scope.$on).toHaveBeenCalledOnceWith('$destroy', jasmine.any(Function));
    });

    it('should end the spark on destroy', function () {
      $scope.$on.mostRecentCall.args[1]();

      expect(getJobSpark.plan().end).toHaveBeenCalledOnce();
    });

    describe('do transition', function () {
      var ack;

      beforeEach(function () {
        jobTree.doTransition(job, 'cancelled');

        ack = getJobSpark.plan().sendPut.mostRecentCall.args[2];
      });

      it('should put the transition', function () {
        expect(getJobSpark.plan().sendPut).toHaveBeenCalledOnceWith(job.resource_uri, {
          json: _.extend({ state: 'cancelled' }, job)
        }, jasmine.any(Function));
      });

      it('should throw on error', function () {
        expect(shouldThrow).toThrow();

        function shouldThrow () {
          ack({ error: {} });
        }
      });

      it('should hide transition while pending', function () {
        expect(jobTree.showTransition(job)).toBe(false);
      });

      it('should show transition when finished', function () {
        ack({ body: job });

        expect(jobTree.showTransition(job)).toBe(true);
      });
    });
  });

  describe('get job spark', function () {
    var requestSocket, jobTree;

    beforeEach(module(function ($provide) {
      requestSocket = jasmine.createSpy('requestSocket').andReturn({
        addPipe: jasmine.createSpy('addPipe')
      });

      jobTree = jasmine.createSpy('jobTree');

      $provide.value('requestSocket', requestSocket);
      $provide.value('jobTree', jobTree);
    }));

    var getJobSpark, spark;

    beforeEach(inject(function (_getJobSpark_) {
      getJobSpark = _getJobSpark_;
      spark = getJobSpark();
    }));

    it('should create a spark', function () {
      expect(requestSocket).toHaveBeenCalledOnce();
    });

    it('should return a spark', function () {
      expect(spark).toEqual(requestSocket.plan());
    });

    it('should add a pipe', function () {
      expect(spark.addPipe).toHaveBeenCalledOnceWith(jasmine.any(Function));
    });

    describe('convert to tree', function () {
      var pipe, response;

      beforeEach(function () {
        pipe = spark.addPipe.mostRecentCall.args[0];

        response = {
          body: {
            objects: [{}]
          }
        };
      });

      it('should throw on error', function () {
        expect(shouldThrow).toThrow();

        function shouldThrow () {
          pipe({ error: {} });
        }
      });

      it('should convert to a tree', function () {
        pipe(response);

        expect(jobTree).toHaveBeenCalledOnceWith([{}]);
      });

      it('should return the converted tree', function () {
        jobTree.andReturn([{ converted: true }]);

        var result = pipe(response);

        expect(result.body).toEqual([{ converted: true }]);
      });
    });
  });
});
