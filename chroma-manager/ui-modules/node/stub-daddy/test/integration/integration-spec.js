'use strict';

var request = require('request-then');
var format = require('util').format;
var fixtures = require('../fixtures/standard-fixtures');
var _ = require('lodash-mixins');
var wireTreeModule = require('../../index');

['http', 'https'].forEach(function testIntegrationTestsWithSecureAndNonSecureUrls (protocol) {
  describe('integration tests for ' + protocol, function () {
    var config, webService, makeRequestAndExpect;

    /**
     * Start the service before each test.
     * @param  {Function} done
     */
    beforeEach(function (done) {
      var wireTree = wireTreeModule(protocol);
      config = wireTree.config;
      webService = wireTree.webService;

      var url = format.bind(null, '%s://localhost:%s%s', config.requestProtocol, config.port);
      makeRequestAndExpect = makeRequestAndExpectWrap(url);
      webService.startService().done(done);
    });

    /**
     * stop the service after each test.
     * @param {Function} done
     */
    afterEach(function (done) {
      webService.flush();
      webService.stopService().done(done);
    });

    describe('register mock api by calling /api/mock', function () {
      it('should receive a 400 when calling /api/mock with a GET', function (done) {
        makeRequestAndExpect({path: '/api/mock'}, 400).done(done);
      });

      fixtures.integration.registerMockRequests.forEach(function (data) {
        var shouldStatement = format('should receive a %s when calling %s with a %s containing %s', data.status,
          data.json.path, data.json.method, Object.keys(data.json.json).join(', '));

        it(shouldStatement, function (done) {
          makeRequestAndExpect(data.json, data.status).done(done);
        });
      });


      it('should fail if incorrect json is sent on the request', function (done) {
        var requestOptions = _.merge({}, fixtures.integration.registerMockRequests
          [fixtures.integration.registerMockRequests.length - 1].json);

        requestOptions.body = JSON.stringify(requestOptions) + '}[';
        delete requestOptions.json;

        makeRequestAndExpect(requestOptions, 400, 'JSON is not properly formed.').done(done);
      });
    });

    describe('register a GET mock API and verify response', function () {
      var requestOptions = _.merge({}, fixtures.integration.registerSuccessfulMockRequest.json.json);
      var shouldMessage = format.bind(null, 'should call mocked API from mock service %s');
      var options = [
        {
          options: {
            path: '/user/profile?user=johndoe&key=abc123',
            headers: requestOptions.request.headers
          },
          status: 200,
          title: 'with all required parameters and verify response'
        },
        {
          options: {
            path: '/user/profile?key=abc123&user=johndoe',
            headers: requestOptions.request.headers
          },
          status: 200,
          title: 'with all required parameters and query parameters reversed'
        },
        {
          options: {
            path: '/user/profile?key=abc123',
            headers: {
              authorization: 'BEARER token55'
            }
          },
          status: 404,
          title: 'with missing parameter and return 404'
        },
        {
          options: {
            path: '/user/profile?key=abc123&user=johndoe',
            headers: {
              authorization: 'BEARER token5'
            }
          },
          status: 404,
          title: 'with incorrect header and return 400'
        },
        {
          options: {
            path: '/user/profile?key=abc123&user=johndoe',
            headers: {}
          },
          status: 404,
          title: 'without required header and return 400'
        }
      ];

      requestOptions = _.merge({}, fixtures.integration.registerSuccessfulMockRequest.json);
      options.forEach(function (option) {
        it(shouldMessage(option.title), function (done) {
          makeRequestAndExpect(requestOptions, 201)
            .then(function afterInitialRequest () {
              var args = [option.options, option.status];

              if (option.status === 200)
                args.push(requestOptions.json.response.data);

              return makeRequestAndExpect.apply(null, args);
            })
            .done(done);
        });
      });
    });

    describe('request to mock API methods', function () {
      var methods = ['POST', 'PUT', 'PATCH'];
      var requestOptions = _.merge({}, fixtures.integration.registerSuccessfulMockPOSTRequest.json);
      var options = [
        {
          options: {
            method: requestOptions.json.request.method,
            path: requestOptions.json.request.url,
            body: JSON.stringify(requestOptions.json.request.data),
            headers: requestOptions.json.request.headers
          },
          status: 200,
          title: 'with all required parameters and verify response'
        },
        {
          options: {
            method: requestOptions.json.request.method,
            path: requestOptions.json.request.url,
            body: JSON.stringify({key: 'abc123'}),
            headers: requestOptions.json.request.headers
          },
          status: 404,
          title: 'with missing parameter and return 404'
        },
        {
          options: {
            method: requestOptions.json.request.method,
            path: requestOptions.json.request.url,
            body: JSON.stringify(requestOptions.json.request.data),
            headers: {
              authorization: 'BEARER token5'
            }
          },
          status: 404,
          title: 'with incorrect header and return 400'
        },
        {
          options: {
            method: requestOptions.json.request.method,
            path: requestOptions.json.request.url,
            body: JSON.stringify(requestOptions.json.request.data),
            headers: {}
          },
          status: 404,
          title: 'without required header and return 400'
        }
      ];
      var shouldMessage = format.bind(null, 'should %s mocked API from mock service %s');

      methods.forEach(function (method) {
        options.forEach(function (option) {
          it(shouldMessage(method, option.title), function (done) {
            requestOptions.json.request.method = method;

            makeRequestAndExpect(requestOptions, 201)
              .then(function afterInitialRequest () {
                option.options.method = method; // set the current method

                var args = [option.options, option.status];

                if (option.status === 200)
                  args.push(requestOptions.json.response.data);

                return makeRequestAndExpect.apply(null, args);
              })
              .done(done);
          });
        });
      });

      it('should register mock call as a POST but call with a PUT and get a 404', function (done) {
        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            var callOptions = {
              method: 'PUT',
              path: requestOptions.json.request.url,
              body: JSON.stringify(requestOptions.json.request.data),
              headers: requestOptions.json.request.headers
            };

            return makeRequestAndExpect(callOptions, 404);
          })
          .done(done);
      });
    });

    describe('testing expire functionality', function () {
      var requestOptions, callOptions;

      beforeEach(function () {
        requestOptions = _.merge({}, fixtures.integration.registerRequestForExpireFunctionality.json);
        callOptions = {
          path: requestOptions.json.request.url,
          headers: requestOptions.json.request.headers,
          method: requestOptions.json.request.method,
          body: JSON.stringify(requestOptions.json.request.data)
        };
      });

      it('should request successfully the first time and give a 404 on the third attempt', function (done) {
        // Register an API in the mock service
        requestOptions.json.expires = 2;

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            return makeRequestAndExpect(callOptions, 200, requestOptions.json.response.data);
          })
          .then(function afterCallingTheMockOnce () {
            return makeRequestAndExpect(callOptions, 200, requestOptions.json.response.data);
          })
          .then(function afterCallingTheMockTwice () {
            return makeRequestAndExpect(callOptions, 404);
          })
          .done(done);
      });

      it('should successfully request the first, second, and third call because expires is 0', function (done) {
        // Register an API in the mock service
        requestOptions.expires = 3;

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            return makeRequestAndExpect(callOptions, 200, requestOptions.json.response.data);
          })
          .then(function afterCallingTheMockOnce () {
            return makeRequestAndExpect(callOptions, 200, requestOptions.json.response.data);
          })
          .then(function afterCallingTheMockTwice () {
            return makeRequestAndExpect(callOptions, 200, requestOptions.json.response.data);
          })
          .done(done);
      });
    });

    describe('testing mock state', function () {
      var requestOptions, callOptions;

      beforeEach(function () {
        requestOptions = _.merge({}, fixtures.integration.registerRequestForMockState.json);
        callOptions = {
          path: requestOptions.json.request.url,
          headers: requestOptions.json.request.headers,
          method: requestOptions.json.request.method,
          body: JSON.stringify(requestOptions.json.request.data)
        };
      });

      it('should pass with no state errors', function (done) {
        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            return makeRequestAndExpect(callOptions, 200);
          })
          .then(function afterCallingTheMock () {
            var stateOptions = {
              path: '/api/mockstate',
              method: config.methods.GET
            };
            var expectedResponse = [];
            return makeRequestAndExpect(stateOptions, 200, expectedResponse);
          })
          .done(done);
      });

      it('should fail due to making an unregistered call', function (done) {
        callOptions.body = JSON.stringify({
          user: 'johndoe',
          key: '123abc'
        });

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            var stateOptions = {
              path: '/api/mockstate',
              method: config.methods.GET
            };
            return makeRequestAndExpect(stateOptions, 200, []);
          })
          .then(function expect404 () {
            return makeRequestAndExpect(callOptions, 404);
          })
          .then(function afterCallingTheMock () {
            var stateOptions = {
              path: '/api/mockstate',
              method: config.methods.GET
            };
            var expectedResponse = [
              {
                state: 'ERROR',
                message: 'Call made to non-existent mock',
                data: {
                  method: requestOptions.json.request.method,
                  url: requestOptions.json.request.url,
                  data: JSON.parse(callOptions.body),
                  headers: {
                    'content-length': '33',
                    authorization: 'BEARER token55',
                    host: 'localhost:' + config.port,
                    connection: 'close'
                  }
                }
              }
            ];
            return makeRequestAndExpect(stateOptions, 400, expectedResponse);
          })
          .done(done);
      });

      it('should fail due to not calling the registered API enough times', function (done) {
        requestOptions.json.expires = 2;

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            return makeRequestAndExpect(callOptions, 200);
          })
          .then(function afterCallingTheMock () {
            var stateOptions = {
              path: '/api/mockstate'
            };
            var expectedResponse = [
              {
                state: 'ERROR',
                message: 'Call to expected mock not satisfied.',
                data: {
                  request: {
                    method: config.methods.POST,
                    url: '/user/profile',
                    data: {
                      user: 'janedoe',
                      key: 'abc123'
                    },
                    headers: {
                      authorization: 'BEARER token55'
                    }
                  },
                  response: {
                    status: 200,
                    data: {
                      firstName: 'Jane',
                      lastName: 'Doe',
                      dob: '1981-09-13',
                      city: 'Orlando',
                      state: 'FL'
                    },
                    headers: {
                      authorization: 'BEARER token55',
                      'content-type': 'application/json'
                    }
                  },
                  expires: 2,
                  remainingCalls: 1,
                  dependencies: []
                }
              }
            ];
            return makeRequestAndExpect(stateOptions, 400, expectedResponse);
          })
          .done(done);
      });

      it('should fail due to calling the registered api more than the specified number of times', function (done) {
        requestOptions.json.expires = 1;

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterInitialRequest () {
            return makeRequestAndExpect(callOptions, 200);
          })
          .then(function afterCallingTheMockOnce () {
            return makeRequestAndExpect(callOptions, 404);
          })
          .then(function afterCallingTheMockTwice () {
            var stateOptions = {path: '/api/mockstate'};
            var expectedResponse = [
              {
                state: 'ERROR',
                message: 'Call to expected mock not satisfied.',
                data: {
                  request: {
                    method: config.methods.POST,
                    url: '/user/profile',
                    data: {
                      user: 'janedoe',
                      key: 'abc123'
                    },
                    headers: {
                      authorization: 'BEARER token55'
                    }
                  },
                  response: {
                    status: 200,
                    data: {
                      firstName: 'Jane',
                      lastName: 'Doe',
                      dob: '1981-09-13',
                      city: 'Orlando',
                      state: 'FL'
                    },
                    headers: {
                      authorization: 'BEARER token55',
                      'content-type': 'application/json'
                    }
                  },
                  expires: 1,
                  remainingCalls: -1,
                  dependencies: []
                }
              }
            ];

            return makeRequestAndExpect(stateOptions, 400, expectedResponse);
          })
          .done(done);
      });

      it('should fail due to making an unregistered call and also not satisfying the requirements of a ' +
      'registered call', function (done) {

        requestOptions.json.expires = 1;

        makeRequestAndExpect(requestOptions, 201)
          .then(function afterFirstRequest () {
            return makeRequestAndExpect(callOptions, 200);
          })
          .then(function afterCallingTheMockOnce () {
            return makeRequestAndExpect(callOptions, 404);
          })
          .then(function afterCallingTheMockTwice () {
            var unregisteredCallOptions = _.merge({}, callOptions, {
              path: '/user/unregistered/method'
            });
            return makeRequestAndExpect(unregisteredCallOptions, 404);
          })
          .then(function afterCallingAnUnregisteredAPI () {
            var stateOptions = {
              path: '/api/mockstate'
            };
            var expectedResponse = [
              {
                state: 'ERROR',
                message: 'Call made to non-existent mock',
                data: {
                  method: config.methods.POST,
                  url: '/user/unregistered/method',
                  data: {
                    user: 'janedoe',
                    key: 'abc123'
                  },
                  headers: {
                    authorization: 'BEARER token55',
                    host: 'localhost:' + config.port,
                    'content-length': '33',
                    connection: 'close'
                  }
                }
              },
              {
                state: 'ERROR',
                message: 'Call to expected mock not satisfied.',
                data: {
                  request: {
                    method: config.methods.POST,
                    url: '/user/profile',
                    data: {
                      user: 'janedoe',
                      key: 'abc123'
                    },
                    headers: {
                      authorization: 'BEARER token55'
                    }
                  },
                  response: {
                    status: 200,
                    data: {
                      firstName: 'Jane',
                      lastName: 'Doe',
                      dob: '1981-09-13',
                      city: 'Orlando',
                      state: 'FL'
                    },
                    headers: {
                      authorization: 'BEARER token55',
                      'content-type': 'application/json'
                    }
                  },
                  expires: 1,
                  remainingCalls: -1,
                  dependencies: []
                }
              }
            ];
            return makeRequestAndExpect(stateOptions, 400, expectedResponse);
          })
          .done(done);
      });
    });

    describe('integration - testing request with dynamic response', function () {
      var requestOptions1, requestOptions2, callOptions1, callOptions2;

      beforeEach(function () {
        requestOptions1 = _.merge({}, fixtures.integration.registerRequestWithDynamicResponse.json);
        requestOptions1.json.response.data = {
          state: 'green'
        };
        requestOptions1.json.expires = 1;

        requestOptions2 = _.merge({}, fixtures.integration.registerRequestWithDynamicResponse.json);
        requestOptions2.json.response.data = {
          state: 'yellow'
        };

        callOptions1 = {
          path: requestOptions1.json.request.url,
          headers: requestOptions1.json.request.headers,
          method: requestOptions1.json.request.method,
          body: JSON.stringify(requestOptions1.json.request.data)
        };

        callOptions2 = {
          path: requestOptions1.json.request.url,
          headers: requestOptions1.json.request.headers,
          method: requestOptions1.json.request.method,
          body: JSON.stringify(requestOptions2.json.request.data)
        };
      });

      it('should request the post twice', function (done) {
        makeRequestAndExpect(requestOptions1, 201).then(function makeSecondRequest () {
          return makeRequestAndExpect(requestOptions2, 201);
        }).then(function postFirstRequest () {
          var expectedResponse = {
            state: 'green'
          };

          return makeRequestAndExpect(callOptions1, 200, expectedResponse);
        }).then(function postSecondRequest () {
          var expectedResponse = {
            state: 'yellow'
          };

          return makeRequestAndExpect(callOptions2, 200, expectedResponse);
        }).done(done);
      });
    });

    describe('testing entry dependencies', function () {
      var standardAlertRequest, alertRequest, filesystemRequest, alertCall, filesystemCall;

      beforeEach(function () {
        filesystemRequest = _.merge({}, fixtures.integration.registerSuccessfulMockPOSTRequest.json, {
          json: {
            request: {
              method: 'PUT',
              url: '/api/filesystem/'
            },
            expires: 1
          }
        });
        filesystemRequest.json.request.data = {id: 1};
        filesystemRequest.json.response.data = {};
        standardAlertRequest = _.merge({}, fixtures.integration.registerRequestWithDependencies.json, {
          json: {
            response: {
              data: {
                status: 'invalid'
              }
            }
          }
        });
        standardAlertRequest.json.dependencies = [];
        alertRequest = _.merge({}, fixtures.integration.registerRequestWithDependencies.json);

        alertCall = {
          path: alertRequest.json.request.url,
          headers: alertRequest.json.request.headers,
          method: alertRequest.json.request.method,
          body: JSON.stringify(alertRequest.json.request.data)
        };

        filesystemCall = {
          path: filesystemRequest.json.request.url,
          headers: filesystemRequest.json.request.headers,
          method: filesystemRequest.json.request.method,
          body: JSON.stringify(filesystemRequest.json.request.data)
        };
      });

      it('should retrieve standard alert until filesystem PUT request is made', function (done) {
        makeRequestAndExpect(alertRequest, 201).then(function mockStandardAlertRequest () {
          return makeRequestAndExpect(standardAlertRequest, 201);
        }).then(function mockFilesystemPutRequest () {
          return makeRequestAndExpect(filesystemRequest, 201);
        }).then(function getAlert () {
          var expectedResponse = {
            status: 'invalid'
          };

          return makeRequestAndExpect(alertCall, 200, expectedResponse);
        }).then(function putFilesystemRequest () {
          return makeRequestAndExpect(filesystemCall, 200, {});
        }).then(function getAlertAgain () {
          var expectedResponse = {
            status: 'OK'
          };

          return makeRequestAndExpect(alertCall, 200, expectedResponse);
        }).done(done);
      });
    });
  });
});

/**
 * HOF returns a function that will make a request and verify the expectation passed in.
 * @param {Function} url
 * @returns {Function}
 */
function makeRequestAndExpectWrap (url) {
  /**
   * Starts the service and then makes a POST request attempting to register an api mock.
   * @param {Object} options
   * @param {Number} expectedResponse
   * @param {Object|String} dataToCompare
   */
  return function makeRequestAndExpect (options, expectedResponse, dataToCompare) {
    if (!options)
      throw new Error('Options is required to make a request.');

    options = _.merge({}, options, {
      uri: url(options.path),
      strictSSL: false,
      headers: {
        'Connection': 'close'
      }
    });
    delete options.path;

    return request(options)
      .then(function checkExpectationsAfterRequest (resp) {
        expect(resp.headers['content-type']).toEqual('application/json');

        if (expectedResponse)
          expect(resp.statusCode).toEqual(expectedResponse);

        if (!dataToCompare) return;

        if (typeof dataToCompare === 'string')
          expect(resp.body).toEqual(dataToCompare);
        else if (typeof dataToCompare === 'object')
          expect(JSON.parse(resp.body)).toEqual(dataToCompare);
      });
  };
}
