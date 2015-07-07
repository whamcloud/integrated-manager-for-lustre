describe('server actions', function () {
  'use strict';

  var serverActions, hosts, detectFs, rewriteTargetConfig, installUpdates;

  beforeEach(module('server'));

  beforeEach(inject(function (_serverActions_) {
    serverActions = _serverActions_;

    hosts = [
      {
        id: 1,
        resource_uri: '/api/host/1',
        server_profile: {
          managed: true
        }
      }
    ];

    detectFs = serverActions[0];
    rewriteTargetConfig = serverActions[1];
    installUpdates = serverActions[2];
  }));

  it('should be an array', function () {
    expect(serverActions).toEqual(jasmine.any(Array));
  });

  it('should contain actions', function () {
    expect(serverActions).toEqual([
      {
        value: 'Detect File Systems',
        message: 'Detecting File Systems',
        tooltip: 'detect_file_systems-tooltip',
        helpTopic: 'detect_file_systems-dialog',
        jobClass: 'DetectTargetsJob',
        convertToJob: jasmine.any(Function)
      },
      {
        value: 'Re-write Target Configuration',
        message: 'Updating file system NIDs',
        tooltip: 'rewrite_target_configuration-tooltip',
        helpTopic: 'rewrite_target_configuration-dialog',
        jobClass: 'UpdateNidsJob',
        convertToJob: jasmine.any(Function),
        isDisabled: jasmine.any(Function)
      },
      {
        value: 'Install Updates',
        message: 'Install updates',
        tooltip: 'install_updates_configuration-tooltip',
        helpTopic: 'install_updates_dialog',
        jobClass: 'UpdateJob',
        convertToJob: jasmine.any(Function),
        isDisabled: jasmine.any(Function)
      }
    ]);
  });

  it('should convert detect file systems hosts to a job', function () {


    var result = detectFs.convertToJob(hosts);

    expect(result).toEqual([{
      class_name: 'DetectTargetsJob',
      args: {
        hosts: [ '/api/host/1' ]
      }
    }]);
  });

  it('should check if a re-write target configuration host is disabled', function () {


    var result = rewriteTargetConfig.isDisabled(hosts[0]);

    expect(result).toBe(false);
  });

  it('should convert install updates hosts to a job', function () {
    var result = installUpdates.convertToJob(hosts);

    expect(result).toEqual([{
      class_name: 'UpdateJob',
      args: {
        host_id: 1
      }
    }]);
  });
});
