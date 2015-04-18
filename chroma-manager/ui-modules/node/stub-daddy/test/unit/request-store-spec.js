/*jshint node: true*/
'use strict';

var url = require('url');
var querystring = require('querystring');
var modelsModule = require('../../models').wiretree;
var requestStoreModule = require('../../request-store').wiretree;
var dataStore = require('./data-store');
var configulator = require('configulator');
var configModule = require('../../config').wiretree;
var _ = require('lodash-mixins');

describe('request store module', function () {

  var request, response, requestEntry, entry, config, requestStore, models, requestMatcher, logger,
    dependencies, mockStatus;

  beforeEach(function () {
    request = dataStore.searchRequest;
    response = dataStore.searchResponse;
    dependencies = dataStore.searchDependencies;
    requestEntry = dataStore.requestEntry;
    config = configModule(configulator);
    models = modelsModule(config, url, querystring);
    requestMatcher = jasmine.createSpy('requestMatcher');
    logger = jasmine.createSpyObj('logger', ['info', 'debug', 'trace', 'logByLevel']);
    mockStatus = {
      haveRequestsBeenSatisfied: jasmine.createSpy('haveRequestsBeenSatisfied')
    };
    requestStore = requestStoreModule(requestMatcher, models, logger, _, mockStatus);

    requestStore.addEntry(request, response, 0, dependencies);
  });

  describe('single request matching', function () {

    beforeEach(function () {
      requestMatcher.and.returnValue(true);
      mockStatus.haveRequestsBeenSatisfied.and.returnValue(true);

      var entries = requestStore.findEntriesByRequest(request);
      entry = entries.shift();
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

    it('should have entry.dependencies set', function () {
      expect(requestEntry.dependencies).toEqual(dependencies);
    });

    it('should call requestMatcher with request and entry.request', function() {
      expect(requestMatcher).toHaveBeenCalledWith(request, entry.request);
    });
  });

  describe('multiple requests matching', function () {
    var request2, response2, dependencies2, entries;

    beforeEach(function () {
      // Add a similar entry that contains the same request but a different response
      request2 = _.cloneDeep(request);
      response2 = _.cloneDeep(response);
      response2.data.name = 'Joe';
      dependencies2 = _.cloneDeep(dependencies);
      dependencies2[0].data.name = 'Joe';
      requestStore.addEntry(request2, response2, 0, dependencies2);

      requestMatcher.and.returnValue(true);
    });

    describe('all of which have not had their dependencies met', function () {
      beforeEach(function () {
        mockStatus.haveRequestsBeenSatisfied.and.returnValue(false);
        entries = requestStore.findEntriesByRequest(request);
      });

      it('should return an empty array', function () {
        expect(entries).toEqual([]);
      });

    });

    describe('some of which have their dependencies met', function () {
      var request3, response3;
      beforeEach(function () {
        // Add a similar entry that contains the same request but a different response
        request3 = _.cloneDeep(request);
        request3.data.name = 'doesnt match';
        response3 = _.cloneDeep(response);
        response3.data.name = 'Wayne';
        requestStore.addEntry(request3, response3, 0, []);

        mockStatus.haveRequestsBeenSatisfied.and.callFake(function (context, dependencies) {
          // Let the second entry and the entry that doesn't match be satisfied. This will be a good test
          // because we should NOT get back the entry that doesn't match, even though its dependencies have
          // been met.
          return dependencies.length === 0 || dependencies[0].data.name === 'Joe';
        });

        entries = requestStore.findEntriesByRequest(request);
      });

      it('should contain a single entry', function () {
        expect(entries.length).toEqual(1);
      });

      it('should return the entry who\'s dependencies have been met', function () {
        expect(entries).toEqual([requestStore.getEntries()[1]]);
      });
    });
  });
});
