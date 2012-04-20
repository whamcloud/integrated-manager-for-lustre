//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var ApiCache = function(){
  var Filesystem = Backbone.Model.extend({
    urlRoot: "/api/filesystem/"
  });

  var FilesystemCollection = Backbone.Collection.extend({
    model: Filesystem,
    url: "/api/filesystem/"
  });

  var Target = Backbone.Model.extend({
    urlRoot: "/api/target/"
  });

  var TargetCollection = Backbone.Collection.extend({
    model: Target,
    url: "/api/target/"
  });

  var Host = Backbone.Model.extend({
    urlRoot: "/api/host/"
  });

  var HostCollection = Backbone.Collection.extend({
    model: Host,
    url: "/api/host/"
  });

  var collections = {
    'filesystem': new FilesystemCollection(),
    'target': new TargetCollection(),
    'host': new HostCollection()
  };

  var outstanding_requests = {
    'filesystem': [],
    'target': [],
    'host': []
  };

  _.each(collections, function(collection, resource_name) {
    collection.add(CACHE_INITIAL_DATA[resource_name]);
  });

  function get(obj_type, obj_id) {
    var collection = collections[obj_type];

    var object = collection.get(obj_id);
    if (!object) {
      if (_.include(outstanding_requests[obj_type], obj_id)) {
        return null;
      } else {
        outstanding_requests[obj_type].push(obj_id);
        collection.fetch({
            add:true,
            data:{id:obj_id},
            success:function () {
              outstanding_requests[obj_type] = _.reject(outstanding_requests[obj_type], function (x) {return x == obj_id;});
            }
        });
      }
    }
    return object;
  }

  function put(resource, obj)
  {
    var collection = collections[resource];
    if (collection){
      // If this is a cached resource
      var model = collection.get(obj.id);
      if (!model) {
        collection.add(obj);
      } else {
        model.set(obj);
      }
    }
  }

  function list(resource) {
    var collection = collections[resource];
    return collection.toJSON();
  }

  function purge(resource, id){
    var collection = collections[resource];
    if (collection){
      // If this is a cached resource
      var model = collection.get(id);
      if (model) {
        // If we had a cached copy of this object
        collection.remove(model);
      }
    }
  }

  return {
    get: get,
    put: put,
    purge: purge,
    list: list
  }
}();
