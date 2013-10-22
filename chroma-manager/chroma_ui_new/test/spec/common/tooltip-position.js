describe('Tooltip positioning service', function () {
  'use strict';

  var tooltipPosition, $window;

  beforeEach(module('tooltipPosition'));

  beforeEach(module(function ($provide) {
    $window = {
      innerWidth: 500,
      innerHeight: 300
    };

    $provide.value('$window', $window);
  }));

  beforeEach(inject(function (_tooltipPosition_) {
    tooltipPosition = _tooltipPosition_;
  }));

  it('should expose directions', function () {
    expect(tooltipPosition.DIRECTIONS).toEqual({
      TOP: 'top',
      BOTTOM: 'bottom',
      RIGHT: 'right',
      LEFT: 'left'
    });
  });

  it('should provide default properties', function () {
    expect(tooltipPosition.defaults).toEqual(jasmine.any(Object));

    _.forEach(tooltipPosition.DIRECTIONS, function (direction) {
      var obj = tooltipPosition.defaults[direction];

      expect(obj).toEqual(jasmine.any(Object));
      expect(Object.keys(obj)).toContain('position');
      expect(Object.keys(obj)).toContain('overflows');
    });
  });


  describe('Positioner', function () {
    it('should provide a positioner', function () {
      expect(tooltipPosition.positioner).toEqual(jasmine.any(Function));

      var position = {
        top: 10,
        left: 10,
        right: 20,
        bottom: 20,
        height: 10,
        width: 10
      };

      var tooltip = {
        getBoundingClientRect: jasmine.createSpy('getBoundingClientRect').andCallFake(function () {
          return position;
        })
      };

      expect(tooltipPosition.positioner(tooltip)).toEqual(position);

      expect(tooltipPosition.positioner($window)).toEqual({
        top: 0,
        left: 0,
        right: 500,
        bottom: 300,
        width: 500,
        height: 300
      });
    });

    it('should know the current position', function () {
      var positioner = tooltipPosition.positioner($window);

      $window.innerHeight = 5;

      expect(positioner).toEqual({
        height: 5,
        top: 0,
        left: 0,
        right: 500,
        bottom: 5,
        width: 500
      });
    });
  });
});
