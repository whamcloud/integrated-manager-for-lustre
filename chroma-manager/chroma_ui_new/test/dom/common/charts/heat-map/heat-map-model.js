describe('heat map model', function () {
  'use strict';

  var d3, heatMapModel, $el, $heatMapGroup, selection;

  beforeEach(module('charts'));

  beforeEach(inject(function (_d3_, heatMapModelFactory) {
    d3 = _d3_;
    heatMapModel = heatMapModelFactory();
    $el = angular.element('<svg class="foo"><g></g></svg>');
    $heatMapGroup = $el.find('g');
    selection = d3.select($heatMapGroup[0]);
  }));

  it('should return early when there is no data', function () {
    setup([]);

    expect($heatMapGroup.children().length).toBe(0);
  });

  it('should have destroy as noop before selection has been passed', function () {
    expect(heatMapModel.destroy).toBe(_.noop);
  });

  describe('one data point', function () {
    beforeEach(function () {
      setup([
        {
          key: 'label',
          values: [
            {
              z: 50,
              x: new Date('11/12/13')
            }
          ]
        }
      ]);

      d3.timer.flush();
    });

    it('should have one row', function () {
      expect($heatMapGroup.find('.row').length).toBe(1);
    });

    it('should have one cell', function () {
      expect($heatMapGroup.find('.cell').length).toBe(1);
    });

    it('should have the row start at 0,0', function () {
      expect(selection.select('.row').attr('transform')).toEqual('');
    });

    it('should have the cell take the whole height', function () {
      expect(selection.select('.cell').attr('height')).toEqual(heatMapModel.height().toString());
    });

    it('should have the cell take the whole width', function () {
      expect(selection.select('.cell').attr('width')).toEqual(heatMapModel.width().toString());
    });

    it('should fill the cell', function () {
      expect(selection.select('.cell').attr('fill')).toEqual('#fbecec');
    });

    describe('exit', function () {
      beforeEach(function () {
        setup([]);
      });

      it('should remove the model', function () {
        expect(selection.select('.heat-map-model').node()).toBeNull();
      });
    });
  });

  describe('multiple points', function () {
    beforeEach(function () {
      setup([
        {
          key: 'a',
          values: [
            {
              z: 50,
              x: new Date('11/12/13')
            },
            {
              z: 70,
              x: new Date('11/13/13')
            }
          ]
        },
        {
          key: 'b',
          values: [
            {
              z: 90,
              x: new Date('11/12/13')
            },
            {
              z: 60,
              x: new Date('11/13/13')
            }
          ]
        }
      ]);

      d3.timer.flush();
    });

    it('should have two rows', function () {
      expect($heatMapGroup.find('.row').length).toBe(2);
    });

    it('should have 4 cells', function () {
      expect($heatMapGroup.find('.cell').length).toBe(4);
    });

    it('should have row a first', function () {
      var transform = selection.selectAll('.row').filter(function (d) {
        return d.key === 'a';
      }).attr('transform');

      expect(transform).toEqual('');
    });

    it('should have the row b last', function () {
      var transform = selection.selectAll('.row').filter(function (d) {
        return d.key === 'b';
      }).attr('transform');

      expect(transform).toEqual('translate(0,200)');
    });

    it('should have row a cell 1 lightest', function () {
      var fill = selection.select('.row')
        .selectAll('.cell').filter(':first-child').attr('fill');

      expect(fill).toEqual(heatMapModel.lowColor());
    });

    it('should have row b cell 1 darkest', function () {
      var fill = selection.selectAll('.row').filter(':last-child')
        .selectAll('.cell').filter(':first-child').attr('fill');

      expect(fill).toEqual(heatMapModel.highColor());
    });
  });

  describe('mouse events', function () {
    var mouseOverSpy, mouseOutSpy, mouseMoveSpy, mouseClickSpy, data;

    beforeEach(function () {
      angular.element('body').append($el);

      mouseOverSpy = jasmine.createSpy('onMouseOver');
      mouseOutSpy = jasmine.createSpy('onMouseOut');
      mouseMoveSpy = jasmine.createSpy('onMouseMove');
      mouseClickSpy = jasmine.createSpy('onMouseClick');

      heatMapModel.onMouseOver(mouseOverSpy);
      heatMapModel.onMouseOut(mouseOutSpy);
      heatMapModel.onMouseMove(mouseMoveSpy);
      heatMapModel.onMouseClick(mouseClickSpy);

      data = {
        z: 50,
        x: new Date('11/12/13')
      };

      setup([
        {
          key: 'label',
          values: [data]
        }
      ]);

      d3.timer.flush();
    });


    afterEach(function () {
      $el.remove();
    });

    it('should fire on mouse over of a cell', function () {
      var event = new MouseEvent('mouseover', {
        bubbles: true
      });

      $heatMapGroup.find('.cell')[0].dispatchEvent(event);

      var expected = _.clone(data);
      expected.key = 'label';
      expected.size = 960;


      expect(mouseOverSpy).toHaveBeenCalledOnceWith(expected, jasmine.any(Object));
    });

    it('should fire on mouse out of a cell', function () {
      var event = new MouseEvent('mouseout', {
        bubbles: true
      });

      $heatMapGroup.find('.cell')[0].dispatchEvent(event);

      var expected = _.clone(data);
      expected.key = 'label';
      expected.size = 960;

      expect(mouseOutSpy).toHaveBeenCalledOnceWith(expected, jasmine.any(Object));
    });

    it('should fire on mouse move in a cell', function () {
      var event = new MouseEvent('mousemove', {
        bubbles: true
      });

      $heatMapGroup.find('.cell')[0].dispatchEvent(event);

      var expected = _.clone(data);
      expected.key = 'label';
      expected.size = 960;

      expect(mouseMoveSpy).toHaveBeenCalledOnceWith(expected, jasmine.any(Object));
    });

    it('should fire on mouse click in a cell', function () {
      var event = new MouseEvent('click', {
        bubbles: true
      });

      $heatMapGroup.find('.cell')[0].dispatchEvent(event);

      var expected = _.clone(data);
      expected.key = 'label';
      expected.size = 960;

      expect(mouseClickSpy).toHaveBeenCalledOnceWith(expected, jasmine.any(Object));
    });
  });

  function setup (data) {
    heatMapModel.transitionDuration(0);

    selection
      .datum(data)
      .call(heatMapModel);
  }
});