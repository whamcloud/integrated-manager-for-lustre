/*jshint node: true*/
'use strict';

var mockStatusModule = require('../../mock-status').wiretree;
var config = {
  methods: {
    GET: 'GET'
  }
};

var url = require('url');
var querystring = require('querystring');
var models = require('../../models').wiretree(config, url, querystring);

describe('test mock status', function() {
  var request, requestMatcher, mockStatus, logger;

  beforeEach(function() {
    request = new models.Request(config.methods.GET, '/system/status', {}, {});
    requestMatcher = jasmine.createSpy('requestMatcher').and.returnValue(true);
    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'warn', 'fatal']);
    mockStatus = mockStatusModule(requestMatcher, logger);
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
          requestStore = jasmine.createSpyObj('requestStore', ['findEntryByRequest', 'getEntries']);
          mockStatus.recordRequest(request);

          requestStore.findEntryByRequest.and.returnValue(json.request);
          requestStore.getEntries.and.returnValue(json.entry);

          errors = mockStatus.getMockApiState(requestStore);
        });

        it('should call requestStore.findEntryByRequest with the request parameter', function() {
          expect(requestStore.findEntryByRequest.calls.argsFor(0)).toEqual([request]);
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
});

