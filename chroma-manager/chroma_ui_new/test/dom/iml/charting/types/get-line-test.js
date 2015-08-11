describe('get line', function () {
  'use strict';

  beforeEach(module('charting', function ($provide) {
    $provide.value('$location', {
      absUrl: fp.always('https://foo/')
    });
  }));

  var getLine, div, svg, query, queryAll, d3;

  beforeEach(inject(function (_getLine_, _d3_) {
    d3 = _d3_;
    getLine = _getLine_;

    div = document.createElement('div');

    svg = document
      .createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', 500);
    svg.setAttribute('height', 500);

    div.appendChild(svg);

    query = svg.querySelector.bind(svg);
    queryAll = svg.querySelectorAll.bind(svg);
  }));

  it('should be a function', function () {
    expect(getLine).toEqual(jasmine.any(Function));
  });

  describe('instance', function () {
    var inst, spy, setup;

    beforeEach(inject(function (d3) {
      inst = getLine();
      spy = jasmine.createSpy('spy');

      var x = d3.scale.linear();
      x.range([0, 100]);

      var y = d3.scale.linear();
      y.range([100, 0]);

      svg = d3.select(svg)
        .append('g');

      setup = function setup (d) {
        x.domain([0, d3.max(d, fp.lensProp('x'))]);
        y.domain([0, d3.max(d, fp.lensProp('y'))]);

        inst
          .xScale(x)
          .yScale(y)
          .xValue(fp.lensProp('x'))
          .xComparator(fp.eq)
          .yValue(fp.lensProp('y'));

        svg
          .datum(d)
          .call(inst);
      };
    }));

    it('should have a color accessor', function () {
      expect(inst.color()).toEqual('#000000');
    });

    it('should have a color setter', function () {
      inst.color('#111111');

      expect(inst.color()).toEqual('#111111');
    });

    it('should have an xValue accessor', function () {
      expect(inst.xValue()).toBe(fp.noop);
    });

    it('should have an xValue setter', function () {
      inst.xValue(spy);

      expect(inst.xValue()).toBe(spy);
    });

    it('should have a yValue accessor', function () {
      expect(inst.yValue()).toBe(fp.noop);
    });

    it('should have a yValue setter', function () {
      inst.yValue(spy);

      expect(inst.yValue()).toBe(spy);
    });

    it('should have an xScale accessor', function () {
      expect(inst.xScale()).toBe(fp.noop);
    });

    it('should have a xScale setter', function () {
      inst.xScale(spy);

      expect(inst.xScale()).toBe(spy);
    });

    it('should have a yScale accessor', function () {
      expect(inst.yScale()).toBe(fp.noop);
    });

    it('should have a yScale setter', function () {
      inst.yScale(spy);

      expect(inst.yScale()).toBe(spy);
    });

    it('should have an xComparator accessor', function () {
      expect(inst.xComparator()).toBe(fp.noop);
    });

    it('should have an xComparator setter', function () {
      inst.xComparator(spy);

      expect(inst.xComparator()).toBe(spy);
    });

    describe('with data', function () {
      var line;

      beforeEach(function () {
        setup([
          {
            x: 0,
            y: 0
          },
          {
            x: 1,
            y: 1
          },
          {
            x: 2,
            y: 2
          }
        ]);

        line = query('.clipPath1 path.line1');
      });

      it('should add a clip path', function () {
        expect(query('clipPath#clip1')).toBeDefined();
      });

      it('should set the clipping to rectangle the scale width', function () {
        expect(query('rect').getAttribute('width')).toEqual('100');
      });

      it('should set the clipping rectangle to the scale height', function () {
        expect(query('rect').getAttribute('height')).toEqual('100');
      });

      it('should set the corresponding clip path', function () {
        expect(query('.clipPath1').getAttribute('clip-path')).toEqual('url(https://foo/#clip1)');
      });

      it('should calculate the line from data', function () {
        expect(line.getAttribute('d')).toEqual('M0,100L50,50L100,0');
      });

      it('should set the color on the line', function () {
        expect(line.getAttribute('stroke')).toEqual('#000000');
      });

      it('should set stroke-dasharray to the total length of the line', function () {
        line.getAttribute('stroke-dasharray')
          .split(' ')
          .map(fp.curry(1, parseInt))
          .forEach(expectToBeGreaterThan0);

        function expectToBeGreaterThan0 (x) {
          expect(x).toBeGreaterThan(0);
        }
      });

      it('should set stroke-dashoffset to the total length of the line', function () {
        expect(parseInt(line.getAttribute('stroke-dashoffset')))
          .toBeGreaterThan(0);
      });

      it('should animate stroke-dashoffset to 0', function () {
        window.flushD3Transitions();

        expect(line.getAttribute('stroke-dashoffset')).toEqual('0');
      });

      it('should animate stroke-dasharray to 0', function () {
        window.flushD3Transitions();

        expect(line.getAttribute('stroke-dasharray')).toBeNull();
      });

      describe('and updating', function () {
        beforeEach(function () {
          window.flushD3Transitions();

          setup([
            {
              x: 1,
              y: 1
            },
            {
              x: 2,
              y: 2
            },
            {
              x: 3,
              y: 3
            }
          ]);
        });

        it('should start with previous coordinates', function () {
          expect(line.getAttribute('d')).toEqual('M0,100L50,50L100,0');
        });

        it('should update the line data and keep the previous point', function () {
          expect(d3.select(line).datum()).toEqual([
            {
              x: 0,
              y: 0
            },
            {
              x: 1,
              y: 1
            },
            {
              x: 2,
              y: 2
            },
            {
              x: 3,
              y: 3
            }
          ]);
        });

        it('should end with new coordinates', function () {
          window.flushD3Transitions();

          expect(line.getAttribute('d'))
            .toEqual('M33.33333333333333,66.66666666666667L66.66666666666666,33.333333333333336L100,0');
        });

        it('should end with new data', function () {
          window.flushD3Transitions();

          expect(d3.select(line).datum()).toEqual([
            {
              x: 1,
              y: 1
            },
            {
              x: 2,
              y: 2
            },
            {
              x: 3,
              y: 3
            }
          ]);
        });
      });

      describe('and exiting', function () {
        beforeEach(function () {
          window.flushD3Transitions();

          setup([]);

          window.flushD3Transitions();
        });

        it('should remove the line', function () {
          expect(query('.clipPath1 path.line1')).toBeNull();
        });
      });
    });
  });
});
