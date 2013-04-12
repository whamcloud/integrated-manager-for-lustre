//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

describe('Power Control Type Model', function () {
  'use strict';


  beforeEach(module('models', 'ngResource', 'services'));

  it('should call the correct endpoint', inject(function (PowerControlTypeModel, $httpBackend) {
    $httpBackend.expectGET('/api/power_control_type/').respond({});

    PowerControlTypeModel.get();

    $httpBackend.flush();
  }));
});
