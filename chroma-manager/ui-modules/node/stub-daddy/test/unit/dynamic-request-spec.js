'use strict';

var dynamicRequest, mockState, requestStore, mockRequest, searchRequest, searchResponse, entry, logger;
var config = {
  methods: {
    GET: 'GET'
  }
};

var url = require('url');
var querystring = require('querystring');
var models = require('../../models').wiretree(config, url, querystring);
var _ = require('lodash-mixins');

describe('test dynamic-request module', function () {

  beforeEach(function () {
    mockState = jasmine.createSpyObj('mockState', ['recordRequest']);
    requestStore = jasmine.createSpyObj('requestStore', ['findEntriesByRequest']);
    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'warn', 'fatal', 'trace']);

    dynamicRequest = require('../../dynamic-request').wiretree(mockState, requestStore, models, logger, _);
  });

  var bodies = [{name: 'will'}, undefined];
  bodies.forEach(function(body) {
    describe('handling request with a body of ' + JSON.stringify(body), function() {
      var myResponse;
      beforeEach(function() {
        generateDependencies(body);
        requestStore.findEntriesByRequest.and.returnValue([entry]);

        myResponse = dynamicRequest(mockRequest, body);
      });

      it('should call findEntriesByRequest with searchRequest', function () {
        expect(requestStore.findEntriesByRequest).toHaveBeenCalledWith(searchRequest);
      });

      it('should call recordRequest with searchRequest', function() {
        expect(mockState.recordRequest).toHaveBeenCalledWith(searchRequest);
      });

      it('should have the expected response', function() {
        expect(myResponse).toEqual(entry.response);
      });
    });
  });
});

/**
 * @param {Object} body
 */
function generateDependencies(body) {
  mockRequest = {
    method: config.methods.GET,
    url: '/target',
    headers: {
      host: 'localhost:8888',
      connection: 'keep-alive',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35"' +
        '.0.1916.153 Safari/537.36',
      'content-type': 'text/plain; charset=utf-8',
      accept: '*/*',
      'accept-encoding': 'gzip,deflate,sdch',
      'accept-language': 'en-US,en;q=0.8',
      cookie: 'm=34e2:; csrftoken=Di8V2cFIUliMJVr0tNb8E4SrwCp5QMdg; sessionid=d2fa382c8a220126c1315c94af4bb42c'
    }
  };

  searchRequest = new models.Request(config.methods.GET, mockRequest.url, body || {}, mockRequest.headers);

  searchResponse = new models.Response(config.methods.GET, body || {}, mockRequest.headers);

  entry = new models.RequestEntry(searchRequest, searchResponse, 0);
}
