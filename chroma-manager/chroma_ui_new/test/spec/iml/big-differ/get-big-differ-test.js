describe('The big differ', function () {
  'use strict';

  beforeEach(module('bigDifferModule', 'dataFixtures'));

  var bigDiffer;

  beforeEach(inject(function (_bigDiffer_) {
    bigDiffer = _bigDiffer_;
  }));

  it('should be a collection of diff tools', function () {
    expect(bigDiffer).toEqual({
      diffObj3: jasmine.any(Function),
      diffObjInColl3: jasmine.any(Function),
      mergeObj: jasmine.any(Function),
      mergeColl: jasmine.any(Function)
    });
  });

  describe('diffObj3', function () {
    var fixture, lndNetworkLens, diff;

    beforeEach(inject(function (networkInterfaceDataFixtures) {
      fixture = angular.copy(networkInterfaceDataFixtures[0].in[0]);

      lndNetworkLens = fp.flowLens(
        fp.lensProp('nid'),
        fp.lensProp('lnd_network')
      );

      diff = bigDiffer.diffObj3({
        lndNetwork: lndNetworkLens
      });
    }));

    it('should return a differ', function () {
      expect(diff).toEqual(jasmine.any(Function));
    });

    it('should tell records are the same', function () {
      expect(diff(fixture, fixture, fixture)).toEqual({});
    });

    it('should work with bad values', function () {
      expect(diff(null, null, null)).toEqual({});
    });

    it('should tell if local changed', function () {
      var local = angular.copy(fixture);
      lndNetworkLens.set(7, local);

      expect(diff(fixture, local, fixture))
        .toEqual({
          lndNetwork: {
            name: 'lndNetwork',
            lens: jasmine.any(Function),
            resetInitial: jasmine.any(Function),
            resetLocal: jasmine.any(Function),
            diff: {
              initial: 3,
              remote: 3
            },
            type: 'local'
          }
        });
    });

    it('should tell if remote changed', function () {
      var remote = angular.copy(fixture);
      lndNetworkLens.set(8, remote);

      expect(diff(fixture, fixture, remote))
        .toEqual({
          lndNetwork: {
            name: 'lndNetwork',
            lens: jasmine.any(Function),
            resetInitial: jasmine.any(Function),
            resetLocal: jasmine.any(Function),
            diff: {
              initial: 3,
              remote: 8
            },
            type: 'remote'
          }
        });
    });

    it('should tell if there was a conflict', function () {
      var local = angular.copy(fixture);
      lndNetworkLens.set(9, local);

      var remote = angular.copy(fixture);
      lndNetworkLens.set(10, remote);

      expect(diff(fixture, local, remote))
        .toEqual({
          lndNetwork: {
            name: 'lndNetwork',
            lens: jasmine.any(Function),
            resetInitial: jasmine.any(Function),
            resetLocal: jasmine.any(Function),
            diff: {
              initial: 3,
              remote: 10
            },
            type: 'conflict'
          }
        });
    });

    it('should work with multiple lenses', function () {
      var inet4AddressLens = fp.lensProp('inet4_address');

      diff = bigDiffer.diffObj3({
        lndNetwork: lndNetworkLens,
        inet4Address: inet4AddressLens
      });


      var local = angular.copy(fixture);
      lndNetworkLens.set(6, local);
      inet4AddressLens.set('10.3.0.1', local);

      expect(diff(fixture, local, fixture))
        .toEqual({
          lndNetwork: {
            name: 'lndNetwork',
            lens: jasmine.any(Function),
            resetInitial: jasmine.any(Function),
            resetLocal: jasmine.any(Function),
            diff: {
              initial: 3,
              remote: 3
            },
            type: 'local'
          },
          inet4Address: {
            name: 'inet4Address',
            lens: jasmine.any(Function),
            resetInitial: jasmine.any(Function),
            resetLocal: jasmine.any(Function),
            diff: {
              initial: '10.3.0.0',
              remote: '10.3.0.0'
            },
            type: 'local'
          }
        });
    });
  });

  describe('diffObjInColl3', function () {
    var fixture, lndNetworkLens, diff;

    beforeEach(inject(function (networkInterfaceDataFixtures) {
      fixture = angular.copy(networkInterfaceDataFixtures[0].in[0]);

      var idLens = fp.lensProp('id');

      lndNetworkLens = fp.flowLens(
        fp.lensProp('nid'),
        fp.lensProp('lnd_network')
      );

      diff = bigDiffer.diffObjInColl3(
        idLens,
        {
          lndNetwork: lndNetworkLens
        },
        angular.copy(networkInterfaceDataFixtures[0].in),
        fp.__,
        angular.copy(networkInterfaceDataFixtures[0].in)
      );
    }));

    it('should return a differ', function () {
      expect(diff).toEqual(jasmine.any(Function));
    });

    it('should tell if local has changed', function () {
      lndNetworkLens.set(6, fixture);

      expect(diff(fixture)).toEqual({
        lndNetwork: {
          name: 'lndNetwork',
          lens: jasmine.any(Function),
          resetInitial: jasmine.any(Function),
          resetLocal: jasmine.any(Function),
          diff: {
            initial: 3,
            remote: 3
          },
          type: 'local'
        }
      });
    });
  });

  describe('mergeObj', function () {
    var fixture, lndNetworkLens, merge;

    beforeEach(inject(function (networkInterfaceDataFixtures) {
      fixture = angular.copy(networkInterfaceDataFixtures[0].in[0]);

      lndNetworkLens = fp.flowLens(
        fp.lensProp('nid'),
        fp.lensProp('lnd_network')
      );

      merge = bigDiffer.mergeObj({
        lndNetwork: lndNetworkLens
      });
    }));

    it('should return a merge function', function () {
      expect(merge).toEqual(jasmine.any(Function));
    });

    it('should merge local to remote', function () {
      var local = angular.copy(fixture);
      lndNetworkLens.set(5, local);

      expect(merge(local, fixture))
        .toEqual(local);
    });
  });

  describe('mergeColl', function () {
    var fixtures, lndNetworkLens, diff;

    beforeEach(inject(function (networkInterfaceDataFixtures) {
      fixtures = angular.copy(networkInterfaceDataFixtures[0].in);

      var idLens = fp.lensProp('id');

      lndNetworkLens = fp.flowLens(
        fp.lensProp('nid'),
        fp.lensProp('lnd_network')
      );

      diff = bigDiffer.mergeColl(
        idLens,
        {
          lndNetwork: lndNetworkLens
        },
        fp.__,
        fixtures
      );
    }));

    it('should return a differ', function () {
      expect(diff).toEqual(jasmine.any(Function));
    });

    it('should merge local changes', function () {
      var localFixtures = angular.copy(fixtures);
      lndNetworkLens.set(6, localFixtures[0]);

      var merged = diff(localFixtures);

      expect(lndNetworkLens(merged[0])).toEqual(6);
    });
  });
});
