describe('select server profile', function () {
  'use strict';

  beforeEach(module('server'));

  describe('select server profile step ctrl', function () {
    var $scope, $stepInstance, data, off, CACHE_INITIAL_DATA;

    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();
      $stepInstance = {
        transition: jasmine.createSpy('transition')
      };
      off = jasmine.createSpy('off');
      data = {
        hostProfileSpark: {
          onValue: jasmine.createSpy('onValue').andReturn(off)
        },
        server: {
          pdsh: 'storage0.localdomain'
        }
      };

      CACHE_INITIAL_DATA = {
        server_profile: [
          {
            initial_state: 'configured',
            managed: true,
            name: 'base_managed',
            default: false,
            worker: false,
            user_selectable: true,
            ui_description: 'A storage server suitable for creating new HA-enabled filesystem targets',
            ui_name: 'Managed storage server',
            resource_uri: '/api/server_profile/base_managed/'
          },
          {
            initial_state: 'configured',
            managed: false,
            name: 'base_monitored',
            default: false,
            worker: false,
            user_selectable: true,
            ui_description: 'A storage server suitable for monitoring only',
            ui_name: 'Monitored storage server',
            resource_uri: '/api/server_profile/base_monitored/'
          },
          {
            initial_state: 'configured',
            managed: true,
            name: 'posix_copytool_worker',
            default: false,
            worker: true,
            user_selectable: true,
            ui_description: 'An HSM agent node using the POSIX copytool',
            ui_name: 'POSIX HSM Agent Node',
            resource_uri: '/api/server_profile/posix_copytool_worker/'
          },
          {
            initial_state: 'configured',
            managed: true,
            name: 'robinhood_server',
            default: false,
            worker: true,
            user_selectable: true,
            ui_description: 'A server running the Robinhood Policy Engine',
            ui_name: 'Robinhood Policy Engine Server',
            resource_uri: '/api/server_profile/robinhood_server/'
          }
        ]
      };

      $controller('SelectServerProfileStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data,
        CACHE_INITIAL_DATA: CACHE_INITIAL_DATA
      });
    }));

    it('should contain a transition method', function () {
      expect($scope.selectServerProfile.transition).toEqual(jasmine.any(Function));
    });

    it('should contain an onSelected method', function () {
      expect($scope.selectServerProfile.onSelected).toEqual(jasmine.any(Function));
    });

    it('should contain a getHostPath method', function () {
      expect($scope.selectServerProfile.getHostPath).toEqual(jasmine.any(Function));
    });

    it('should contain a pdshUpdate method', function () {
      expect($scope.selectServerProfile.pdshUpdate).toEqual(jasmine.any(Function));
    });

    it('should contain the pdsh expression on the scope', function () {
      expect($scope.selectServerProfile.pdsh).toEqual(data.server.pdsh);
    });

    it('should call data.hostProfileSpark.onValue', function () {
      expect(data.hostProfileSpark.onValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
    });

    describe('transition', function () {
      var action;
      beforeEach(function () {
        action = 'previous';
        $scope.selectServerProfile.transition(action);
      });

      it('should call off', function () {
        expect(off).toHaveBeenCalledOnce();
      });

      it('should call transition on the step instance', function () {
        expect($stepInstance.transition).toHaveBeenCalledOnceWith(action, {
          data: data,
          hostProfileData: $scope.selectServerProfile.data,
          profile: $scope.selectServerProfile.item
        });
      });
    });

    describe('receiving data change on hostProfileSpark', function () {
      var profile, response;
      beforeEach(function () {
        response = {
          statusCode: 200,
          body: {
            meta: {
              limit: 20,
              next: null,
              offset: 0,
              previous: null,
              total_count: 1
            },
            objects: [
              {
                address: 'storage1.localdomain',
                host: 69,
                profiles: {
                  base_managed: [
                    {
                      description: '',
                      pass: true,
                      test: 'zfs_installed == False'
                    }
                  ],
                  base_monitored: [],
                  posix_copytool_worker: [],
                  robinhood_server: []
                }
              }
            ]
          }
        };
        data.hostProfileSpark.onValue.mostRecentCall.args[1](response);
      });

      it('should set the data on the server profile', function () {
        expect($scope.selectServerProfile.data).toEqual(response.body.objects);
      });

      describe('receiving more data', function () {
        beforeEach(function () {
          response = {
            statusCode: 200,
            body: {
              meta: {
                limit: 20,
                next: null,
                offset: 0,
                previous: null,
                total_count: 1
              },
              objects: [
                {
                  address: 'storage1.localdomain',
                  host: 69,
                  profiles: {
                    base_managed: [
                      {
                        description: 'ZFS must not be installed',
                        error: '',
                        pass: true,
                        test: 'zfs_installed == False'
                      }
                    ],
                    base_monitored: [],
                    posix_copytool_worker: [],
                    robinhood_server: []
                  }
                }
              ]
            }
          };
          data.hostProfileSpark.onValue.mostRecentCall.args[1](response);
        });

        it('should keep the same profile', function () {
          expect($scope.selectServerProfile.profile).toEqual({
            name: 'base_managed',
            uiName: 'Managed storage server',
            invalid: false,
            hosts: [{
              address: 'storage1.localdomain',
              invalid: false,
              problems: [{
                description: 'ZFS must not be installed',
                error: '',
                pass: true,
                test: 'zfs_installed == False'
              }],
              uiName: 'Managed storage server'
            }]
          });
        });
      });

      describe('onSelected', function () {
        beforeEach(function () {
          profile = {
            name: 'base_managed',
            uiName: 'Managed storage server',
            invalid: false,
            hosts: [{
              address: 'storage1.localdomain',
              invalid: false,
              problems: [{
                description: 'ZFS must not be installed',
                error: '',
                pass: false,
                test: 'zfs_installed == False'
              }],
              uiName: 'Managed storage server'
            }]
          };

          $scope.selectServerProfile.onSelected(profile);
        });

        it('should set overridden to false', function () {
          expect($scope.selectServerProfile.overridden).toEqual(false);
        });

        it('should set the profile on the scope', function () {
          expect($scope.selectServerProfile.profile).toEqual(profile);
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
        expect($scope.selectServerProfile.getHostPath(item)).toEqual(item.address);
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

      describe('without hostnames', function () {
        beforeEach(function () {
          $scope.selectServerProfile.pdshUpdate(pdsh);
        });

        it('should contain the pdsh expression', function () {
          expect($scope.selectServerProfile.pdsh).toEqual(pdsh);
        });

        it('should not have the hostnames', function () {
          expect($scope.selectServerProfile.hostnames).toEqual(undefined);
        });
      });

      describe('with hostnames', function () {
        beforeEach(function () {
          $scope.selectServerProfile.pdshUpdate(pdsh, hostnames, hostnamesHash);
        });

        it('should contain the pdsh expression', function () {
          expect($scope.selectServerProfile.pdsh).toEqual(pdsh);
        });

        it('should have the hostnames', function () {
          expect($scope.selectServerProfile.hostnames).toEqual(hostnames);
        });

        it('should have the hostnamesHash', function () {
          expect($scope.selectServerProfile.hostnamesHash).toEqual(hostnamesHash);
        });
      });
    });
  });

  describe('selectServerProfileStep', function () {
    var $q, $scope, $transition, data, requestSocket, hostProfileData, profile, selectServerProfileStep,
      spark, postPromise;
    var waitForCommandCompletion, OVERRIDE_BUTTON_TYPES;

    beforeEach(inject(function (_selectServerProfileStep_, _$rootScope_, _$q_) {
      $scope = _$rootScope_.$new();
      selectServerProfileStep = _selectServerProfileStep_;
      $q = _$q_;

      waitForCommandCompletion = jasmine.createSpy('waitForCommandCompletion')
        .andReturn($q.when('transition_end'));

      OVERRIDE_BUTTON_TYPES = {
        OVERRIDE: 'override',
        PROCEED: 'proceed',
        PROCEED_SKIP: 'proceed and skip'
      };
    }));

    it('should contain the appropriate properties', function () {
      expect(selectServerProfileStep).toEqual({
        templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
        controller: 'SelectServerProfileStepCtrl',
        transition: jasmine.any(Array)
      });
    });

    describe('invoking the transition', function () {
      beforeEach(function () {
        postPromise = $q.when({
          body: {
            objects: [
              {id: 1}
            ]
          }
        });
        spark = {
          sendPost: jasmine.createSpy('sendPost').andReturn(postPromise),
          end: jasmine.createSpy('end')
        };
        requestSocket = jasmine.createSpy('requestSocket').andReturn(spark);
        data = {
          serverSpark: {
            onceValue: jasmine.createSpy('onceValue')
          }
        };
        $transition = {
          steps: {
            serverStatusStep: {}
          },
          end: jasmine.createSpy('end')
        };
        hostProfileData = [
          {
            host: 1
          }
        ];
        profile = {
          caption: 'Base Monitored',
          name: 'base_monitored'
        };
      });

      describe('previous action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'previous';
          result = _.last(selectServerProfileStep.transition)(
            $transition, data, requestSocket, hostProfileData, profile);
        });

        it('should resolve with the serverStatusStep', function () {
          expect(result).toEqual({
            step: $transition.steps.serverStatusStep,
            resolve: { data: data }
          });
        });
      });

      describe('end action', function () {
        var result;

        beforeEach(function () {
          $transition.action = 'end';

          result = selectServerProfileStep.transition[selectServerProfileStep.transition.length - 1](
            $transition, data, requestSocket, hostProfileData, profile, $q, waitForCommandCompletion,
            OVERRIDE_BUTTON_TYPES);

          data.serverSpark.onceValue.mostRecentCall.args[1]({
            body: {
              objects: [
                {
                  id: '1',
                  server_profile: {
                    initial_state: 'unconfigured'
                  }
                }
              ]
            }
          });

          $scope.$digest();
        });

        it('should invoke the request socket', function () {
          expect(requestSocket).toHaveBeenCalledOnce();
        });

        it('should listen for value on data', function () {
          expect(data.serverSpark.onceValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
        });

        it('should send a post to /host_profile', function () {
          expect(spark.sendPost).toHaveBeenCalledOnceWith('/host_profile', {
            json: {
              objects: [
                {
                  host: 1,
                  profile: 'base_monitored'
                }
              ]
            }
          }, true);
        });

        it('should call waitForCommandCompletion', function () {
          expect(waitForCommandCompletion).toHaveBeenCalledWith(false);
        });

        it('should call $transition.end', function () {
          expect($transition.end).toHaveBeenCalledOnce();
        });

        it('should end the spark', function () {
          expect(spark.end).toHaveBeenCalledOnce();
        });

        it('should receive an undefined response', function () {
          expect(result).toEqual(undefined);
        });
      });
    });
  });
});
