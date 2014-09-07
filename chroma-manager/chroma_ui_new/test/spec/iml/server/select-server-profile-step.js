(function () {
  'use strict';
  describe('select server profile step ctrl', function () {
    var $scope, $stepInstance, data, off;

    beforeEach(module('server'));
    beforeEach(inject(function ($rootScope, $controller) {
      $scope = $rootScope.$new();
      $stepInstance = {
        transition: jasmine.createSpy('transition')
      };
      off = jasmine.createSpy('off');
      data = {
        hostProfileSpark: {
          onValue: jasmine.createSpy('onValue').andReturn(off)
        }
      };

      $controller('SelectServerProfileStepCtrl', {
        $scope: $scope,
        $stepInstance: $stepInstance,
        data: data
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

    it('should contain a showWarning method', function () {
      expect($scope.selectServerProfile.showWarning).toEqual(jasmine.any(Function));
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

      it('should set the server profile to a disabled state', function () {
        expect($scope.selectServerProfile.disabled).toEqual(true);
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
      var item, response;
      beforeEach(function () {
        response = {
          body: {
            objects: [
              {
                profiles: {
                  base_managed: [
                    {
                      description: 'ZFS must not be installed',
                      result: true
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

      it('should set fancy options', function () {
        expect($scope.selectServerProfile.options).toEqual([
          {
            id: 'base_managed',
            caption: 'Base managed',
            label: 'Incompatible',
            labelType: 'label-danger',
            valid: undefined
          },
          {
            id: 'base_monitored',
            caption: 'Base monitored',
            valid: true
          },
          {
            id: 'posix_copytool_worker',
            caption: 'Posix copytool worker',
            valid: true
          },
          {
            id: 'robinhood_server',
            caption: 'Robinhood server',
            valid: true
          }
        ]);
      });

      describe('onSelected', function () {
        beforeEach(function () {
          item = {
            id: 'base_monitored',
            caption: 'Base monitored'
          };

          $scope.selectServerProfile.onSelected(item);
        });

        it('should set warning to false', function () {
          expect($scope.selectServerProfile.warning).toEqual(false);
        });

        it('should set the item on the server profile', function () {
          expect($scope.selectServerProfile.item).toEqual(item);
        });

        it('should set the items', function () {
          expect($scope.selectServerProfile.items).toEqual([
            {
              items: [],
              profile: 'Base monitored',
              profiles: {
                base_managed: [
                  {
                    description: 'ZFS must not be installed',
                    result: true
                  }
                ],
                base_monitored: [],
                posix_copytool_worker: [],
                robinhood_server: []
              },
              valid: true
            }
          ]);
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
      var pdsh, hostnames;
      beforeEach(function () {
        pdsh = 'test[001-002].localdomain';
        hostnames = ['test001.localdomain', 'test002.localdomain'];
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
          $scope.selectServerProfile.pdshUpdate(pdsh, hostnames);
        });

        it('should contain the pdsh expression', function () {
          expect($scope.selectServerProfile.pdsh).toEqual(pdsh);
        });

        it('should have the hostnames', function () {
          expect($scope.selectServerProfile.hostnames).toEqual(hostnames);
        });
      });
    });

    describe('show warning', function () {
      beforeEach(function () {
        $scope.selectServerProfile.showWarning();
      });

      it('should set warning to true', function () {
        expect($scope.selectServerProfile.warning).toEqual(true);
      });
    });
  });

  describe('selectServerProfileStep', function () {
    var $q, $scope, $transition, data, requestSocket, hostProfileData, profile, selectServerProfileStep,
      spark, postPromise;

    beforeEach(module('server'));
    beforeEach(inject(function (_selectServerProfileStep_, _$rootScope_, _$q_) {
      $scope = _$rootScope_.$new();
      selectServerProfileStep = _selectServerProfileStep_;
      $q = _$q_;
    }));

    it('should contain the appropriate properties', function () {
      expect(selectServerProfileStep).toEqual({
        templateUrl: 'iml/server/assets/html/select-server-profile-step.html',
        controller: 'SelectServerProfileStepCtrl',
        transition: jasmine.any(Array)
      });
    });

    describe('invoking the transition', function () {
      var promise;

      beforeEach(function () {
        postPromise = $q.when('transition_end');
        spark = {
          sendPost: jasmine.createSpy('sendPost').andReturn(postPromise),
          end: jasmine.createSpy('end')
        };
        requestSocket = jasmine.createSpy('requestSocket').andReturn(spark);
        data = {
          statusSpark: {
            onValue: jasmine.createSpy('onValue')
          }
        };
        $transition = {
          steps: {
            addServerStep: {},
            serverStatusStep: {}
          },
          end: jasmine.createSpy('end')
        };
        hostProfileData = [
          {
            host: 'test001.localdomain'
          }
        ];
        profile = {
          caption: 'Base Monitored',
          id: 'base_monitored'
        };
      });

      describe('not an end action', function () {
        var response;
        beforeEach(function () {
          data.statusSpark.off = jasmine.createSpy('off');
        });

        describe('previous action', function () {
          beforeEach(function () {
            $transition.action = 'previous';
            promise = selectServerProfileStep.transition[selectServerProfileStep.transition.length - 1]($q,
              $transition, data, requestSocket, hostProfileData, profile);
          });

          it('should call statusSpark.onValue', function () {
            expect(data.statusSpark.onValue).toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
          });

          [
            {
              description: 'valid',
              valid: true,
              expectedStep: 'addServersStep'
            },
            {
              description: 'invalid',
              valid: false,
              expectedStep: 'serverStatusStep'
            }
          ].forEach(function testPreviousActionPermutations (json) {
              describe(json.description, function () {
                beforeEach(function () {
                  response = {
                    body: {
                      isValid: json.valid
                    }
                  };

                  data.statusSpark.onValue.mostRecentCall.args[1].call(data.statusSpark, response);
                });

                it('should call off', function () {
                  expect(data.statusSpark.off).toHaveBeenCalledOnce();
                });

                it('should resolve with the addServersStep', function () {
                  promise.then(function (result) {
                    expect(result).toEqual({
                      step: $transition.steps[json.expectedStep],
                      resolve: { data: data }
                    });
                  });

                  $scope.$digest();
                });
              });
            });
        });

        describe('not previous action', function () {
          beforeEach(function () {
            $transition.action = 'next';
            promise = selectServerProfileStep.transition[selectServerProfileStep.transition.length - 1]($q,
              $transition, data, requestSocket, hostProfileData, profile);

            response = {
              body: {
                isValid: true
              }
            };

            data.statusSpark.onValue.mostRecentCall.args[1].call(data.statusSpark, response);
          });

          it('should resolve', function () {
            promise.then(function (result) {
              expect(result).toEqual({
                step: undefined,
                resolve: { data: data }
              });
            });

            $scope.$digest();
          });
        });

        describe('error in body', function () {
          beforeEach(function () {
            $transition.action = 'next';
            promise = selectServerProfileStep.transition[selectServerProfileStep.transition.length - 1]($q,
              $transition, data, requestSocket, hostProfileData, profile);

            response = {
              body: {
                errors: [
                  {msg: 'error'}
                ]
              }
            };
          });

          it('should throw an error', function () {
            try {
              data.statusSpark.onValue.mostRecentCall.args[1].call(data.statusSpark, response);
            } catch (e) {
              expect(e.message).toEqual('[{"msg":"error"}]');
            }
          });
        });
      });

      describe('end action', function () {
        beforeEach(function () {
          $transition.action = 'end';

          promise = selectServerProfileStep.transition[selectServerProfileStep.transition.length - 1]($q,
            $transition, data, requestSocket, hostProfileData, profile);

          $scope.$digest();
        });

        it('should invoke the request socket', function () {
          expect(requestSocket).toHaveBeenCalledOnce();
        });

        it('should send a post to /host_profile', function () {
          expect(spark.sendPost).toHaveBeenCalledOnceWith('/host_profile', {
            json: {
              objects: [
                {
                  host: 'test001.localdomain',
                  profile: 'base_monitored'
                }
              ]
            }
          }, true);
        });

        it('should call $transition.end', function () {
          expect($transition.end).toHaveBeenCalledOnce();
        });

        it('should end the spark', function () {
          expect(spark.end).toHaveBeenCalledOnce();
        });

        it('should receive an undefined response', function () {
          expect(promise).toEqual(undefined);
        });
      });
    });
  });
})();
