describe('Power Control Device', function () {
  'use strict';

  var PowerControlDeviceModel, $httpBackend;

  beforeEach(module('models', 'ngResource', 'interceptors', 'services'));

  beforeEach(inject(function (_PowerControlDeviceModel_, _$httpBackend_) {
    PowerControlDeviceModel = _PowerControlDeviceModel_;
    $httpBackend = _$httpBackend_;
  }));

  it('should flatten nested data when persisting to server', function () {
    var expectedData = {
      outlets: ['foo', 'bar', 'baz'],
      device_type: 'test'
    };

    var data = {
      outlets: [
        {resource_uri: 'foo'},
        {resource_uri: 'bar'},
        {resource_uri: 'baz'}
      ],
      device_type: {
        resource_uri: 'test'
      }
    };

    var baseUri = '/api/power_control_device/';

    $httpBackend
      .expectPUT('%s%s'.sprintf(baseUri, 'foo/'), window.lodash.extend({id: 'foo'}, expectedData))
      .respond({outlets: []});

    var powerControlDeviceModel = new PowerControlDeviceModel(window.lodash.extend({id: 'foo'}, data));

    powerControlDeviceModel.$update();

    $httpBackend.flush();

    $httpBackend
      .expectPOST(baseUri, expectedData)
      .respond({outlets: []});

    PowerControlDeviceModel.save(data);

    $httpBackend.flush();
  });

  it('should vivify nested outlets', function () {
    $httpBackend.expectGET().respond([{
      outlets: [{resource_ur: 'foo'}]
    }]);

    var powerControlDeviceModels = PowerControlDeviceModel.query();

    $httpBackend.flush();

    expect(powerControlDeviceModels[0].outlets[0].$update).toBeDefined();
  });

  it('should have a method to calculate the outlets intersection of a host and pdu', function () {
    var data = {
      outlets: [
        {
          host: '1/2/3',
          identifier: 'outlet 1'
        },
        {
          host: '4/5/6',
          identifier: 'outlet 2'
        },
        {
          host: '1/2/3',
          identifier: 'outlet 3'
        }
      ]
    };

    var powerControlDeviceModel = new PowerControlDeviceModel(data);

    var result = powerControlDeviceModel.getOutletHostIntersection({
      resource_uri: '1/2/3'
    });

    expect(result).toEqual([data.outlets[0], data.outlets[2]]);
  });
});
