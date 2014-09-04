describe('Remove used LNet options', function () {
  'use strict';

  beforeEach(module('configure-lnet-module'));

  var removeUsedLnetOptions, LNET_OPTIONS;

  beforeEach(inject(function (_removeUsedLnetOptionsFilter_, _LNET_OPTIONS_) {
    removeUsedLnetOptions = _removeUsedLnetOptionsFilter_;
    LNET_OPTIONS = _LNET_OPTIONS_;
  }));

  it('should filter out used values', function () {
    var networkInterfaces = createNetworkInterfaces([5, 6, 7]);
    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterfaces[0]);

    expect(filtered).toEqual([
      { name: 'Not Lustre Network', value: -1 },
      { name: 'Lustre Network 0', value: 0 },
      { name: 'Lustre Network 1', value: 1 },
      { name: 'Lustre Network 2', value: 2 },
      { name: 'Lustre Network 3', value: 3 },
      { name: 'Lustre Network 4', value: 4 },
      { name: 'Lustre Network 5', value: 5 },
      { name: 'Lustre Network 8', value: 8 },
      { name: 'Lustre Network 9', value: 9 }
    ]);
  });

  it('should always have Not Lustre Network', function () {
    var networkInterface = createNetworkInterface(-1);
    var networkInterface0 = createNetworkInterface(0);
    var networkInterfaces = [networkInterface, networkInterface, networkInterface0];

    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterface0);

    expect(filtered).toEqual(_.toArray(LNET_OPTIONS));
  });

  it('should work when all options are used', function () {
    var values = _.pluck(LNET_OPTIONS, 'value');
    var networkInterfaces = createNetworkInterfaces(values);
    var filtered = removeUsedLnetOptions(LNET_OPTIONS, networkInterfaces, networkInterfaces[1]);

    expect(filtered).toEqual([ { name : 'Not Lustre Network', value : -1 }, { name : 'Lustre Network 0', value : 0 } ]);
  });

  /**
   * Creates an object representing a network interface
   * @param {Number} id
   * @returns {{nid: {lnd_network: Number}}}
   */
  function createNetworkInterface (id) {
    return { nid: {lnd_network: id} };
  }

  /**
   * Creates a list of objects representing network interfaces.
   * @param {Array} ids
   * @returns {Array<Object>}
   */
  function createNetworkInterfaces (ids) {
    return ids.map(function create (id) {
      return createNetworkInterface(id);
    });
  }
});
