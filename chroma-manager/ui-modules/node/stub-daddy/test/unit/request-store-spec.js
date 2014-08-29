/*jshint node: true*/
'use strict';

var url = require('url');
var querystring = require('querystring');
var modelsModule = require('../../models').wiretree;
var requestStoreModule = require('../../request-store').wiretree;
var dataStore = require('./data-store');
var configulator = require('configulator');
var configModule = require('../../config').wiretree;

describe('request store module', function () {

  var request, response, requestEntry, entry, config, requestStore, models, requestMatcher, logger;
  beforeEach(function () {
    request = dataStore.searchRequest;
    response = dataStore.searchResponse;
    requestEntry = dataStore.requestEntry;
    config = configModule(configulator);
    models = modelsModule(config, url, querystring);
    requestMatcher = jasmine.createSpy('requestMatcher');
    logger = jasmine.createSpyObj('logger', ['info', 'debug']);
    requestStore = requestStoreModule(requestMatcher, models, logger);

    requestStore.addEntry(request, response, 0);
    requestMatcher.and.returnValue(true);

    entry = requestStore.findEntryByRequest(request);
  });

  it('should have entry.request set', function () {
    expect(entry.request).toEqual(requestEntry.request);
  });

  it('should have entry.expires set', function() {
    expect(entry.expires).toEqual(requestEntry.expires);
  });

  it('should have entry.respone set', function() {
    expect(entry.response).toEqual(requestEntry.response);
  });

  it('should have entry.remainingCalls set', function() {
    expect(entry.remainingCalls).toEqual(requestEntry.remainingCalls);
  });

  it('should call requestMatcher with request and entry.request', function() {
    expect(requestMatcher).toHaveBeenCalledWith(request, entry.request);
  });
});
