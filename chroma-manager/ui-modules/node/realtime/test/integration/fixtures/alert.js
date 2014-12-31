'use strict';

module.exports = function () {
 return {
   greenHealth: {
     request: {
       method: 'GET',
       url: '/api/alert/?active=true&severity__in=WARNING&severity__in=ERROR&limit=0',
       data: {},
       headers: {}
     },
     response: {
       status: 200,
       headers: {},
       data: {
         meta: {
           limit: 20,
           next: null,
           offset: 0,
           previous: null,
           total_count: 0
         },
         objects: []
       }
     },
     dependencies: [],
     expires: 0
   },
   yellowHealth: {
     request: {
       method: 'GET',
       url: '/api/alert/?active=true&severity__in=WARNING&severity__in=ERROR&limit=0',
       data: {},
       headers: {}
     },
     response: {
       status: 200,
       headers: {},
       data: {
         meta: {
           limit: 20,
           next: null,
           offset: 0,
           previous: null,
           total_count: 1
         },
         objects: [
           {
             active: false,
             affected: [
               {
                 content_type_id: 35,
                 id: 1,
                 resource_uri: '/api/host/1/'
               }
             ],
             alert_item: '/api/host/1/',
             alert_item_content_type_id: 35,
             alert_item_id: 1,
             alert_item_str: 'lotus-32vm15.iml.intel.com',
             alert_type: 'HostOfflineAlert',
             begin: '2014-12-19T21:47:41.543919+00:00',
             created_at: '2014-12-19T21:47:41.543919+00:00',
             dismissed: false,
             end: '2014-12-19T21:48:02.201082+00:00',
             id: '2',
             message: 'Host is offline lotus-32vm15.iml.intel.com',
             resource_uri: '/api/alert/2/',
             severity: 'WARNING'
           }
         ]
       }
     },
     dependencies: [],
     expires: 0
   },
   redHealth: {
     request: {
       method: 'GET',
       url: '/api/alert/?active=true&severity__in=WARNING&severity__in=ERROR&limit=0',
       data: {},
       headers: {}
     },
     response: {
       status: 200,
       headers: {},
       data: {
         meta: {
           limit: 20,
           next: null,
           offset: 0,
           previous: null,
           total_count: 1
         },
         objects: [
           {
             active: false,
             affected: [
               {
                 content_type_id: 35,
                 id: 1,
                 resource_uri: '/api/host/1/'
               }
             ],
             alert_item: '/api/host/1/',
             alert_item_content_type_id: 35,
             alert_item_id: 1,
             alert_item_str: 'lotus-32vm15.iml.intel.com',
             alert_type: 'HostOfflineAlert',
             begin: '2014-12-19T21:47:41.543919+00:00',
             created_at: '2014-12-19T21:47:41.543919+00:00',
             dismissed: false,
             end: '2014-12-19T21:48:02.201082+00:00',
             id: '2',
             message: 'Host is offline lotus-32vm15.iml.intel.com',
             resource_uri: '/api/alert/2/',
             severity: 'ERROR'
           }
         ]
       }
     },
     dependencies: [],
     expires: 0
   }
 };
};
