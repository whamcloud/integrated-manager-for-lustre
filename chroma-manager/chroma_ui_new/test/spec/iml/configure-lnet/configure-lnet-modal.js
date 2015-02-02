describe('Configure LNet modal', function () {
  'use strict';

  var createCommandSpark;
  beforeEach(module('configure-lnet-module', 'dataFixtures', function ($provide) {
    createCommandSpark = jasmine.createSpy('createCommandSpark')
      .andReturn({
        end: jasmine.createSpy('end')
      });
    $provide.value('createCommandSpark', createCommandSpark);
  }));

  describe('Controller', function () {
    var $modalInstance, $scope, networkInterfaceSpark, hostSpark,
      requestSocket, openCommandModal, configureLnet, deferred, networkInterfaceResponse;

    beforeEach(inject(function ($rootScope, $controller, networkInterfaceDataFixtures, $q) {
      networkInterfaceResponse = _.cloneDeep(networkInterfaceDataFixtures[0].in);

      $scope = $rootScope.$new();

      $modalInstance = {
        close: jasmine.createSpy('close'),
        dismiss: jasmine.createSpy('dismiss')
      };

      networkInterfaceSpark = {
        onValue: jasmine.createSpy('onValue'),
        end: jasmine.createSpy('end')
      };

      hostSpark = {
        onValue: jasmine.createSpy('onValue'),
        end: jasmine.createSpy('end')
      };

      deferred = $q.defer();

      requestSocket = jasmine.createSpy('requestSocket').andReturn({
        sendPost: jasmine.createSpy('sendPost').andReturn(deferred.promise),
        end: jasmine.createSpy('end')
      });

      spyOn($scope, '$on').andCallThrough();

      openCommandModal = jasmine.createSpy('openCommandModal')
        .andReturn({
          result: $q.when()
        });

      $controller('ConfigureLnetModalCtrl', {
        $scope: $scope,
        $modalInstance: $modalInstance,
        networkInterfaceSpark: networkInterfaceSpark,
        hostSpark: hostSpark,
        requestSocket: requestSocket,
        openCommandModal: openCommandModal
      });

      configureLnet = $scope.configureLnet;
    }));

    it('should close the modal', function () {
      configureLnet.close();

      expect($modalInstance.dismiss).toHaveBeenCalledOnceWith('cancel');
    });

    it('should listen for $destroy', function () {
      expect($scope.$on).toHaveBeenCalledOnceWith('$destroy', jasmine.any(Function));
    });

    it('should end the host spark on destroy', function () {
      $scope.$on.mostRecentCall.args[1]();

      expect(hostSpark.end).toHaveBeenCalledOnce();
    });

    it('should end the network interface spark on destroy', function () {
      $scope.$on.mostRecentCall.args[1]();

      expect(networkInterfaceSpark.end).toHaveBeenCalledOnce();
    });

    describe('save', function () {
      beforeEach(function () {
        configureLnet.networkInterfaces = [
          {
            nid: { id: '1'}
          },
          {
            nid: { id: '2'}
          }
        ];

        configureLnet.save();
        deferred.resolve({
          body: {
            command: {
              id: 10
            }
          }
        });
        $scope.$digest();
      });

      it('should set the message to Saving', function () {
        expect(configureLnet.message).toEqual('Saving');
      });

      it('should send the post', function () {
        expect(requestSocket.plan().sendPost).toHaveBeenCalledOnceWith('/nid', {
          json: {
            objects: [
              { id : '1' },
              { id : '2' }
            ]
          }
        }, true);
      });

      it('should close the modal', function () {
        expect($modalInstance.close).toHaveBeenCalledOnce();
      });

      it('should open the command modal with the spark', function () {
        expect(openCommandModal).toHaveBeenCalledOnceWith(createCommandSpark.plan());
      });

      it('should call createCommandSpark with the last response', function () {
        expect(createCommandSpark).toHaveBeenCalledOnceWith([{id: 10}]);
      });

      it('should end the spark after the modal closes', function () {
        openCommandModal.plan().result.then(function whenModalClosed () {
          expect(createCommandSpark.plan().end).toHaveBeenCalledOnce();
        });

        $scope.$digest();
      });

      it('should end the spark', function () {
        expect(requestSocket.plan().end).toHaveBeenCalledOnce();
      });
    });

    describe('working with data', function () {
      var networkInterfacePipe;

      beforeEach(function () {
        networkInterfacePipe = networkInterfaceSpark.onValue.mostRecentCall.args[1];
        networkInterfacePipe(networkInterfaceResponse);
      });

      it('should set network interfaces on the scope', function () {
        expect(configureLnet.networkInterfaces).toEqual(networkInterfaceResponse);
      });

      it('should remove old items', function () {
        networkInterfacePipe([{
          id: '26',
          nid: {
            lnd_network: 3
          }
        }]);

        expect(configureLnet.networkInterfaces).toEqual(_.where(networkInterfaceResponse, { id: '26' }));
      });

      it('should add new items', function () {
        var response = [
          {
            id: '900',
            nid: {
              lnd_network: 1000
            }
          }
        ];

        networkInterfacePipe(response);

        expect(configureLnet.networkInterfaces).toContain(response[0]);
      });

      it('should return no diff if nothing changed', function () {
        expect(configureLnet.getDiff(configureLnet.networkInterfaces[0]))
          .toBe(undefined);
      });

      it('should tell if there was a local change', function () {
        configureLnet.networkInterfaces[0].nid.lnd_network = 2;

        expect(configureLnet.getDiff(configureLnet.networkInterfaces[0])).toEqual({
          params: {
            remote : 'Lustre Network 3'
          },
          type : 'local'
        });
      });

      it('should tell if there was a remote change', function () {
        var item = _.find(networkInterfaceResponse, { id: '26' });
        item.nid.lnd_network = -1;

        networkInterfacePipe(networkInterfaceResponse);

        var localItem = _.find(configureLnet.networkInterfaces, { id: '26' });

        expect(configureLnet.getDiff(localItem)).toEqual({
          params: {
            remote: 'Not Lustre Network'
          },
          type : 'remote'
        });
      });

      it('should tell if there was a local and remote change', function () {
        var item = _.find(networkInterfaceResponse, { id: '26' });
        item.nid.lnd_network = -1;

        networkInterfacePipe(networkInterfaceResponse);

        var localItem = _.find(configureLnet.networkInterfaces, { id: '26' });
        localItem.nid.lnd_network = 2;

        expect(configureLnet.getDiff(localItem)).toEqual({
          params: {
            initial: 'Lustre Network 3',
            remote: 'Not Lustre Network'
          },
          type: 'conflict'
        });
      });
    });

  });

  describe('Open LNet Modal', function () {
    var $modal, host;

    beforeEach(module(function ($provide) {
      $modal = {
        open: jasmine.createSpy('open')
      };

      $provide.value('$modal', $modal);
    }));

    beforeEach(inject(function (openLnetModal) {
      host = {
        resouce_uri: '/api/host/1',
        id: '1'
      };

      openLnetModal(host);
    }));

    it('should open the modal with the expected params', function () {
      expect($modal.open).toHaveBeenCalledOnceWith({
        templateUrl: 'iml/configure-lnet/assets/html/configure-lnet-modal.html',
        controller: 'ConfigureLnetModalCtrl',
        windowClass: 'configure-lnet-modal',
        backdrop: 'static',
        resolve: {
          hostSpark: jasmine.any(Array),
          networkInterfaceSpark: jasmine.any(Array)
        }
      });
    });

    describe('resolves', function () {
      var requestSocket, spark;

      describe('hostSpark', function () {
        beforeEach(function () {
          requestSocket = jasmine.createSpy('requestSocket').andReturn({
            setLastData: jasmine.createSpy('setLastData'),
            sendGet: jasmine.createSpy('sendGet')
          });

          spark = $modal.open.mostRecentCall.args[0].resolve.hostSpark[1](requestSocket);
        });

        it('should return a spark', function () {
          expect(spark).toEqual(requestSocket.plan());
        });

        it('should set the last data', function () {
          expect(spark.setLastData).toHaveBeenCalledOnceWith({
            statusCode: 200,
            body: host
          });
        });

        it('should send a get', function () {
          expect(spark.sendGet).toHaveBeenCalledOnceWith(host.resource_uri);
        });
      });

      describe('networkInterfaceSpark', function () {
        beforeEach(inject(function (throwIfError, LNET_OPTIONS) {

          requestSocket = jasmine.createSpy('requestSocket').andReturn({
            addPipe: jasmine.createSpy('addPipe'),
            sendGet: jasmine.createSpy('sendGet')
          });

          spark = $modal.open.mostRecentCall
            .args[0].resolve.networkInterfaceSpark[3](requestSocket, throwIfError, LNET_OPTIONS);
        }));

        it('should return a spark', function () {
          expect(spark).toEqual(requestSocket.plan());
        });

        it('should send a get', function () {
          expect(spark.sendGet).toHaveBeenCalledOnceWith('/network_interface', {
            qs: {
              host__id : '1'
            }
          });
        });

        describe('add Pipe', function () {
          var pipe;

          beforeEach(function () {
            pipe = spark.addPipe.mostRecentCall.args[0];
          });

          it('should throw on error', function () {
            expect(shouldThrow).toThrow('foo');

            function shouldThrow () {
              pipe({
                error: {message: 'foo'}
              });
            }
          });

          it('should add a nid if missing', function () {
            var response = {
              body: {
                objects: [
                  {
                    resource_uri: '/api/network_interface/1'
                  },
                  {
                    resource_uri: '/api/network_interface/2',
                    nid: {
                      lnd_network: 1,
                      network_interface: '/api/network_interface/2'
                    }
                  }
                ]
              }
            };

            var result = pipe(response);

            expect(result).toEqual([{
              resource_uri : '/api/network_interface/1',
              nid : { lnd_network : -1, network_interface : '/api/network_interface/1' }
            },
            {
              resource_uri : '/api/network_interface/2',
              nid : { lnd_network : 1, network_interface : '/api/network_interface/2' }
            }]);
          });
        });
      });
    });
  });
});
