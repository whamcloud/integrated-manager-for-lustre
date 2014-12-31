'use strict';

/*jslint maxlen: 500 */
//jscs:disable maximumLineLength

module.exports = function () {
  return {
    reversedTrace: {
      request: {
        method: 'POST',
        url: '/api/client_error/',
        data: {
          method: 'post',
          message: 'Come on sourcemaps',
          stack: 'at /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/iml/dashboard/dashboard-filter-controller.js:161:14\n\
at apply /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/angular/angular.js:10795:20\n\
at fn /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/angular/angular.js:19036:16\n\
at this /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/angular/angular.js:12632:28\n\
at $eval /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/angular/angular.js:12730:22\n\
at $apply /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/angular/angular.js:19035:20\n\
at apply /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/jquery/jquery.js:4371:8\n\
at apply /Users/wkseymou/projects/chroma/chroma-manager/chroma_ui_new/source/chroma_ui/bower_components/jquery/jquery.js:4057:27\n',
          url: 'https://lotus-34vm3.iml.intel.com/ui/dashboard/server/2'
        },
        headers: {
          cookie: 'csrftoken=z2WVzbtXqNvydVFACW8HlCyVpebt82M1; sessionid=a948605f1cb2dc8b1e929b8371d41a45',
          'x-csrftoken': 'z2WVzbtXqNvydVFACW8HlCyVpebt82M1',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/39.0.2171.95 Safari/537.36'
        }
      },
      response: {
        status: 201,
        headers: {},
        data: {}
      },
      dependencies: [],
      expires: 1
    },
    originalTrace: {
      path: '/srcmap-reverse',
      options: {
        method: 'post',
        message: 'Come on sourcemaps',
        stack: 'Error: Come on sourcemaps.\n\
at Object.DashboardFilterCtrl.$scope.filter.onFilterView (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:38:7096)\n\
at https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:14:4896\n\
at https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:14:16407\n\
at Scope.$eval (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:12:12643)\n\
at Scope.$apply (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:12:12989)\n\
at HTMLButtonElement.<anonymous> (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:14:16389)\n\
at HTMLButtonElement.jQuery.event.dispatch (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:7:13226)\n\
at HTMLButtonElement.elemData.handle (https://localhost:8000/static/chroma_ui/built-fd5ce21b.js:7:8056)\n',
        url: 'https://lotus-34vm3.iml.intel.com/ui/dashboard/server/2',
        headers: {
          Cookie: 'csrftoken=z2WVzbtXqNvydVFACW8HlCyVpebt82M1; sessionid=a948605f1cb2dc8b1e929b8371d41a45',
          'X-CSRFToken': 'z2WVzbtXqNvydVFACW8HlCyVpebt82M1',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/39.0.2171.95 Safari/537.36'
        }
      }
    }
  };
};
