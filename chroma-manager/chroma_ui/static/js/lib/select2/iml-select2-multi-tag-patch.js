//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/**
 * @fileOverview This is a patch for select2 tags to make them stylable.
 */

window.Select2.class.multi.prototype.addSelectedChoice = function (data) {
  /*jshint
    strict: false
    quotmark: true
    curly: false
    eqeqeq: false
  */
  function killEvent(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  var enableChoice = !data.locked,
    enabledItem = $(
      "<li class='select2-search-choice'>" +
        "    <div></div>" +
        "    <a href='#' onclick='return false;' class='select2-search-choice-close' tabindex='-1'></a>" +
        "</li>"),
    disabledItem = $(
      "<li class='select2-search-choice select2-locked'>" +
        "<div></div>" +
        "</li>");
  var choice = enableChoice ? enabledItem : disabledItem,
    id = this.id(data),
    val = this.getVal(),
    formatted;

  if (this.opts.formatTagCssClass) {
    choice.addClass(this.opts.formatTagCssClass(data));
  }

  formatted = this.opts.formatSelection(data, choice.find("div"));
  if (formatted != undefined) {
    choice.find("div").replaceWith("<div>" + this.opts.escapeMarkup(formatted) + "</div>");
  }

  if (enableChoice) {
    choice.find(".select2-search-choice-close")
      .bind("mousedown", killEvent)
      .bind("click dblclick", this.bind(function (e) {
        if (!this.enabled) return;

        $(e.target).closest(".select2-search-choice").fadeOut('fast', this.bind(function () {
          this.unselect($(e.target));
          this.selection.find(".select2-search-choice-focus").removeClass("select2-search-choice-focus");
          this.close();
          this.focusSearch();
        })).dequeue();
        killEvent(e);
      })).bind("focus", this.bind(function () {
        if (!this.enabled) return;
        this.container.addClass("select2-container-active");
        this.dropdown.addClass("select2-drop-active");
      }));
  }

  choice.data("select2-data", data);
  choice.insertBefore(this.searchContainer);

  val.push(id);
  this.setVal(val);
};
