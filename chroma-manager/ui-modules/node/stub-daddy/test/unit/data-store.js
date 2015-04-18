/*jshint node: true*/
'use strict';

var config = {
  methods: {
    GET: 'GET'
  }
};

var url = require('url');
var querystring = require('querystring');
var models = require('../../models').wiretree(config, url, querystring);

var body = {name: 'will'};
var mockRequest = {
  method: config.methods.GET,
  url: '/target',
  headers: {
    host: 'localhost:8888',
    connection: 'keep-alive',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko)"' +
      ' Chrome/35.0.1916.153 Safari/537.36',
    'content-type': 'text/plain; charset=utf-8',
    accept: '*/*',
    'accept-encoding': 'gzip,deflate,sdch',
    'accept-language': 'en-US,en;q=0.8',
    cookie: 'm=34e2:; csrftoken=Di8V2cFIUliMJVr0tNb8E4SrwCp5QMdg; sessionid=d2fa382c8a220126c1315c94af4bb42c'
  }
};

var searchRequest = new models.Request(config.methods.GET, mockRequest.url, body, mockRequest.headers);

var searchResponse = new models.Response(config.methods.GET, mockRequest.headers, body);

var searchDependencies = [
  new models.Response(config.methods.PUT, mockRequest.url, body, mockRequest.headers)
];

var requestEntry = new models.RequestEntry(searchRequest, searchResponse, 0, searchDependencies);

module.exports = {
  mockRequest: mockRequest,
  searchRequest: searchRequest,
  searchResponse: searchResponse,
  searchDependencies: searchDependencies,
  requestEntry: requestEntry
};
