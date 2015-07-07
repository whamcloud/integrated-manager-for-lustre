describe('status controller', function () {
  'use strict';

  beforeEach(module('status'));

  var $scope, jobMonitor, alertMonitor;

  beforeEach(inject(function ($rootScope) {
    $scope = $rootScope.$new();

    spyOn($scope, '$on').andCallThrough();

    jobMonitor = {
      end: jasmine.createSpy('end')
    };

    alertMonitor = {
      end: jasmine.createSpy('end')
    };
  }));
});

[
  {
    name: 'Job Monitor',
    type: 'job',
    api: '/job/',
    jsonMask: 'objects(write_locks,read_locks,description)',
    qs: {
      limit: 0,
      state__in: ['pending', 'tasked']
    }
  },
  {
    name: 'Alert Monitor',
    type: 'alert',
    api: '/alert/',
    jsonMask: 'objects(alert_item,message)',
    qs: {
      limit: 0,
      active: true
    }
  }
].forEach(function testEachMonitor (monitor) {
    'use strict';

    describe(monitor.name, function () {

      var requestSocket;

      beforeEach(module('status', function ($provide) {
        requestSocket = jasmine.createSpy('requestSocket').andReturn({
          sendGet: jasmine.createSpy('sendGet')
        });

        $provide.value('requestSocket', requestSocket);
      }));

      var service, result;

      if (monitor.type === 'job') {
        beforeEach(inject(function (_jobMonitor_) {
          service = _jobMonitor_;
          result = service();
        }));
      } else if (monitor.type === 'alert') {
        beforeEach(inject(function (_alertMonitor_) {
          service = _alertMonitor_;
          result = service();
        }));
      }

      it('should create a spark', function () {
        expect(requestSocket).toHaveBeenCalledOnce();
      });

      it('should get pending jobs', function () {
        expect(result.sendGet).toHaveBeenCalledOnceWith(monitor.api, {
          jsonMask: monitor.jsonMask,
          qs: monitor.qs
        });
      });
    });
  });
