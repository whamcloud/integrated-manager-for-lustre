$(document).ready(function() {
// JavaScript Document	var chart;
	$('.text').mouseover(function() {
		$(this).css("border","0px solid #444444");
	});
	$('.text').mouseout(function() {
		$(this).css("border","0px solid black");
	});
	
	$("#plusImg").click(function(){
		$(".panel").toggle("slow");
		$("#plusImg").hide();
		$("#minusImg").show();
		$(this).toggleClass("active");
		return false;
	});
	
	$("#minusImg").click(function(){
		$(".panel").toggle("slow");
		$(this).toggleClass("active");
		$("#minusImg").hide();$("#plusImg").show();
		return false;
	});
	
	$("#alertAnchor").click(function(){
		$("#alertsDiv").toggle("slideUp");
		$("#alertAnchor").css("color",'red');
		$("#eventsDiv").hide();
		$("#eventsAnchor").css("color",'#7A848B');
		$("#jobsAnchor").css("color",'#7A848B');
		$("#jobsDiv").hide();
	});
	$("#eventsAnchor").click(function(){
		$("#eventsDiv").toggle("slideUp");
		$("#eventsAnchor").css("color",'#0040FF');
		$("#alertsDiv").hide();
		$("#alertAnchor").css("color",'#7A848B');
		$("#jobsDiv").hide();
		$("#jobsAnchor").css("color",'#7A848B');
	});
	$("#jobsAnchor").click(function(){
		$("#jobsDiv").toggle("slideUp");
		$("#jobsAnchor").css("color",'green');
		$("#alertsDiv").hide();
		$("#alertAnchor").css("color",'#7A848B');
		$("#eventsDiv").hide();
		$("#eventsAnchor").css("color",'#7A848B');
	});

	$(".tab_content").hide(); //Hide all content
	$("ul.tabs li:first").addClass("active").show(); //Activate first tab
	$(".tab_content:first").show(); //Show first tab content

	//On Click Event
	$("ul.tabs li").click(function() {

		$("ul.tabs li").removeClass("active"); //Remove any "active" class
		$(this).addClass("active"); //Add "active" class to selected tab
		$(".tab_content").hide(); //Hide all tab content

		var activeTab = $(this).find("a").attr("href"); //Find the href attribute value to identify the active tab + content
		$(activeTab).fadeIn(); //Fade in the active ID content
		return false;
	});
	
	// Dialog Link
	$('input[name=alertsPopUpBtn]').click(function(){
		$('#alerts_dialog').dialog('open');
		return false;
	});
	$('input[name=eventsPopUpBtn]').click(function(){
		$('#events_dialog').dialog('open');
		return false;
	});
	
	$('input[name=alertsPopUpBtn]').hover(function() {
		$(this).css('cursor','pointer');
	}, function() {
		$(this).css('cursor','auto');
	});
	$('input[name=eventsPopUpBtn]').hover(function() {
		$(this).css('cursor','pointer');
	}, function() {
		$(this).css('cursor','auto');
	});
	
	/********* URL's start*****************/
	var getVolumes = "";
	
	/********* URL's end*****************/
 });
