'use strict';

var rewire = require('rewire');
var commandUtils = rewire('../../../socket-router/command-utils');
var fixtures = require('../../integration/fixtures');
var λ = require('highland');
var _ = require('lodash-mixins');

describe('command utils', function () {
  var revoke, apiRequest, responseStream;

  beforeEach(function () {
    responseStream = λ();
    apiRequest = jasmine.createSpy('apiRequest').and.returnValue(responseStream);

    revoke = commandUtils.__set__({
      apiRequest: apiRequest
    });
  });

  afterEach(function () {
    revoke();
  });

  describe('get commands', function () {
    var req, result, commandData;

    beforeEach(function () {
      req = {};

      commandData = [
        {
          objects: [
            {
              id: 1,
              complete: true
            },
            {
              id: 2,
              complete: true
            }
          ]
        }
      ];

      result = commandUtils.getCommands(req);
    });

    it('should call apiRequest', function () {
      result.each(_.noop);

      expect(apiRequest).toHaveBeenCalledOnceWith('/command', req);
    });

    it('should send the original data', function () {
      result
        .collect()
        .each(function (data) {
          expect(data).toEqual(commandData[0].objects);
        });

      responseStream.write(commandData[0]);
      responseStream.end();
    });

    it('should catch an error in the response', function (done) {
      result
        .errors(function onError (err) {
          expect(err).toEqual(error);
          done();
        })
        .each(done.fail);

      var error = new Error('im an error');

      responseStream.write(new StreamError(error));
      responseStream.end();
    });

    it('should not return on unfinished commands', function () {
      var incompleteData = _.cloneDeep(commandData);
      incompleteData[0].objects[0].complete = false;

      responseStream.write(incompleteData[0]);
      responseStream.end();

      result
        .otherwise(λ(['nope']))
        .each(function (x) {
          expect(x).toEqual('nope');
        });
    });
  });

  describe('get steps', function () {
    var commands, jobs, commandStream, resultStream, spy;

    beforeEach(function () {
      spy = jasmine.createSpy('spy');
      commands = fixtures.command()
        .twoServers.response.data.objects;

      jobs = fixtures.job()
        .twoServers.response.data;

      commandStream = λ();
      resultStream = commandUtils.getSteps(commandStream.flatten());
    });

    it('should call apiRequest with job ids', function () {
      commandStream.write(commands);
      commandStream.end();

      resultStream.each(_.noop);

      expect(apiRequest).toHaveBeenCalledOnceWith('/job', {
        qs: {
          id__in: ['2', '3'],
          limit: 0
        },
        jsonMask: 'objects(step_results,steps)'
      });
    });

    it('should return the steps', function (done) {
      commandStream.write(commands);
      commandStream.end();
      responseStream.write(jobs);
      responseStream.end();

      resultStream
        .errors(done.fail)
        .collect()
        .each(function (x) {
          var obj = _(jobs.objects)
            .pluck('step_results')
            .map(_.values)
            .flatten().value();

          expect(x).toEqual(obj);
          done();
        });
    });

    it('should return empty on no data', function () {
      commandStream.end();

      resultStream
        .otherwise(λ(['nope']))
        .each(spy);

      expect(spy).toHaveBeenCalledOnceWith('nope');
    });

    it('should throw on error', function (done) {
      var boom = new Error('boom!');
      commandStream.write(new StreamError(boom));

      resultStream
        .errors(function (err) {
          expect(err).toEqual(err);
          done();
        })
        .each(done.fail);
    });
  });
});

function StreamError (err) {
  this.__HighlandStreamError__ = true;
  this.error = err;
}
