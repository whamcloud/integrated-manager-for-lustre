//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


function load_resource_graph(container, target_id) {
    Api.get("target/" + target_id + "/resource_graph/", {},
    success_callback = function(data)
    {
     render_resource_graph(container, data.graph);
    });
}

function render_resource_graph(container, graph) {
  var markup = "";
  $.each(graph.nodes, function(i, node) {
    markup += "<div class='block' style='width: " + graph.item_width + "px; height: " + graph.item_height + "px; position: absolute; left: " + node.left + "px; top: " + node.top + "px; border-color: " + node.highlight + " ' id='" + node.id + "'>"
        markup += "<div class='block_header'>";
          markup += "<img src='" + node.icon + "'>";
          markup += "<span class='block_title'>" + node.type + "</span><br>"
        markup += "</div>";
        markup += "<span class='block_body'>";
            markup += uri_properties_link("/api/storage_resource/" + node.id + "/", node.title)
        markup += "</span>";
    markup += "</div>"

  });
  $.each(graph.edges, function(i, edge) {
    markup += "<div class='connector " + edge[0] + " " + edge[1] + "'></div>";
  });

  container.css("width", graph.width + "px");
  container.css("height", graph.height + "px");
  container.html(markup);
  initPageObjects();
}


