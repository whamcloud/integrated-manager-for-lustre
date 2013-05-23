//
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


var ContextualHelp = (function(){
  var compiled_snippet_template = _.template("<div class='ui-helper-clearfix ui-state-<%= state%> ui-corner-all'><div class='contextual_help_icon'><span class='ui-icon ui-icon-<%= icon %>'></span></div><div class='contextual_help'><%= content %></div></div>");

  function set_default(value, default_value) {
    return ( _.isUndefined(value) ? default_value : value );
  }

  function populate_snippet(container) {
    // skip if no topic
    var topic = $(container).data('topic');
    if (_.isUndefined(topic)) {
      return true;
    }

    var icon = set_default($(container).data('icon'), 'info');

    var state = set_default($(container).data('state'), 'highlight');

    $(container).removeClass('help_loader')
      .addClass('help_loaded')
      .html(compiled_snippet_template({
        content: window.HELP_TEXT[topic],
        icon: icon,
        state: state
      }));

    return true;
  }

  function load_snippets(parent_selector, snippet_selector) {

    var selector = set_default(snippet_selector,'div.help_loader');
    var snippets;
    if (_.isElement(parent_selector) || _.isString(parent_selector) ) {
      snippets = $(parent_selector).find(selector);
    }
    else {
      snippets = $(selector);
    }

    snippets.each(function () { populate_snippet(this); });

  }

  function help_elements() {
    function help_qtip(element, click) {
      var event;
      if (click) {
        event = 'click';
      } else {
        event = 'mouseenter';
      }

      element.qtip({
        content: {
          text: window.HELP_TEXT[element.data('topic')]
        },
        position: {
          viewport: $(window),
          my: 'top center',
          at: 'bottom center'
        },
        show: { event: event }
      });
    }

    // tooltip on a link/button - hover activated
    $('a.help_hover, button.help_hover').each(function () {
      var el = $(this);
      if (!el.data('qtip')) {
        help_qtip(el, false);
      }
    });

    // a button with text and the ? icon - click activated
    $('a.help_button').each(function() {
      var el = $(this);
      if (!el.data('qtip')) {
        el.button({icons: {primary: 'ui-icon-help'}});
        help_qtip(el, true);
      }
    });

    // a button with only ? - click activated
    $('a.help_button_small').each(function() {
      var el = $(this);
      if (!el.data('qtip')) {
        el.css({ padding: '0px', width: '24px', height: '24px'})
          .button({icons: {primary: 'ui-icon-help'}})
          .find('.ui-icon').css('margin-left', '-3px');
        help_qtip(el, true);
      }
    });
  }

  // populate all tooltip based help and set a trigger to re-scan for
  // new help items after every ajax request (as they may have been
  // loaded dynamically by said request)
  function init() {
    help_elements();
    $(document).ajaxComplete(help_elements);
  }

  return {
    init: init,
    load_snippets: load_snippets
  };
}());



/*
 * Examples:
<button class='help_hover' data-topic='test'>Button Text</a>
<a class='help_hover' data-topic='test'>My help</a>
<a class='help_button' data-topic='test'>My help</a>
<a class='help_button_small' data-topic='test'></a>
<div class='help_loader' data-topic='advanced_settings' data-icon='info' data-state='highlight|error' />
  - data-icon (optional) can be any valid icon from jquery ui
    reference: http://jqueryui.com/themeroller/ (at the bottom; hover over for name)
    default: info
  - data-state (optional) should be any one of "highlight", "error"
    default: highlight
*/
