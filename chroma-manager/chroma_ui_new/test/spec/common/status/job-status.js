describe('Job Status directive', function () {
  'use strict';

  var $scope, element, node, jobMonitor, popover, i, spark;

  beforeEach(module('status', 'templates', 'ui.bootstrap.tooltip', 'ui.bootstrap.tpls', function ($provide) {

    spark = {
      onValue: jasmine.createSpy('onValue')
    };

    jobMonitor = jasmine.createSpy('jobMonitor').andReturn(spark);

    $provide.value('jobMonitor', jobMonitor);

  }));

  beforeEach(inject(function ($rootScope, $compile) {
    // Create an instance of the element
    element = '<job-status record-id="host/6"></job-status>';

    $scope = $rootScope.$new();

    node = $compile(element)($scope);

    // Update the html
    $scope.$digest();

    $scope.$$childHead.recordId = 'host/6';

    popover = node.find('iml-popover');
    i = node.find('i');
  }));

  describe('populate jobs on data change', function () {

    it('should have no job messages if the response doesn\'t contain a body.', function () {
      var response = {};

      var handler = jobMonitor().onValue.mostRecentCall.args[1];
      handler(response);

      expect($scope.$$childHead.jobStatus.containsJobMessages()).toEqual(false);
    });

    describe('write locks', function () {
      var response;
      beforeEach(function () {
        response = {
          body: {
            objects: [
              {
                write_locks: [
                  {
                    locked_item_uri: 'host/6'
                  }
                ],
                description: 'write lock description'
              }
            ]
          }
        };

        var handler = jobMonitor().onValue.mostRecentCall.args[1];
        handler(response);
      });

      it('should contain a write lock job message', function () {
        expect($scope.$$childHead.jobStatus.getWriteMessages()).toEqual(['write lock description']);
      });

      it('should get write lock tooltip message ', function () {
        expect($scope.$$childHead.jobStatus.getLockTooltipMessage()).toEqual('1 ongoing write lock operation.' +
          ' Click to review details.');
      });
    });

    describe('read locks', function () {
      var response;
      beforeEach(function () {
        response = {
          body: {
            objects: [
              {
                read_locks: [
                  {
                    locked_item_uri: 'host/6'
                  }
                ],
                description: 'read lock description'
              }
            ]
          }
        };

        var handler = jobMonitor().onValue.mostRecentCall.args[1];
        handler(response);
      });

      it('should contain a read lock job message', function () {
        expect($scope.$$childHead.jobStatus.getReadMessages()).toEqual(['read lock description']);
      });

      it('should get read lock tooltip message ', function () {
        expect($scope.$$childHead.jobStatus.getLockTooltipMessage()).toEqual('Locked by 1 pending operation. ' +
          'Click to review details.');
      });
    });

    describe('read and write locks', function () {
      var response;

      beforeEach(function () {
        response = {
          body: {
            objects: [
              {
                read_locks: [
                  {
                    locked_item_uri: 'host/6'
                  }
                ],
                description: 'read lock description'
              },
              {
                write_locks: [
                  {
                    locked_item_uri: 'host/6'
                  }
                ],
                description: 'write lock description'
              }
            ]
          }
        };

        var handler = jobMonitor().onValue.mostRecentCall.args[1];
        handler(response);
      });

      it('should contain a read and write lock job message', function () {
        var messages = $scope.$$childHead.jobStatus.getReadMessages()
          .concat($scope.$$childHead.jobStatus.getWriteMessages());

        expect(messages)
          .toEqual(['read lock description', 'write lock description']);
      });

      it('should get lock tooltip message for both read and write lock messages', function () {
        expect($scope.$$childHead.jobStatus.getLockTooltipMessage()).toEqual('There is 1 ongoing write lock' +
          ' operation and 1 pending read lock operation. Click to review details.');
      });
    });
  });

  describe('lock icon interaction', function () {
    var response;

    beforeEach(function () {
      response = {
        body: {
          objects: [
            {
              read_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'read lock description'
            },
            {
              write_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'write lock description'
            }
          ]
        }
      };

      var handler = jobMonitor().onValue.mostRecentCall.args[1];
      handler(response);

      // Update the html
      $scope.$digest();

      i = node.find('i');
    });

    it('should display the info icon', function () {
      expect(i).toBeShown();
    });

    it('should display the popover after clicking info icon', function () {
      i.trigger('click');

      popover = node.find('i ~ .popover');
      expect(popover).toBeShown();
    });

    it('should display the tooltip after mousing over the info icon', function () {
      i.trigger('mouseover');

      var tooltip = node.find('.tooltip');
      expect(tooltip).toBeShown();
    });
  });

  describe('read message updates', function () {
    var response;
    beforeEach(function () {
      response = {
        body: {
          objects: [
            {
              read_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'read lock description1'
            }
          ]
        }
      };

      var handler = jobMonitor().onValue.mostRecentCall.args[1];
      handler(response);

      // Change the response to have 2 messages now
      response = {
        body: {
          objects: [
            {
              read_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'read lock description1'
            },
            {
              read_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'read lock description2'
            }
          ]
        }
      };

      handler(response);

      // Now, remove the first message so that only message 2 remains
      response = {
        body: {
          objects: [
            {
              read_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'read lock description2'
            }
          ]
        }
      };

      handler(response);
    });

    it('should contain the second message in the status array.', function () {
      expect($scope.$$childHead.jobStatus.getReadMessages()).toEqual(['read lock description2']);
    });

    it('should contain both messages in the message record.', function () {
      expect($scope.$$childHead.jobStatus.getReadMessageRecord())
        .toEqual(['read lock description1', 'read lock description2']);
    });

    it('should contain only message1 in the difference array.', function () {
      expect($scope.$$childHead.jobStatus.getReadMessageDifference()).toEqual(['read lock description1']);
    });
  });

  describe('write message updates', function () {
    var response;
    beforeEach(function () {
      response = {
        body: {
          objects: [
            {
              write_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'write lock description1'
            }
          ]
        }
      };

      var handler = jobMonitor().onValue.mostRecentCall.args[1];
      handler(response);

      // Change the response to have 2 messages now
      response = {
        body: {
          objects: [
            {
              write_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'write lock description1'
            },
            {
              write_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'write lock description2'
            }
          ]
        }
      };

      handler(response);

      // Now, remove the first message so that only message 2 remains
      response = {
        body: {
          objects: [
            {
              write_locks: [
                {
                  locked_item_uri: 'host/6'
                }
              ],
              description: 'write lock description2'
            }
          ]
        }
      };

      handler(response);
    });

    it('should contain the second message in the status array.', function () {
      expect($scope.$$childHead.jobStatus.getWriteMessages()).toEqual(['write lock description2']);
    });

    it('should contain both messages in the message record.', function () {
      expect($scope.$$childHead.jobStatus.getWriteMessageRecord())
        .toEqual(['write lock description1', 'write lock description2']);
    });

    it('should contain only message1 in the difference array.', function () {
      expect($scope.$$childHead.jobStatus.getWriteMessageDifference()).toEqual(['write lock description1']);
    });
  });
});
