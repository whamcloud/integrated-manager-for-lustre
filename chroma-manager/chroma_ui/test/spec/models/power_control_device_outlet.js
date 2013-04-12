//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

describe('Power Control Device Outlet', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'services'));


  it('should have a method to see if the outlet has power', inject(function (PowerControlDeviceOutlet) {
    var states = {
      on: true,
      off: false,
      unknown: null
    };

    Object.keys(states).forEach(function (state) {
      var deviceOutlet = new PowerControlDeviceOutlet({has_power: states[state]});

      expect(deviceOutlet.hasPower()).toEqual(state);
    });
  }));
});
