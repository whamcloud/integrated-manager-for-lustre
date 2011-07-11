
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

    // borrowed ideas from rrdgraph
    function si_scale_value(value, suffix, base, decimals) {
        // work around lack of default parameter vals
        var base = typeof(base) != 'undefined' ? base : 1000;
        var decimals = typeof(decimals) != 'undefined' ? decimals : 2;

        var units = [
            "a",        // 10e-18 Atto
            "f",        // 10e-15 Femto
            "p",        // 10e-12 Pico
            "n",        // 10e-9  Nano
            "u",        // 10e-6  Micro
            "m",        // 10e-3  Milli
            " ",        // Base
            "k",        // 10e3   Kilo
            "M",        // 10e6   Mega
            "G",        // 10e9   Giga
            "T",        // 10e12  Tera
            "P",        // 10e15  Peta
            "E"         // 10e18  Exa
        ];
        var uindex;
        var magfact;
        var newval = value * 1.0;
        var pivot = 6;
        var unit = "?";

        if (value == 0.0 || isNaN(value)) {
            uindex = 0;
            magfact = 1.0;
        } else {
            uindex = Math.floor(Math.log(Math.abs(value)) / Math.log(base));
            magfact = Math.pow(base, uindex);
            newval = value / magfact;
        }
        if (uindex <= pivot && uindex >= -pivot) {
            unit = units[pivot + uindex];
        }

        return newval.toFixed(decimals) + unit + suffix;
    }

    var spark_hash = {};
    var line_color = "blue";
    function refresh_sparklines() {
        $('span.sparkline').each(function(item) {
            var span_id = $(this).attr('id');
            $.getJSON('/monitor/sparklines/' + span_id, function(data) {
                var span_vals = new Array();
                $.each(data, function(k, v) {
                    var data_id = span_id + '_' + k;
                    var spark_span = 'span.sparkline[id=' + span_id + ']';
                    var val_span = 'span.sparkvals[id=' + span_id + ']';
                    if (typeof spark_hash[data_id] == 'undefined') {
                        var vals = new Array();
                        spark_hash[data_id] = vals;
                    }
                    span_vals.push(k + ": " + si_scale_value(v, "B/s"));
                    // 30 data points * 5sec == 2.5min of data -- useful
                    // for a "telemetry squiggle". 
                    spark_hash[data_id].push(v);
                    if (spark_hash[data_id].length > 30) {
                        spark_hash[data_id].shift();
                    }
                    $(spark_span).sparkline(spark_hash[data_id], { composite: true, lineColor: line_color });
                    $(val_span).html(span_vals.join(", "));
                    // This is really kind of awful -- but it serves the
                    // purpose of usefully compositing two sparklines
                    // in one span.  If we need to display more than two
                    // we'll figure something else out.
                    if (line_color == "blue") {
                      line_color = "red";
                    } else {
                      line_color = "blue";
                    }
                });
            });
        });

        setTimeout('refresh_sparklines()', 5000);
    }
