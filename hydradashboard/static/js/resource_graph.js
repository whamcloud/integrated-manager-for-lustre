
function load_resource_graph(container_name, target_id) {
    invoke_api_call(api_post, "get_target_resource_graph/", {target_id: target_id},
    success_callback = function(data)
    {
     container = $("#" + container_name)
     render_resource_graph(container, data.response.graph);
    });
}

function render_resource_graph(container, graph) {
  markup = ""
  $.each(graph.nodes, function(i, node) {
    markup += "<div class='block' style='width: " + graph.item_width + "px; height: " + graph.item_height + "px; position: absolute; left: " + node.left + "px; top: " + node.top + "px; border-color: " + node.highlight + " ' id='" + node.id + "'>"
        markup += "<div class='block_header'>"
          markup += "<img src='" + node.icon + "'>"
          markup += "<span class='block_title'>" + node.type + "</span><br>"
        markup += "</div>"
        markup += "<span class='block_body'>"
            markup += "<a href='/hydracm/#storage_resource_" + node.id + "'>" + node.title + "</a>"
        markup += "</span>"
    markup += "</div>"

  });
  $.each(graph.edges, function(i, edge) {
    markup += "<div class='connector " + edge[0] + " " + edge[1] + "'></div>"
  });

  container.css("width", graph.width + "px");
  container.css("height", graph.height + "px");
  container.html(markup);
  initPageObjects();
}


