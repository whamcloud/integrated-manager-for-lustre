// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


(function () {
  'use strict';

  angular.module('progress', []).directive('progressCircle', ['d3', function (d3) {
    return {
      scope: {
        radius: '=',
        complete: '@'
      },
      replace: true,
      restrict: 'E',
      template: '<div class="progress-circle"><svg></svg></div>',
      link: function (scope, element) {
        var diameter = scope.radius * 2,
          innerCircleRadius = scope.radius - (scope.radius / 8);

        element.css({width: diameter, height: diameter});

        var svg = d3.select(element.find('svg')[0])
          .attr('width', diameter)
          .attr('height', diameter)
          .append('g')
          .attr('transform', 'translate(' + scope.radius + ',' + scope.radius + ')');

        var circle = svg.append('circle')
          .attr('r', 0);

        circle
          .transition(500)
          .attr('r', innerCircleRadius);

        var pie = d3.layout.pie()
          .value(function (d) { return d.value; })
          .sort(d3.ascending);

        var arc = d3.svg.arc()
          .outerRadius(scope.radius)
          .innerRadius(innerCircleRadius);

        var values = ['elapsed', 'remaining'],
          color = d3.scale.ordinal()
            .domain(values)
            .range(values);

        function arcTween(a) {
          /*jshint validthis:true */
          var i = d3.interpolate(this.current, a);
          this.current = i(0);
          return function(t) { return arc(i(t)); };
        }

        /**
         * Updates the progress circle.
         * @param {number} complete
         */
        function update(complete) {
          if (complete == null) {
            complete = 0;
          }

          complete = parseInt(complete, 10);

          if (_.isNaN(complete)) {
            throw new Error('Complete not a number! Got %s'.sprintf(complete));
          }

          if (complete < 0 || complete > 100) {
            throw new Error('Complete not between 0 and 100 inclusive! Got %s'.sprintf(complete));
          }

          var slices = d3.entries({
            elapsed: complete,
            remaining: 100 - complete
          });

          // Text: data join
          var text = svg.selectAll('text').data([complete]);

          // Text: enter
          text.enter()
            .append('text')
            .style('font-size', scope.radius / 2 + 'px');

          // Text: enter + update
          text
            .text(function (d) { return d + '%'; })
            .attr('x', function () {
              var rect = this.getBoundingClientRect();

              return -1 * (rect.width / 2);
            })
            .attr('y', function () {
              var rect = this.getBoundingClientRect();

              return (scope.radius - rect.height) / 2;
            });


          // Path: data join
          var path = svg.selectAll('path').data(pie(slices));

          // Path: update
          path.transition()
            .duration(200)
            .attrTween('d', arcTween);

          // Path: enter
          path.enter()
            .append('path')
            .attr('class', function(d) { return color(d.data.key); })
            .attr('d', arc)
            .each(function (d) { this.current = d; });
        }

        scope.$watch('complete', update);
      }
    };
  }]);
}());
