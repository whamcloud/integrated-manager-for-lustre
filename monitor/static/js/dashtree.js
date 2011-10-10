
    /* http://stackoverflow.com/questions/2068272/getting-a-jquery-selector-for-an-element */
    jQuery.fn.getPath = function () {
        if (this.length != 1) throw 'Requires one element.';

        var path, node = this;
        while (node.length) {
            var realNode = node[0], name = realNode.localName;
            if (!name) break;
            name = name.toLowerCase();

            var parent = node.parent();

            var siblings = parent.children(name);
            if (siblings.length > 1) { 
                name += ':eq(' + siblings.index(realNode) + ')';
            }

            path = name + (path ? '>' + path : '');
            node = parent;
        }

        return path;
    };

    closed_states = {};
    function dashtree_toggle_closed(item, state, duration) {
        /* state==true means 'closed' */
        if (state == null) {
            state = !item.hasClass('closed')
        }
        if (state != item.hasClass('closed')) {
            if (state) {
                var style = 'hide';
            } else {
                var style = 'show'; 
            }
            item.children('ul').animate({height: style, opacity: style}, duration); 
            item.toggleClass('closed', state)
            closed_states[item.getPath()] = state;
            if (state) {
                item.children('div.open_icon').replaceWith("<div class='closed_icon'></div>");
            } else {
                item.children('div.closed_icon').replaceWith("<div class='open_icon'></div>");
            }
        }
    }

    function dashtree_suggest_closed(element) {
        if (!(element.getPath() in closed_states)) {
          dashtree_toggle_closed(element, true, 0);
        }
    }

    function dashtree() {
        $('li.collapsible').each(function() {
                /* Insert expand all and collapse all links */
                if ($(this).find('li.collapsible').size() == 0) {
                    return;
                }
                
                $("<a href='#' class='tree_all expand_all'>Show all</a>").insertBefore($(this).children('ul'))
                $("<span>&nbsp;/&nbsp;</span><a href='#' class='tree_all collapse_all'>Hide all</a>").insertBefore($(this).children('ul'));

            });

            $('a.expand_all').click(function(event) {
                dashtree_toggle_closed($(this).parent(), false, 0);
                $(this).parent().find('li.collapsible').each(function() {
                    dashtree_toggle_closed($(this), false, 0);
                });
                event.stopPropagation();
            });

            $('a.collapse_all').click(function(event) {
                $(this).parent().find('li.collapsible').each(function() {
                    dashtree_toggle_closed($(this), true, 0);
                });
                dashtree_toggle_closed($(this).parent(), true, 0);
                event.stopPropagation();
            });

            function collapsible_empty(element) {
                if (element.find('ul.tree').find('li').size() == 0) {
                    return true;
                } else {
                    return false;
                }
            }


            $('li.collapsible').each(function(item) {
                /* Apply any closedness states stored in closed_states */
                if ($(this).getPath() in closed_states) {
                    $(this).toggleClass('closed', closed_states[$(this).getPath()])
                }

                if (collapsible_empty($(this))) {
                    $(this).toggleClass('closed', true);
                }
            });

            /* Hide children of nodes with 'closed' class */
            $('li.collapsible').each(function() {
                if ($(this).hasClass('closed')) {
                    $(this).children('ul').hide();
                }
            });

            /* Apply open/closed icon overlays */
            $('li.collapsible').each(function() {
                if (collapsible_empty($(this))) {
                    return;
                }
                if ($(this).hasClass('closed')) {
                    $("<div class='closed_icon'></div>").insertBefore($(this).children('ul'));
                } else {
                    $("<div class='open_icon'></div>").insertBefore($(this).children('ul'));
                }
            });

            /* Add click handler */
            $('li.collapsible').click(function(event) {
                if (collapsible_empty($(this))) {
                    return;
                }
                dashtree_toggle_closed($(this));
                event.stopPropagation();
            });
    }
