describe('wait-for-command-completion-service', function () {
  'use strict';

  var createCommandSpark, commandSpark, openCommandModal, waitForCommandCompletion, $q, $rootScope,
    responseWithCommands;
  beforeEach(module('command', function ($provide) {
    commandSpark = {
      onValue: jasmine.createSpy('onValue'),
      end: jasmine.createSpy('end')
    };

    createCommandSpark = jasmine.createSpy('createCommandSpark')
      .andReturn(commandSpark);

    $provide.value('createCommandSpark', createCommandSpark);

    openCommandModal = jasmine.createSpy('openCommandModal');
    $provide.value('openCommandModal', openCommandModal);
  }));

  beforeEach(inject(function (_waitForCommandCompletion_, _$q_, _$rootScope_) {
    waitForCommandCompletion = _waitForCommandCompletion_;
    $q = _$q_;
    $rootScope = _$rootScope_;
  }));

  responseWithCommands = [
    {
      body: {
        commands: [
          {
            state: 'finished'
          }
        ]
      }
    },
    {
      body: {
        objects: [
          {
            arg: 'arg',
            command: {
              state: 'finished'
            }
          }
        ]
      }
    }
  ];

  describe('response with errors', function () {
    var response;
    beforeEach(function () {
      response = {
        body: {
          errors: [
            {
              message: 'error message'
            }
          ]
        }
      };
    });

    it('should throw an exception', function () {
      function callWaitForCommandCompletion () {
        var waitFunction = waitForCommandCompletion(true);
        waitFunction(response);
      }

      expect(callWaitForCommandCompletion).toThrow(new Error(JSON.stringify([
        {message: 'error message'}
      ])));
    });
  });


  describe('no commands', function () {
    [
      {
        body: {
          commands: []
        }
      },
      {
        body: {
          objects: [
            {
              no: 'commands'
            }
          ]
        }
      }
    ].forEach(function handleResponse (response) {
        var result;
        beforeEach(function () {
          var waitFunction = waitForCommandCompletion(true);
          result = waitFunction(response);
        });

        it('should return a promise', function () {
          expect(isPromise(result)).toEqual(true);
        });

        it('should resolve with the response that was passed in initially', function () {
          result.then(function (resp) {
            expect(resp).toEqual(response);
          });

          $rootScope.$digest();
        });
      });
  });

  describe('contains finished commands', function () {
    responseWithCommands.forEach(function handleResponse (response) {
        var result;
        beforeEach(function () {
          var waitFunction = waitForCommandCompletion(true);
          result = waitFunction(response);
        });

        it('should call createCommandSpark', function () {
          expect(createCommandSpark).toHaveBeenCalledWith(getCommands(response));
        });

        it('should call openCommandModal', function () {
          expect(openCommandModal).toHaveBeenCalledWith(commandSpark);
        });

        it('should call commandSpark.onValue', function () {
          expect(commandSpark.onValue).toHaveBeenCalledWith('pipeline', jasmine.any(Function));
        });

        describe('when pipeline event is received', function () {
          [
            {
              body: {
                objects: [
                  {
                    state: 'not pending'
                  }
                ]
              }
            },
            {
              body: {
                state: 'not pending'
              }
            }
          ].forEach(function handleResponse (onPipeResponse) {
              beforeEach(function () {
                commandSpark.onValue.mostRecentCall.args[1](onPipeResponse);
              });

              it('should call commandSpark.end', function () {
                expect(commandSpark.end).toHaveBeenCalled();
              });

              it('should resolve the result', function () {
                result.then(function handleCommandsFinished (resp) {
                  expect(resp).toEqual(response);
                });

                $rootScope.$digest();
              });
            });
        });
      });
  });

  describe('don\'t show command modal', function () {
    responseWithCommands.forEach(function handleReponse (response) {
      var result;
      beforeEach(function () {
        var waitFunction = waitForCommandCompletion(false);
        result = waitFunction(response);
      });

      it('should not call openCommandModal', function () {
        expect(openCommandModal).not.toHaveBeenCalled();
      });
    });
  });

  function getCommands (response) {
    return (response.body.commands) ? _(response.body.commands).compact().value()
      : _(response.body.objects).pluck('command').compact().value();
  }

  /**
   * Determines if an object is a promise
   * @param {Object} obj
   * @returns {*}
   */
  function isPromise (obj) {
    return (obj.then != null && obj.catch != null && obj.finally != null);
  }
});
