describe('host profile then', function () {
  'use strict';

  beforeEach(module('server', 'dataFixtures'));

  describe('get host profiles service', function () {
    var throwIfError, CACHE_INITIAL_DATA;

    beforeEach(module(function ($provide) {
      throwIfError = jasmine.createSpy('throwIfError').andReturn(_.identity);
      $provide.value('throwIfError', throwIfError);

      CACHE_INITIAL_DATA = {
        server_profile: [
          {
            default: false,
            initial_state: 'unconfigured',
            managed: false,
            name: 'default',
            resource_uri: '/api/server_profile/default/',
            ui_description: 'An unconfigured server.',
            ui_name: 'Unconfigured Server',
            user_selectable: false,
            worker: false
          },
          {
            default: false,
            initial_state: 'configured',
            managed: true,
            name: 'base_managed',
            resource_uri: '/api/server_profile/base_managed/',
            ui_description: 'A storage server suitable for creating new HA-enabled filesystem targets',
            ui_name: 'Managed Storage Server',
            user_selectable: true,
            worker: false
          },
          {
            default: false,
            initial_state: 'configured',
            managed: false,
            name: 'base_monitored',
            resource_uri: '/api/server_profile/base_monitored/',
            ui_description: 'A storage server suitable for monitoring only',
            ui_name: 'Monitored Storage Server',
            user_selectable: true,
            worker: false
          },
          {
            default: false,
            initial_state: 'configured',
            managed: true,
            name: 'posix_copytool_worker',
            resource_uri: '/api/server_profile/posix_copytool_worker/',
            ui_description: 'An HSM agent node using the POSIX copytool',
            ui_name: 'POSIX HSM Agent Node',
            user_selectable: true,
            worker: true
          },
          {
            default: false,
            initial_state: 'configured',
            managed: true,
            name: 'robinhood_server',
            resource_uri: '/api/server_profile/robinhood_server/',
            ui_description: 'A server running the Robinhood Policy Engine',
            ui_name: 'Robinhood Policy Engine Server',
            user_selectable: true,
            worker: true
          }
        ]
      };
      $provide.constant('CACHE_INITIAL_DATA', CACHE_INITIAL_DATA);
    }));

    var getHostProfiles, runPipeline, flint, hostProfiles;

    beforeEach(inject(function (_getHostProfiles_, _runPipeline_) {
      flint = jasmine.createSpy('flint').andReturn({
        pipeline: [],
        sendGet: jasmine.createSpy('sendGet'),
        addPipe: jasmine.createSpy('addPipe').andCallFake(function (f) {
          this.pipeline.push(f);

          return this;
        })
      });

      runPipeline = _runPipeline_;

      getHostProfiles = _getHostProfiles_;
      hostProfiles = getHostProfiles(flint, [{id: 1}, {id: 2}]);
    }));

    it('should retrieve profiles for given hosts', function () {
      expect(hostProfiles.sendGet).toHaveBeenCalledOnceWith('/host_profile', {
        qs: {
          id__in: [1, 2],
          server_profile__user_selectable: true,
          limit: 0
        }
      });
    });

    it('should register errors', function () {
      expect(throwIfError).toHaveBeenCalledOnce();
    });

    describe('response handling', function () {
      var response, transformed;

      beforeEach(function () {
        response = {
          body: {
            meta: {
              limit: 20,
              next: null,
              offset: 0,
              previous: null,
              total_count: 2
            },
            objects: [
              {
                error: null,
                host_profiles: {
                  address: 'lotus-34vm5.iml.intel.com',
                  host: 28,
                  profiles: {
                    base_managed: [
                      {
                        description: 'ZFS is installed but is unsupported by the Managed Storage Server profile',
                        error: 'Result unavailable while host agent starts',
                        pass: false,
                        test: 'zfs_installed == False'
                      }
                    ],
                    base_monitored: [],
                    posix_copytool_worker: [],
                    robinhood_server: []
                  },
                  resource_uri: '/api/host_profile/28/'
                },
                traceback: null
              },
              {
                error: null,
                host_profiles: {
                  address: 'lotus-34vm6.iml.intel.com',
                  host: 29,
                  profiles: {
                    base_managed: [
                      {
                        description: 'ZFS is installed but is unsupported by the Managed Storage Server profile',
                        error: 'Result unavailable while host agent starts',
                        pass: false,
                        test: 'zfs_installed == False'
                      }
                    ],
                    base_monitored: [],
                    posix_copytool_worker: [],
                    robinhood_server: []
                  },
                  resource_uri: '/api/host_profile/29/'
                },
                traceback: null
              }
            ]
          }
        };

        hostProfiles.pipeline.push(function (resp) {
          transformed = resp;
        });

        runPipeline(hostProfiles.pipeline, response);
      });

      it('should transform into top level profiles', inject(function (transformedHostProfileFixture) {
        expect(transformed).toEqual(transformedHostProfileFixture);
      }));
    });
  });

  describe('create host profiles', function () {
    var createHostProfiles, requestSocket, waitForCommandCompletion, postDeferred;

    beforeEach(module(function ($provide) {
      waitForCommandCompletion = jasmine
        .createSpy('waitForCommandCompletion')
        .andReturn(jasmine.createSpy('waitForCommandCompletionInner').andCallFake(_.identity));
      $provide.value('waitForCommandCompletion', waitForCommandCompletion);

      requestSocket = jasmine.createSpy('requestSocket').andReturn({
        sendPost: jasmine.createSpy('sendPost').andCallFake(),
        end: jasmine.createSpy('end')
      });
      $provide.value('requestSocket', requestSocket);

      $provide.decorator('requestSocket', function ($q, $delegate) {
        postDeferred = $q.defer();

        $delegate.plan().sendPost.andReturn(postDeferred.promise);

        return $delegate;
      });
    }));

    var serverSpark, profile, deferred, transformedHostProfileFixture, promise;

    beforeEach(inject(function ($q, _createHostProfiles_, _transformedHostProfileFixture_) {
      transformedHostProfileFixture = _transformedHostProfileFixture_;

      serverSpark = {
        onceValueThen: jasmine.createSpy('onceValueThen').andCallFake(function () {
          deferred = $q.defer();

          return deferred.promise;
        })
      };

      profile = transformedHostProfileFixture[0];

      createHostProfiles = _createHostProfiles_;
      promise = createHostProfiles(serverSpark, profile, false);
    }));

    it('should return a promise', function () {
      expect(promise).toEqual({
        then: jasmine.any(Function),
        catch: jasmine.any(Function),
        finally: jasmine.any(Function)
      });
    });

    describe('posting profiles', function () {
      beforeEach(inject(function ($rootScope) {
        deferred.resolve({
          body: {
            objects: [
              {
                address: profile.hosts[0].address,
                id: 1,
                server_profile: {
                  initial_state: 'unconfigured'
                }
              },
              {
                address: profile.hosts[1].address,
                id: 2,
                server_profile: {
                  initial_state: 'deployed'
                }
              }
            ]
          }
        });

        postDeferred.resolve({
          body: {
            objects: [
              { commands: [{ command: 1 }] }
            ]
          }
        });

        $rootScope.$digest();
      }));

      it('should post unconfigured host profiles', function () {
        expect(requestSocket.plan().sendPost).toHaveBeenCalledOnceWith('/host_profile', {
          json: {
            objects: [
              {
                host: 1,
                profile: profile.name
              }
            ]
          }
        }, true );
      });

      it('should pass in the commands to wait for command completion', function () {
        expect(waitForCommandCompletion.plan()).toHaveBeenCalledOnceWith({
          body: {
            objects: [
              {
                command: { command: 1 }
              }
            ]
          }
        });
      });

      it('should end the spark', function () {
        expect(requestSocket.plan().end).toHaveBeenCalledOnce();
      });
    });
  });
});
