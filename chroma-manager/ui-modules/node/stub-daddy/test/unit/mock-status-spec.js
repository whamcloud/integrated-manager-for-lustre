/*jshint node: true*/
'use strict';

var mockStatusModule = require('../../mock-status').wiretree;
var config = {
  methods: {
    GET: 'GET',
    PUT: 'PUT'
  }
};

var url = require('url');
var querystring = require('querystring');
var models = require('../../models').wiretree(config, url, querystring);

describe('test mock status', function() {
  var request, requestMatcher, mockStatus, logger, _;

  beforeEach(function() {
    request = new models.Request(config.methods.GET, '/system/status', {}, {});
    requestMatcher = jasmine.createSpy('requestMatcher').and.returnValue(true);
    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'warn', 'fatal', 'trace']);
    _ = require('lodash-mixins');
    mockStatus = mockStatusModule(requestMatcher, logger, _);
  });

  describe('test recording requests', function () {
    beforeEach(function () {
      request = new models.Request(config.methods.GET, '/system/status', {}, {});

      mockStatus.flushRequests();
      mockStatus.recordRequest(request);
    });

    it('should record the request', function () {
      expect(mockStatus.requests.length).toEqual(1);
    });

    it('should only have one entry of a request even if the request is sent multiple times', function () {
      mockStatus.recordRequest(request);
      expect(mockStatus.requests.length).toEqual(1);
    });
  });

  describe('test the mock api state', function () {

    var unregisteredCalls = [
      {id: 1}
    ];
    var unsatisfiedEntries = [
      {id: 2}
    ];

    var dataProvider = [
      {
        request: unregisteredCalls,
        entry: [],
        errors: []
      },
      {
        request: null,
        entry: [],
        errors: [
          {
            state: 'ERROR',
            message: 'Call made to non-existent mock',
            data: new models.Request('GET', '/system/status', {}, {})
          }
        ]
      },
      {
        request: unregisteredCalls,
        entry: unsatisfiedEntries,
        errors: [
          {
            state: 'ERROR',
            message: 'Call to expected mock not satisfied.',
            data: {id: 2}
          }
        ]
      },
      {
        request: null,
        entry: unsatisfiedEntries,
        errors: [
          {
            state: 'ERROR',
            message: 'Call made to non-existent mock',
            data: new models.Request(config.methods.GET, '/system/status', {}, {})
          },
          {
            state: 'ERROR',
            message: 'Call to expected mock not satisfied.',
            data: {id: 2}
          }
        ]
      }
    ];

    dataProvider.forEach(function(json) {
      describe('each request in data provider', function() {
        var errors, requestStore;
        beforeEach(function() {
          requestStore = jasmine.createSpyObj('requestStore', ['findEntriesByRequest', 'getEntries']);
          mockStatus.recordRequest(request);

          requestStore.findEntriesByRequest.and.returnValue(json.request);
          requestStore.getEntries.and.returnValue(json.entry);

          errors = mockStatus.getMockApiState(requestStore);
        });

        it('should call requestStore.findEntriesByRequest with the request parameter', function() {
          expect(requestStore.findEntriesByRequest.calls.argsFor(0)).toEqual([request]);
        });

        it('should call requestStore.getEntries with a filter function', function() {
          expect(requestStore.getEntries).toHaveBeenCalledWith(jasmine.any(Function));
        });

        it('should return expected errors', function() {
          expect(errors).toEqual(json.errors);
        });
      });
    });
  });

  describe('to verify requests status', function () {

    var requestStore, entries, requests, request1, response1, entry1, request2, response2, entry2;
    beforeEach(function () {
      request1 = new models.Request(
        config.methods.PUT,
        '/api/filesystem/',
        {},
        {}
      );
      response1 = new models.Response(
        200,
        {key: 'value'},
        {}
      );
      entry1 = new models.RequestEntry(request1, response1, 1, []);

      request2 = new models.Request(
        config.methods.GET,
        '/api/alert/',
        {},
        {}
      );
      response2 = new models.Response(
        200,
        {key2: 'value2'},
        {}
      );
      entry2 = new models.RequestEntry(request2, response2, 0, []);

      entries = [entry1, entry2];

      requestStore = {
        getEntries: jasmine.createSpy('getEntries').and.callFake(function (fn) {
          return fn(entries);
        })
      };

      requests = [
        new models.Request(
          config.methods.PUT,
          '/api/filesystem/',
          {},
          {}
        ),
        new models.Request(
          config.methods.GET,
          '/api/alert/',
          {},
          {}
        )
      ];

      mockStatus = mockStatusModule(requestMatcher, logger, _);
    });

    it('should be satisfied if an empty array is passed as the requests', function () {
      var result = mockStatus.haveRequestsBeenSatisfied(requestStore, []);
      expect(result).toBeTruthy();
    });

    it('should be satisfied when all calls are made to each entry', function () {
      entry1.updateCallCount();
      var result = mockStatus.haveRequestsBeenSatisfied(requestStore, requests);
      expect(result).toBeTruthy();
    });

    it('should NOT be satisfied if not all required calls are made to each entry', function () {
      var result = mockStatus.haveRequestsBeenSatisfied(requestStore, requests);
      expect(result).toBeFalsy();
    });

    it('should NOT be satisfied if the filtered entries length doesn\'t match requests length', function () {
      entry1.updateCallCount();
      // add an additional request that must be present. Only two of the three will match and thus this
      // should fail.
      requests.push(new models.Request(
        config.methods.GET,
        '/api/notRegistered/',
        {},
        {}
      ));
      var result = mockStatus.haveRequestsBeenSatisfied(requestStore, requests);
      expect(result).toBeFalsy();
    });
  });
});

