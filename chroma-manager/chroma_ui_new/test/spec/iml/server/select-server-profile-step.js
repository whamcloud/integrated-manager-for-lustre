describe('select server profile', function () {
  'use strict';

  beforeEach(module('server', 'dataFixtures'));

  describe('select server profile step ctrl', function () {
    var $scope, $stepInstance, data,
      createHostProfiles, hostProfileSpark, selectServerProfileStep;

    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();
      $stepInstance = {
        transition: jasmine.createSpy('transition')
      };

      hostProfileSpark = {
        onValue: jasmine.createSpy('onValue'),
        end: jasmine.createSpy('end')
      };

      createHostProfiles = jasmine.createSpy('createHostProfiles');

      data = {
        pdsh: 'storage0.localdomain'
      };

      selectServerProfileStep = $controller('SelectServerProfileStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data,
        hostProfileSpark: hostProfileSpark,
        createHostProfiles: createHostProfiles
      });
    }));

    it('should setup the controller', function () {
      expect(selectServerProfileStep).toEqual({
        pdsh: data.pdsh,
        transition: jasmine.any(Function),
        onSelected: jasmine.any(Function),
        getHostPath: jasmine.any(Function),
        pdshUpdate: jasmine.any(Function),
        close: jasmine.any(Function)
      });
    });

    it('should call hostProfileSpark.onValue', function () {
      expect(hostProfileSpark.onValue)
        .toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    describe('transition', function () {
      var action;
      beforeEach(function () {
        action = 'previous';
        selectServerProfileStep.transition(action);
      });

      it('should end the hostProfileSpark', function () {
        expect(hostProfileSpark.end).toHaveBeenCalledOnce();
      });

      it('should call transition on the step instance', function () {
        expect($stepInstance.transition).toHaveBeenCalledOnceWith(action, {
          data: data
        });
      });
    });

    describe('receiving data change on hostProfileSpark', function () {
      var transformedHostProfileFixture;
      beforeEach(inject(function (_transformedHostProfileFixture_) {
        transformedHostProfileFixture = _transformedHostProfileFixture_;

        hostProfileSpark.onValue.mostRecentCall.args[1](transformedHostProfileFixture);
      }));

      it('should set the profiles', function () {
        expect(selectServerProfileStep.profiles).toEqual(transformedHostProfileFixture);
      });

      describe('receiving more data', function () {
        beforeEach(function () {
          hostProfileSpark.onValue.mostRecentCall.args[1](transformedHostProfileFixture);
        });

        it('should keep the same profile', function () {
          expect(selectServerProfileStep.profile).toEqual(transformedHostProfileFixture[0]);
        });
      });

      describe('onSelected', function () {
        beforeEach(function () {
          selectServerProfileStep.onSelected(transformedHostProfileFixture[0]);
        });

        it('should set overridden to false', function () {
          expect(selectServerProfileStep.overridden).toEqual(false);
        });

        it('should set the profile on the scope', function () {
          expect(selectServerProfileStep.profile).toEqual(transformedHostProfileFixture[0]);
        });
      });
    });

    describe('get host path', function () {
      var item;
      beforeEach(function () {
        item = {
          address: 'address'
        };
      });

      it('should retrieve the host address', function () {
        expect(selectServerProfileStep.getHostPath(item)).toEqual(item.address);
      });
    });

    describe('pdsh update', function () {
      var pdsh, hostnames, hostnamesHash;
      beforeEach(function () {
        pdsh = 'test[001-002].localdomain';
        hostnames = ['test001.localdomain', 'test002.localdomain'];
        hostnamesHash = {
          'test001.localdomain': 1,
          'test002.localdomain': 1
        };
      });

      beforeEach(function () {
        selectServerProfileStep.pdshUpdate(pdsh, hostnames, hostnamesHash);
      });

      it('should have the hostnamesHash', function () {
        expect(selectServerProfileStep.hostnamesHash).toEqual(hostnamesHash);
      });
    });
  });

  describe('selectServerProfileStep', function () {
    var selectServerProfileStep;

    beforeEach(inject(function (_selectServerProfileStep_) {
      selectServerProfileStep = _selectServerProfileStep_;
    }));

    it('should contain the appropriate properties', function () {
      expect(selectServerProfileStep).toEqual({
        templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
        controller: 'SelectServerProfileStepCtrl as selectServerProfile',
        onEnter: ['data', 'createOrUpdateHostsThen', 'getHostProfiles',
          'waitForCommandCompletion', 'showCommand', jasmine.any(Function)],
        transition: jasmine.any(Function)
      });
    });

    it('should transition to the server status step', function () {
      var steps = {
        serverStatusStep: {}
      };

      expect(selectServerProfileStep.transition(steps)).toEqual(steps.serverStatusStep);
    });

    describe('on enter', function () {
      var onEnter, data, createOrUpdateHostsThen,
        getHostProfiles, waitForCommandCompletion, result,
        response;

      beforeEach(inject(function ($q, $rootScope) {
        data = {
          flint: jasmine.createSpy('flint'),
          servers: [],
          serverSpark: {}
        };

        response = {
          body: {
            objects: [
              {
                command_and_host: {
                  command: {
                    cancelled: false,
                    complete: false,
                    created_at: '2014-12-10T17:11:00.852148+00:00',
                    dismissed: false,
                    errored: false,
                    id: '390',
                    jobs: [
                      '/api/job/390/'
                    ],
                    logs: '',
                    message: 'Setting up host lotus-34vm5.iml.intel.com',
                    resource_uri: '/api/command/390/'
                  },
                  host: {
                    address: 'lotus-34vm5.iml.intel.com',
                    available_actions: [],
                    available_jobs: [],
                    available_transitions: [],
                    boot_time: null,
                    client_mounts: [],
                    content_type_id: 35,
                    corosync_reported_up: false,
                    fqdn: 'lotus-34vm5.iml.intel.com',
                    id: '32',
                    immutable_state: true,
                    install_method: 'existing_keys_choice',
                    label: 'lotus-34vm5.iml.intel.com',
                    locks: {
                      read: [],
                      write: [
                        390
                      ]
                    },
                    member_of_active_filesystem: false,
                    needs_fence_reconfiguration: false,
                    needs_update: false,
                    nids: [],
                    nodename: 'lotus-34vm5',
                    private_key: null,
                    private_key_passphrase: null,
                    properties: '{}',
                    resource_uri: '/api/host/32/',
                    root_pw: null,
                    server_profile: {
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
                    state: 'undeployed',
                    state_modified_at: '2014-12-10T17:11:00.845748+00:00',
                    version: null
                  }
                },
                error: null,
                traceback: null
              },
              {
                command_and_host: {
                  command: {
                    cancelled: false,
                    complete: false,
                    created_at: '2014-12-10T17:11:03.280882+00:00',
                    dismissed: false,
                    errored: false,
                    id: '391',
                    jobs: [
                      '/api/job/391/'
                    ],
                    logs: '',
                    message: 'Setting up host lotus-34vm6.iml.intel.com',
                    resource_uri: '/api/command/391/'
                  },
                  host: {
                    address: 'lotus-34vm6.iml.intel.com',
                    available_actions: [],
                    available_jobs: [],
                    available_transitions: [],
                    boot_time: null,
                    client_mounts: [],
                    content_type_id: 35,
                    corosync_reported_up: false,
                    fqdn: 'lotus-34vm6.iml.intel.com',
                    id: '33',
                    immutable_state: true,
                    install_method: 'existing_keys_choice',
                    label: 'lotus-34vm6.iml.intel.com',
                    locks: {
                      read: [],
                      write: [
                        391
                      ]
                    },
                    member_of_active_filesystem: false,
                    needs_fence_reconfiguration: false,
                    needs_update: false,
                    nids: [],
                    nodename: 'lotus-34vm6',
                    private_key: null,
                    private_key_passphrase: null,
                    properties: '{}',
                    resource_uri: '/api/host/33/',
                    root_pw: null,
                    server_profile: {
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
                    state: 'undeployed',
                    state_modified_at: '2014-12-10T17:11:03.273059+00:00',
                    version: null
                  }
                },
                error: null,
                traceback: null
              }
            ]
          }
        };

        createOrUpdateHostsThen = jasmine.createSpy('createOrUpdateHostsThen')
          .andReturn($q.when(_.cloneDeep(response)));
        waitForCommandCompletion = jasmine.createSpy('waitForCommandCompletion')
          .andReturn(_.identity);
        getHostProfiles = jasmine.createSpy('getHostProfiles').andReturn({
          onceValueThen: jasmine.createSpy('onceValueThen').andReturn($q.when('gotHostProfiles'))
        });

        onEnter = _.last(selectServerProfileStep.onEnter);

        result = onEnter(data, createOrUpdateHostsThen, getHostProfiles, waitForCommandCompletion, true);
        $rootScope.$apply();
      }));

      it('should create or update the hosts', function () {
        expect(createOrUpdateHostsThen).toHaveBeenCalledOnceWith(data.servers, data.serverSpark);
      });

      it('should wait for command completion', function () {
        expect(waitForCommandCompletion).toHaveBeenCalledOnceWith(true);
      });

      it('should call getHostProfiles', function () {
        var hosts = _.fmap(_.pluckPath('command_and_host.host'), response.body.objects);

        expect(getHostProfiles).toHaveBeenCalledOnceWith(data.flint, hosts);
      });

      it('should return data and a hostProfileSpark promise', function () {
        expect(result).toEqual({
          data: data,
          hostProfileSpark: {
            then: jasmine.any(Function),
            catch: jasmine.any(Function),
            finally: jasmine.any(Function)
          }
        });
      });
    });
  });
});
