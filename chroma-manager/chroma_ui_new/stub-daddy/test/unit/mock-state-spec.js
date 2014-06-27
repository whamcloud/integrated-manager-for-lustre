/*jshint node: true*/
'use strict';

var configulator = require('configulator');
var configModule = require('../../config').wiretree;
var mockStateModule = require('../../mock-state').wiretree;
var modelsModule = require('../../models').wiretree;
var url = require('url');
var querystring = require('querystring');

describe('test mock status module', function () {

  var mockStatus, mockState, requestStore, config, request, models;

  beforeEach(function() {
    config = configModule(configulator);
    mockStatus = jasmine.createSpyObj('mockStatus', ['getMockApiState']);
    requestStore = jasmine.createSpy('requestStore');
    request = {
      method: config.methods.GET
    };
    models = modelsModule(config, url, querystring);

    mockState = mockStateModule(mockStatus, requestStore, config, models);

    mockStatus.getMockApiState.and.returnValue({});
  });

  it('should call getMockApiState with the request store', function () {
    mockState(request);
    expect(mockStatus.getMockApiState).toHaveBeenCalledWith(requestStore);
  });

  it('should have a response indicating good standing', function() {
    var response = mockState(request);
    expect(response).toEqual({
      status: 200,
      data: {},
      headers: config.standardHeaders
    });
  });

  it('should not return anything if the method is not a GET', function() {
    request = {
      method: config.methods.POST
    };

    var response = mockState(request);

    expect(response.status).toEqual(400);
  });

});
