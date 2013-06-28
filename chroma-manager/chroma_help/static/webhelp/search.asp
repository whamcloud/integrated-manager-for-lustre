<%
' ----------------------------------------------------------------------------
' Zoom Search Engine 6.0 (31/Oct/2011)
' ASP search script
' A fast custom website search engine using pre-indexed data files.
' Copyright (C) Wrensoft 2000 - 2011
'
' This script is designed for Classic ASP with VBScript 5.5 or later.
' If you wish to integrate the search page with a .NET website, you can use
' the native ASP.NET control instead (see Users Guide for more information).
'
' NOTE: YOU SHOULD NOT NEED TO MODIFY THIS SCRIPT. If you wish to customize
' the appearance of the search page, you should change the contents of the
' "search_template.html" file. See chapter 6 of the Users Guide for more
' details: http://www.wrensoft.com/zoom/usersguide.html
' 
' IF YOU NEED TO ADD ASP TO THE SEARCH PAGE, see this FAQ:
' http://www.wrensoft.com/zoom/support/faq_ssi.html
'
' email: zoom@wrensoft.com
' www: http://www.wrensoft.com
' ----------------------------------------------------------------------------
Dim UseUTF8, Charset, NoCharset, Codepage, MapAccents, MinWordLen, Highlighting, GotoHighlight, PdfHighlight, FormFormat, Logging, LogFileName
Dim MaxKeyWordLineLen, DictIDLen, NumKeywords, NumPages, DictReservedLimit, DictReservedPrefixes, DictReservedSuffixes, DictReservedNoSpaces
Dim WordSplit, ZoomInfo, Timing, DefaultToAnd, SearchAsSubstring, ToLowerSearchWords, ContextSize, MaxContextKeywords, AllowExactPhrase
Dim UseLinkTarget, LinkTarget, UseDateTime, WordJoinChars, Spelling, SpellingWhenLessThan, NumSpellings, UseCats, LinkBackURL
Dim DisplayNumber, DisplayTitle, DisplayMetaDesc, DisplayContext, DisplayTerms, DisplayScore, DisplayURL, DisplayDate, Version, SearchMultiCats
Dim AccentChars, NormalChars, StripDiacritics, UseZoomImage, Recommended, NumRecommended, RecommendedMax, DisplayFilesize, WeightProximity
Dim UseStemming, StemmingAlgo, OutputVariantBufferSize, NumVariants, PageInfoSize, MetaMoneyCurrency, MetaMoneyShowDec
Dim UseMetaFields, NumMetaFields, DisplayMetaFields, StartPtFailed, DisplayCatSummary, TruncateShowURL
Dim MaxMatches, MaxContextSeeks, MaxSearchTime

Dim STR_FORM_SEARCHFOR, STR_FORM_SUBMIT_BUTTON, STR_FORM_RESULTS_PER_PAGE, STR_FORM_CATEGORY, STR_FORM_CATEGORY_ALL, STR_FORM_MATCH
Dim STR_FORM_ANY_SEARCH_WORDS, STR_FORM_ALL_SEARCH_WORDS, STR_NO_QUERY, STR_RESULTS_FOR, STR_RESULTS_IN_ALL_CATEGORIES, STR_RESULTS_IN_CATEGORY
Dim STR_POWEREDBY, STR_NO_RESULTS, STR_RESULT, STR_RESULTS, STR_PHRASE_CONTAINS_COMMON_WORDS, STR_SKIPPED_FOLLOWING_WORDS
Dim STR_SKIPPED_PHRASE, STR_SUMMARY_NO_RESULTS_FOUND, STR_SUMMARY_FOUND_CONTAINING_ALL_TERMS, STR_SUMMARY_FOUND_CONTAINING_SOME_TERMS
Dim STR_SUMMARY_FOUND, STR_PAGES_OF_RESULTS, STR_POSSIBLY_GET_MORE_RESULTS, STR_ANY_OF_TERMS, STR_ALL_CATS, STR_DIDYOUMEAN, STR_SORTEDBY_RELEVANCE
Dim STR_SORTBY_RELEVANCE, STR_SORTBY_DATE, STR_SORTEDBY_DATE, STR_RESULT_TERMS_MATCHED, STR_RESULT_SCORE, STR_RESULT_URL, STR_RESULT_PAGES
Dim STR_RESULT_PAGES_PREVIOUS, STR_RESULT_PAGES_NEXT, STR_SEARCH_TOOK, STR_SECONDS, STR_MORETHAN, STR_MAX_RESULTS, STR_OR
Dim STR_RECOMMENDED, STR_CAT_SUMMARY

Dim zoomit, zoomfso, PerPageOptions
Dim query, queryForSearch, queryForHTML, queryForURL, metaParams
Dim per_page, NewSearch, zoompage, andq, zoomsort, selfURL, zoomtarget, zres_image, zres_target
Dim zoomcat, num_zoom_cats, query_zoom_cats
Dim UseWildCards, SkippedOutputStr, SkippedWords, SkippedExactPhrase
Dim sw_results, search_terms_ids, phrase_terms_ids
Dim catnames, NumCats, catpages, catindex, NumCatBytes
Dim IsZoomQuery
Dim pageinfofile, pageinfo_count, pageinfoline, fp_pagedata, FoundEOL, pgdataline, templine, newlinepos
Dim LogQuery, DateString, LogString
Dim metafields, meta_query
Dim wordsmatched, IsMaxLimitExceeded
Dim LinkBackJoinChar

%>
<!-- #include file="settings.asp" -->
<%
if (ScriptEngine <> "VBScript" OR ScriptEngineMajorVersion < 5) then
	Response.Write("This script requires VBScript 5.5 or later installed on the web server. Please download the latest Windows Script package from Microsoft and install this on your server, or consult your web host<br />")
	Response.End
end if
if (ScriptEngineMajorVersion = 5 AND ScriptEngineMinorVersion < 5 AND AllowExactPhrase = 1) then
	Response.Write("This script requires VBScript 5.5 or later installed on the web server. Please download the latest Windows Script package from Microsoft and install this on your server, or consult your web host<br />")
	Response.Write("Note that you may be able to run this on VBScript 5.1 if you have Exact Phrase matching disabled.<br />")
	Response.End
end if

Function MapPath(path)
	Dim IsHSP
	on error resume next
	IsHSP = Server.IsHSPFile
	if (err.Number = 0 AND IsHSP) then
		MapPath = Server.MapExternalPath(path) ' for HSP support
	else
		MapPath = Server.MapPath(path)
	end if
	on error goto 0
End Function

Function ConvertBinaryToString(Binary)
	Dim I, St
	For I = 1 To LenB(Binary)
		St = St & Chr(AscB(MidB(Binary, I, 1)))
	Next
	ConvertBinaryToString = St
End Function

Function GetPageData(index)
	fp_pagedata.Position = pgdataoffset(index)
	FoundEOL = False
	pgdataline = ""
	do while FoundEOL = False AND fp_pagedata.EOS = False
		templine = ConvertBinaryToString(fp_pagedata.Read(1024))
		newlinepos = InStr(templine, vbCr)
		if (newlinepos > 0) then
			FoundEOL = True
			templine = Left(templine, newlinepos)
		end if
		pgdataline = pgdataline & templine
	loop
	GetPageData = Split(pgdataline, "|")
End Function

function unUDate(intTimeStamp)
	unUDate = DateAdd("s", intTimeStamp, "01/01/1970 00:00:00")
end function


' Check for dependant files
set zoomfso = CreateObject("Scripting.FileSystemObject")
if (zoomfso.FileExists(MapPath("settings.asp")) = False OR zoomfso.FileExists(MapPath("zoom_wordmap.zdat")) = FALSE OR zoomfso.FileExists(MapPath("zoom_dictionary.zdat")) = FALSE) then
	Response.Write("<b>Zoom files missing error:</b> Zoom is missing one or more of the required index data files.<br />Please make sure the generated index files are uploaded to the same path as this search script.<br />")
	Response.End
end if

' ----------------------------------------------------------------------------
' Settings
' ----------------------------------------------------------------------------

' The options available in the dropdown menu for number of results
' per page
PerPageOptions = Array(10, 20, 50, 100)

' Index format information
Dim PAGEDATA_URL, PAGEDATA_TITLE, PAGEDATA_DESC, PAGEDATA_IMG
PAGEDATA_URL = 0
PAGEDATA_TITLE = 1
PAGEDATA_DESC = 2
PAGEDATA_IMG = 3

Dim METAFIELD_TYPE, METAFIELD_NAME, METAFIELD_SHOW, METAFIELD_FORM
Dim METAFIELD_METHOD, METAFIELD_DROPDOWN
METAFIELD_TYPE = 0
METAFIELD_NAME = 1
METAFIELD_SHOW = 2
METAFIELD_FORM = 3
METAFIELD_METHOD = 4
METAFIELD_DROPDOWN = 5

Dim METAFIELD_TYPE_NUMERIC, METAFIELD_TYPE_TEXT, METAFIELD_TYPE_DROPDOWN, METAFIELD_TYPE_MULTI
Dim METAFIELD_TYPE_MONEY
METAFIELD_TYPE_NUMERIC = 0
METAFIELD_TYPE_TEXT = 1
METAFIELD_TYPE_DROPDOWN = 2
METAFIELD_TYPE_MULTI = 3
METAFIELD_TYPE_MONEY = 4

Dim METAFIELD_METHOD_EXACT, METAFIELD_METHOD_LESSTHAN, METAFIELD_METHOD_LESSTHANORE
Dim METAFIELD_METHOD_GREATERTHAN, METAFIELD_METHOD_GREATERTHANORE, METAFIELD_METHOD_SUBSTRING
METAFIELD_METHOD_EXACT = 0
METAFIELD_METHOD_LESSTHAN = 1
METAFIELD_METHOD_LESSTHANORE = 2
METAFIELD_METHOD_GREATERTHAN = 3
METAFIELD_METHOD_GREATERTHANORE = 4
METAFIELD_METHOD_SUBSTRING = 5

Dim METAFIELD_NOVALUE_MARKER, METAFIELD_NOVALUE_MULTI
METAFIELD_NOVALUE_MARKER = 4294967295
METAFIELD_NOVALUE_MULTI = 255

Dim DICT_WORD, DICT_PTR, DICT_VARCOUNT, DICT_VARIANTS
DICT_WORD = 0
DICT_PTR = 1
DICT_VARCOUNT = 2
DICT_VARIANTS = 3

' ----------------------------------------------------------------------------
' Parameter initialisation
' ----------------------------------------------------------------------------
if (NoCharset = 0) then
	Response.Charset = Charset
end if

' we use the method=GET and 'zoom_query' parameter now (for sub-result pages etc)
IsZoomQuery = 0
if Request.QueryString("zoom_query").Count <> 0 then
	query = Request.QueryString("zoom_query")
	IsZoomQuery = 1
end if

' number of results per page, defaults to 10 if not specified
if Request.QueryString("zoom_per_page").Count <> 0 AND IsNumeric(Request.QueryString("zoom_per_page")) then
	per_page = CInt(Request.QueryString("zoom_per_page"))
	if (per_page < 1) then
		per_page = 1
	end if
else
	per_page = 10
end if

' current result page number, defaults to the first page if not specified
NewSearch = 0
if Request.QueryString("zoom_page").Count <> 0 AND IsNumeric(Request.QueryString("zoom_page")) then
	zoompage = CInt(Request.QueryString("zoom_page"))
else
	zoompage = 1
	NewSearch = 1
end if

' AND operator.
' 1 if we are searching for ALL terms
' 0 if we are searching for ANY terms (default)
if Request.QueryString("zoom_and").Count <> 0 AND IsNumeric(Request.QueryString("zoom_and")) then
	andq = CInt(Request.QueryString("zoom_and"))
elseif (IsEmpty(DefaultToAnd) = false AND DefaultToAnd = 1) then
	andq = 1
else
	andq = 0
end if

' categories
num_zoom_cats = 0
Dim catit
if Request.QueryString("zoom_cat[]").Count <> 0 then
	Redim zoomcat(Request.QueryString("zoom_cat[]").Count)
	Dim zoom_cat_count
	zoom_cat_count = Request.QueryString("zoom_cat[]").Count
	for catit = 1 to zoom_cat_count
		zoomcat(num_zoom_cats) = CInt(Request.QueryString("zoom_cat[]")(catit))
		if (zoomcat(num_zoom_cats) > -1 AND zoomcat(num_zoom_cats) < NumCats) then
			' only keep the ones that are valid
			num_zoom_cats = num_zoom_cats + 1
		else
			zoomcat(num_zoom_cats) = -1
		end if
	next
elseif Request.QueryString("zoom_cat").Count <> 0 AND IsNumeric(Request.QueryString("zoom_cat")) then
	zoomcat = Array(Int(Request.QueryString("zoom_cat")))
	num_zoom_cats = 1
else
	zoomcat = Array(-1)
	num_zoom_cats = 1
end if

' for sorting options
' zero is default (relevance)
' 1 is sort by date (if date/time data is available)
if Request.QueryString("zoom_sort").Count <> 0 AND IsNumeric(Request.QueryString("zoom_sort")) then
	zoomsort = CInt(Request.QueryString("zoom_sort"))
else
	zoomsort = 0
end if

LinkBackJoinChar = "?"
if (IsEmpty(LinkBackURL)) then
	selfURL = Request.ServerVariables("URL")
else
	selfURL = LinkBackURL
end if

if (InStr(selfURL, "?")) then
	LinkBackJoinChar = "&amp;"
end if

zoomtarget = ""
if (UseLinkTarget = 1) then
	zoomtarget = " target=""" & LinkTarget & """ "
end if

' ------------------------------------------------------------------
' Template buffers
' ------------------------------------------------------------------
Dim OUTPUT_FORM_START, OUTPUT_FORM_END, OUTPUT_FORM_SEARCHBOX
Dim OUTPUT_FORM_SEARCHBUTTON, OUTPUT_FORM_RESULTSPERPAGE, OUTPUT_FORM_MATCH
Dim OUTPUT_FORM_CATEGORIES, OUTPUT_FORM_CUSTOMMETA
Dim OUTPUT_HEADING, OUTPUT_SUMMARY, OUTPUT_SUGGESTION, OUTPUT_PAGESCOUNT
Dim OUTPUT_SORTING, OUTPUT_SEARCHTIME, OUTPUT_RECOMMENDED, OUTPUT_PAGENUMBERS
Dim OUTPUT_TAG_COUNT, OUTPUT_CATSUMMARY

OUTPUT_FORM_START = 0
OUTPUT_FORM_END = 1
OUTPUT_FORM_SEARCHBOX = 2
OUTPUT_FORM_SEARCHBUTTON = 3
OUTPUT_FORM_RESULTSPERPAGE = 4
OUTPUT_FORM_MATCH = 5
OUTPUT_FORM_CATEGORIES = 6
OUTPUT_FORM_CUSTOMMETA = 7

OUTPUT_HEADING = 8
OUTPUT_SUMMARY = 9
OUTPUT_SUGGESTION = 10
OUTPUT_PAGESCOUNT = 11
OUTPUT_SORTING = 12
OUTPUT_SEARCHTIME = 13
OUTPUT_RECOMMENDED = 14
OUTPUT_PAGENUMBERS = 15
OUTPUT_CATSUMMARY = 16
OUTPUT_TAG_COUNT = 17

Dim tagnum, tagPos
Dim OutBuf()
Redim OutBuf(OUTPUT_TAG_COUNT)
For	tagnum = 0 to OUTPUT_TAG_COUNT-1
	OutBuf(tagnum) = ""
Next
Dim OutResBuf
OutResBuf = ""

Dim TemplateShowTags
TemplateShowTags = Array("<!--ZOOM_SHOW_FORMSTART-->", "<!--ZOOM_SHOW_FORMEND-->", "<!--ZOOM_SHOW_SEARCHBOX-->", "<!--ZOOM_SHOW_SEARCHBUTTON-->","<!--ZOOM_SHOW_RESULTSPERPAGE-->","<!--ZOOM_SHOW_MATCHOPTIONS-->","<!--ZOOM_SHOW_CATEGORIES-->","<!--ZOOM_SHOW_CUSTOMMETAOPTIONS-->","<!--ZOOM_SHOW_HEADING-->","<!--ZOOM_SHOW_SUMMARY-->","<!--ZOOM_SHOW_SUGGESTION-->","<!--ZOOM_SHOW_PAGESCOUNT-->","<!--ZOOM_SHOW_SORTING-->","<!--ZOOM_SHOW_SEARCHTIME-->","<!--ZOOM_SHOW_RECOMMENDED-->","<!--ZOOM_SHOW_PAGENUMBERS-->","<!--ZOOM_SHOW_CATSUMMARY-->")

Dim TemplateDefaultTag, TemplateSearchFormTag
Dim TemplateResultsTag, TemplateQueryTag

TemplateDefaultTag = "<!--ZOOMSEARCH-->"
TemplateSearchFormTag = "<!--ZOOM_SHOW_SEARCHFORM-->"
TemplateResultsTag = "<!--ZOOM_SHOW_RESULTS-->"
TemplateQueryTag = "<!--ZOOM_SHOW_QUERY-->"

OutBuf(OUTPUT_FORM_START) = "<form method=""get"" action=""" & selfURL & """ class=""zoom_searchform"">"
OutBuf(OUTPUT_FORM_END) = "</form>"

Sub ShowDefaultForm()
	Response.Write(OutBuf(OUTPUT_FORM_START))
	Response.Write(OutBuf(OUTPUT_FORM_SEARCHBOX))
	Response.Write(OutBuf(OUTPUT_FORM_SEARCHBUTTON))
	Response.Write(OutBuf(OUTPUT_FORM_RESULTSPERPAGE))
	Response.Write(OutBuf(OUTPUT_FORM_MATCH))
	Response.Write(OutBuf(OUTPUT_FORM_CATEGORIES))
	Response.Write(OutBuf(OUTPUT_FORM_CUSTOMMETA))
	Response.Write(OutBuf(OUTPUT_FORM_END))
End Sub


Sub ShowTemplate
	'Open and print start of result page template
	Dim fp_template, Template
	Dim TemplateFilename

	' DO NOT MODIFY THE TEMPLATE FILENAME BELOW:
	TemplateFilename = "search_template.html"
	' Note that there is no practical need to change the TemplateFilename. This file
	' is not visible to the end user. The search link on your website should point to
	' "search.asp", and not the template file.
	'
	' Note also that you cannot change the filename to a PHP or ASP file.
	' The template file will only be treated as a static HTML page and changing the
	' extension will not alter this behaviour. Please see this FAQ support page
	' for a solution: http://www.wrensoft.com/zoom/support/faq_ssi.html

	set fp_template = zoomfso.OpenTextFile(MapPath(TemplateFilename), 1)
	' find the "<!--ZOOMSEARCH-->" string in the template html file
	dim templatePtr, tagPtr, tagLen
	tagPtr = ""
	do while fp_template.AtEndOfStream <> True

		if (templatePtr = "") then
			templatePtr = fp_template.ReadLine & VbCrLf
			tagPtr = templatePtr
		end if

		tagPos = InStr(templatePtr, "<!--ZOOM")
		if (tagPos = 0) then
			tagPtr = ""
		else
			Response.Write(Mid(templatePtr, 1, tagPos-1))
			tagPtr = Mid(templatePtr, tagPos)
		end if

		if (tagPtr = "") then
			Response.Write(templatePtr)
			templatePtr = ""
		elseif (InStr(tagPtr, TemplateDefaultTag) <> 0) then
			ShowDefaultForm()
			Response.Write(OutBuf(OUTPUT_HEADING))
			Response.Write(OutBuf(OUTPUT_SUMMARY))
			Response.Write(OutBuf(OUTPUT_CATSUMMARY))
			Response.Write(OutBuf(OUTPUT_SUGGESTION))
			Response.Write(OutBuf(OUTPUT_PAGESCOUNT))
			Response.Write(OutBuf(OUTPUT_RECOMMENDED))
			Response.Write(OutBuf(OUTPUT_SORTING))
			Response.Write(OutResBuf)
			Response.Write(OutBuf(OUTPUT_PAGENUMBERS))
			Response.Write(OutBuf(OUTPUT_SEARCHTIME))
			templatePtr = Mid(tagPtr, Len(TemplateDefaultTag)+1)
		elseif (InStr(tagPtr, TemplateSearchFormTag) <> 0) then
			ShowDefaultForm()
			templatePtr = Mid(tagPtr, Len(TemplateSearchFormTag)+1)
		elseif (InStr(tagPtr, TemplateResultsTag) <> 0) then
			Response.Write(OutResBuf)
			templatePtr = Mid(tagPtr, Len(TemplateResultsTag)+1)
		elseif (InStr(tagPtr, TemplateQueryTag) <> 0) then
			if (Len(queryForHTML) > 0) then
				Response.Write(queryForHTML)
			end if
			templatePtr = Mid(tagPtr, Len(TemplateQueryTag)+1)			
		else
			For	tagnum = 0 to OUTPUT_TAG_COUNT-1
				if (InStr(tagPtr, TemplateShowTags(tagnum)) <> 0) then
					Response.Write(OutBuf(tagnum))
					templatePtr = Mid(tagPtr, Len(TemplateShowTags(tagnum))+1)
					Exit for
				end if
			Next
			if (tagnum = OUTPUT_TAG_COUNT) then
				Response.Write(tagPtr)
				templatePtr = ""
			end if
		end if
	loop
	fp_template.Close
	'Template = split(templateFile, "<!--ZOOMSEARCH-->")
	'Response.Write(Template(0)) & VbCrLf
End Sub


' Translate a wildcard pattern to a regexp pattern
' Supports '*' and '?' only at the moment.
Function pattern2regexp(orig_pattern)
	' ASP/VBScript's RegExp has some 7-bit ASCII ch issues
	' and treats accented characters as an end of word for boundaries ("\b")
	' So we use ^ and $ instead, since we're matching single words anyway

	' make a copy of the original pattern first (otherwise the changes are applied to the source)
	Dim pattern
	pattern = orig_pattern
	' we have to do this first before we introduce any other regexp patterns
	pattern = Replace(pattern, "\", "\\")

	if (InStr(pattern, "#") <> False) then
		pattern = Replace(pattern, "#", "\#")
	end if

	if (InStr(pattern, "$") <> False) then
		pattern = Replace(pattern, "$", "\$")
	end if

	pattern = Replace(pattern, ".", "\.")
	pattern = Replace(pattern, "*", "[\d\S]*")
	pattern = Replace(pattern, "?", ".")
	pattern2regexp = pattern
End Function

Dim HIGHLIGHT_NONE, HIGHLIGHT_SINGLE, HIGHLIGHT_START, HIGHLIGHT_END
HIGHLIGHT_NONE = 0
HIGHLIGHT_SINGLE = 1
HIGHLIGHT_START = 2
HIGHLIGHT_END = 3

Function HighlightContextArray(context_word_count)
	Dim word_id, variant_index
	Dim termNum, pterm, res
	Dim phraseStop, i
	for i = 0 to context_word_count
		if (contextArray(0, i) > 0) then
			word_id = contextArray(0, i)
			variant_index = contextArray(1, i)
			for sw = 0 to NumSearchWords-1
				if (AllowExactPhrase = 1 AND InStr(SearchWords(sw), " ") <> 0) then
					termNum = i
					pterm = 0
					phraseStop = False
					do while (phraseStop = False AND phrase_terms_ids(sw)(pterm) <> 0 AND termNum < context_word_count)
						if (termNum = i OR contextArray(0, termNum) > DictReservedLimit) then
							if (phrase_terms_ids(sw)(pterm) <> contextArray(0, termNum)) then
								phraseStop = True
							else
								pterm = pterm + 1
							end if
						end if
						if (phraseStop = False) then
							termNum = termNum + 1
						end if
					loop

					if (pterm > 0 AND phrase_terms_ids(sw)(pterm) = 0) then
						highlightArray(i) = HIGHLIGHT_START
						highlightArray(termNum-1) = HIGHLIGHT_END
					end if
				else
					res = False
					if (UseWildCards(sw) = 1) then
					regExp.Pattern = "^(" & RegExpSearchWords(sw) & ")$"
					res = regExp.Test(GetDictionaryWord(word_id, variant_index))
					else
						if (search_terms_ids(sw) = word_id) then
							res = True
						end if
					end if

					if (res) then
						if (highlightArray(i) = HIGHLIGHT_NONE) then
							highlightArray(i) = HIGHLIGHT_SINGLE
						end if
					end if

				end if
			next
		end if
	next
End Function

'Returns true if a value is found within the array
Function IsInArray(strValue, arrayName)
	Dim iLoop, bolFound
	IsInArray = False
	if (IsArray(arrayName) = False) then
		Exit Function
	End if
	For iLoop = 0 to UBound(arrayName)
		if (CStr(arrayName(iLoop)) = CStr(strvalue)) then
			IsInArray = True
			Exit Function
		end if
	Next
End Function

Sub SkipSearchWord(sw)
	if (SearchWords(sw) <> "") then
		if (SkippedWords > 0) then
			SkippedOutputStr = SkippedOutputStr & ", "
		end if
		SkippedOutputStr = SkippedOutputStr & """<b>" & SearchWords(sw) & "</b>"""
		SearchWords(sw) = ""
	end if
	SkippedWords = SkippedWords + 1
End Sub

Function PrintHighlightDescription(line)
	if (Highlighting = 0) then
		PrintHighlightDescription = line
		Exit Function
	end if
	For zoomit = 0 to NumSearchWords-1
		if Len(RegExpSearchWords(zoomit)) > 0 then
			if (SearchAsSubstring = 1) then
				regExp.Pattern = "(" & RegExpSearchWords(zoomit) & ")"
				line = regExp.Replace(line, "[;:]$1[:;]")
			else
				regExp.Pattern = "(\W|^|\b)(" & RegExpSearchWords(zoomit) & ")(\W|$|\b)"
				line = regExp.Replace(line, "$1[;:]$2[:;]$3")
			end if
		end if
	Next

	line = replace(line, "[;:]", "<span class=""highlight"">")
	line = replace(line, "[:;]", "</span>")
	PrintHighlightDescription = line
End Function

Function PrintNumResults(num)
	if (num = 0) then
		PrintNumResults = STR_NO_RESULTS
	elseif (num = 1) then
		PrintNumResults = num & " " & STR_RESULT
	else
		if (IsMaxLimitExceeded = 1) then
			PrintNumResults = STR_MORETHAN & " " & num & " " & STR_RESULTS
		else
			PrintNumResults = num & " " & STR_RESULTS
		end if		
	end if
End Function

Function RecLinkAddParamToURL(url, paramStr)
	if (InStr(url, "?") <> 0) then
		RecLinkAddParamToURL = url & "&amp;" & paramStr
	else
		dim hashPos
		hashPos = InStr(url, "#")
		if (hashPos > 0) then
			RecLinkAddParamToURL = Mid(url, 1, hashPos-1) & "?" & paramStr & Mid(url, hashPos)
		else
			RecLinkAddParamToURL = url & "?" & paramStr
		end if
	end if
End Function

Function AddParamToURL(url, paramStr)
	if (InStr(url, "?") <> 0) then
		AddParamToURL = url & "&amp;" & paramStr
	else
		AddParamToURL = url & "?" & paramStr
	end if
End Function

Function SplitMulti(string, delimiters)
	For zoomit = 1 to UBound(delimiters)
		string = Replace(string, delimiters(zoomit), delimiters(0))
	Next
	string = Trim(string)   'for replaced quotes
	SplitMulti = Split(string, delimiters(0))
End Function

Sub ShellSort(array)
	Dim first, last, num, distance, index, index2
	Dim value, value0, value2, value3, value4, value5
	last = UBound(array, 2)
	first = 0	'LBound(array, 2)
	num = last - first + 1
	' find the best value for distance
	do
		distance = distance * 3 + 1
	loop until (distance > num)
	do
		distance = distance \ 3
		for index = (distance + first) to last
			value = array(1, index)
			value0 = array(0, index)
			value2 = array(2, index)
			value3 = array(3, index)
			value4 = array(4, index)
			value5 = array(5, index)
			index2 = index
			do while (index2 - distance => first)
				if (array(2, index2 - distance) > value2) then
					exit do
				end if
				if (array(2, index2 - distance) = value2) then
					if (array(1, index2 - distance) >= value) then
						exit do
					end if
				end if
				array(0, index2) = array(0, index2 - distance)
				array(1, index2) = array(1, index2 - distance)
				array(2, index2) = array(2, index2 - distance)
				array(3, index2) = array(3, index2 - distance)
				array(4, index2) = array(4, index2 - distance)
				array(5, index2) = array(5, index2 - distance)
				index2 = index2 - distance
			loop
			array(1, index2) = value
			array(0, index2) = value0
			array(2, index2) = value2
			array(3, index2) = value3
			array(4, index2) = value4
			array(5, index2) = value5
		next
	loop until distance = 1
End Sub

Sub ShellSortByDate(array, datetime)
	dim first, last, num, distance, index, index2
	dim value, value0, value2, value3, value4, value5
	last = UBound(array, 2)
	first = 0	'LBound(array, 2)
	num = last - first + 1
	' find the best value for distance
	do
		distance = distance * 3 + 1
	loop until (distance > num)
	do
		distance = distance \ 3
		for index = (distance + first) to last
			value = array(1, index)
			value0 = array(0, index)
			value2 = array(2, index)
			value3 = array(3, index)
			value4 = array(4, index)
			value5 = array(5, index)
			index2 = index
			do while (index2 - distance => first)
				'if (cdate(datetime(array(0, index2 - distance))) > cdate(datetime(value0))) then
				if (datetime(array(0, index2 - distance)) > datetime(value0)) then
					exit do
				end if
				if (datetime(array(0, index2 - distance)) = datetime(value0)) then
					if (array(2, index2 - distance) >= value2) then
						exit do
					end if
				end if
				array(0, index2) = array(0, index2 - distance)
				array(1, index2) = array(1, index2 - distance)
				array(2, index2) = array(2, index2 - distance)
				array(3, index2) = array(3, index2 - distance)
				array(4, index2) = array(4, index2 - distance)
				array(5, index2) = array(5, index2 - distance)
				index2 = index2 - distance
			loop
			array(1, index2) = value
			array(0, index2) = value0
			array(2, index2) = value2
			array(3, index2) = value3
			array(4, index2) = value4
			array(5, index2) = value5
		next
	loop until distance = 1
End Sub


Function GetBytes(binfile, bytes)
	bytes_buffer = binfile.Read(bytes)
	GetBytes = 0
	bytes_count = LenB(bytes_buffer)
	for k = 1 to bytes_count
		GetBytes = GetBytes +  Ascb(Midb(bytes_buffer, k, 1)) * (256^(k-1))
	next
End Function

Function GetNextDictWord(bin_pagetext)
	GetNextDictWord = GetBytes(bin_pagetext, DictIDLen-1)
End Function
Function GetNextVariant(bin_pagetext)
	GetNextVariant = GetBytes(bin_pagetext, 1)
End Function

Function GetDictionaryWord(word_id, variant_index)
	if (variant_index > 0 AND variant_index <= dict(DICT_VARCOUNT, word_id)) then
		GetDictionaryWord = dict(DICT_VARIANTS, word_id)(variant_index-1)
	else
		GetDictionaryWord = dict(DICT_WORD, word_id)
	end if
End Function

Function GetSpellingWord(word_id)
	if (dict(DICT_VARCOUNT, word_id) > 0) then
		GetSpellingWord = dict(DICT_VARIANTS, word_id)(0)
	else
		GetSpellingWord = dict(DICT_WORD, word_id)
	end if
End Function

Function GetDictID(word)
	Dim dictword
	GetDictID = -1

	if (ToLowerSearchWords = 1) then
		word = Lcase(word)
	end if

	for zoomit = 0 to dict_count

		dictword = dict(0, zoomit)
		if (ToLowerSearchWords = 1) then
			dictword = Lcase(dictword)
		end if

		if (dictword = word) then
			GetDictID = zoomit
			exit for
		end if
	next
End Function

' Custom read file method to avoid TextStream's ReadAll function
' which fails to scale reliably on certain machines/setups.
function ReadDatFile(zoomfso, filename)
	Dim fileObj, tsObj
	set fileObj = zoomfso.GetFile(MapPath(filename))
	set tsObj = fileObj.OpenAsTextStream(1, 0)
	ReadDatFile = tsObj.Read(fileObj.Size)
	tsObj.Close
end function

function GetSPCode(word)
	Dim metalen, tmpword, strPtr, wordlen
	metalen = 4

	' initialize return variable
	GetSPCode = ""

	tmpword = UCase(word)

	wordlen = Len(tmpword)
	if wordlen < 1 then
		Exit Function
	end if

	' if ae, gn, kn, pn, wr then drop the first letter
	strPtr = Left(tmpword, 2)
	if (strPtr = "AE" OR strPtr = "GN" OR strPtr = "KN" OR strPtr = "PN" OR strPtr = "WR") then
		tmpword = Right(tmpword, wordlen-1)
	end if

	' change x to s
	if (Left(tmpword, 1) = "X") then
		tmpword = "S" & Right(tmpword, wordlen-1)
	end if

	' get rid of the 'h' in "wh"
	if (Left(tmpword, 2) = "WH") then
		tmpword = "W" & Right(tmpword, wordlen-2)
	end if

	' update the word length
	wordlen = Len(tmpword)

	' remove an 's' from the end of the string
	if (Right(tmpword, 1) = "S") then
		tmpword = Left(tmpword, wordlen-1)
		wordlen = Len(tmpword)
	end if

	Dim i, ch, vowelBefore, Continue, silent
	Dim prevChar, nextChar, vowelAfter, frontvAfter, nextChar2, lastChr, nextChar3
	lastChr = wordlen

	i = 1
	do while (i <= wordlen AND Len(GetSPCode) < metalen)
		ch = Mid(tmpword, i, 1)
		vowelBefore = False
		Continue = False
		if (i > 1) then
			prevChar = Mid(tmpword, i-1, 1)
			if (prevChar = "A" OR prevChar = "E" OR prevChar = "I" OR prevChar = "O" OR prevChar = "U") then
				vowelBefore = True
			end if
		else
			prevChar = ""
			if (ch = "A" OR ch = "E" OR ch = "I" OR ch = "O" OR ch = "U") then
				GetSPCode = Left(tmpword, 1)
				Continue = True
			end if
		end if

		if (Continue = False) then
			vowelAfter = False
			frontvAfter = False
			nextChar = ""
			if (i < wordlen) then
				nextChar = Mid(tmpword, i+1, 1)
				if (nextChar = "A" OR nextChar = "E" OR nextChar = "I" OR nextChar = "O" OR nextChar = "U") then
					vowelAfter = True
				end if
				if (nextChar = "E" OR nextChar = "I" OR nextChar = "Y") then
					frontvAfter = True
				end if
			end if

			' skip double letters except ones in list
			if (ch = nextChar AND (nextChar <> ".")) then
				Continue = True
			end if

			if (Continue = False) then
				nextChar2 = ""
				if (i < (lastChr-1)) then
					nextChar2 = Mid(tmpword, i+2, 1)
				end if

				nextChar3 = ""
				if (i < (lastChr-2)) then
					nextChar3 = Mid(tmpword, i+3, 1)
				end if

				if (ch = "B") then
					silent = False
					if (i = wordlen AND prevChar = "M") then
						silent = True
					end if
					if (silent = False) then
						GetSPCode = GetSPCode & ch
					end if
				elseif (ch = "C") then
					if (NOT(i > 2 AND prevChar = "S" AND frontvAfter)) then
						if (i > 1 AND nextChar = "I" AND nextChar2 = "A") then
							GetSPCode = GetSPCode & "X"
						elseif (frontvAfter) then
							GetSPCode = GetSPCode & "S"
						elseif (i > 2 AND prevChar = "S" AND nextChar = "H") then
							GetSPCode = GetSPCode & "K"
						else
							if (nextChar = "H") then
								if (i = 1 AND (nextChar2 <> "A" AND nextChar2 <> "E" AND nextChar3 <> "I" AND nextChar3 <> "O" AND nextChar3 <> "U")) then
									GetSPCode = GetSPCode & "K"
								else
									GetSPCode = GetSPCode & "X"
								end if
							else
								if (prevChar = "C") then
									GetSPCode = GetSPCode & "C"
								else
									GetSPCode = GetSPCode & "K"
								end if
							end if
						end if
					end if
				elseif (ch = "D") then
					if (nextChar = "G" AND (nextChar2 = "E" OR nextChar2 = "I" OR nextChar3 = "Y")) then
						GetSPCode = GetSPCode & "J"
					else
						GetSPCode = GetSPCode & "T"
					end if
				elseif (ch = "G") then
					silent = False
					' silent -gh- except for -gh and no vowel after h
					if ((i < (wordlen-1) AND nextChar = "H") AND (nextChar2 <> "A" AND nextChar2 <> "E" AND nextChar2 <> "I" AND nextChar2 <> "O" AND nextChar2 <> "U")) then
						silent = True
					end if

					if (i = (wordlen-3) AND nextChar = "N" AND nextChar2 = "E" AND nextChar3 = "D") then
						silent = True
					else
						if ((i = (wordlen-1)) AND nextChar = "N") then
							silent = True
						end if
					end if

					if (prevChar = "D" AND frontvAfter) then
						silent = True
					end if

					if (prevChar = "G") then
						hard = True
					else
						hard = False
					end if

					if (silent = False) then
						if (frontvAfter AND (NOT hard)) then
							GetSPCode = GetSPCode & "J"
						else
							GetSPCode = GetSPCode & "K"
						end if
					end if
				elseif (ch = "H") then
					silent = False
					'variable sound - those modified by adding a "H"
					if (prevChar = "C" OR prevChar = "S" OR prevChar = "P" OR prevChar = "T" OR prevChar = "G") then
						silent = True
					end if
					if (vowelBefore AND NOT vowelAfter) then
						silent = True
					end if
					if (NOT silent) then
						GetSPCode = GetSPCode & ch
					end if
				elseif (ch = "F" OR ch = "J" OR ch = "L" OR ch = "M" OR ch = "N" OR ch = "R") then
					GetSPCode = GetSPCode & ch
				elseif (ch = "K") then
					if (prevChar <> "C") then
						GetSPCode = GetSPCode & ch
					end if
				elseif (ch = "P") then
					if (nextChar = "H") then
						GetSPCode = GetSPCode & "F"
					else
						GetSPCode = GetSPCode & "P"
					end if
				elseif (ch = "Q") then
					GetSPCode = GetSPCode & "K"
				elseif (ch = "S") then
					if (i > 2 AND nextChar = "I" AND (nextChar2 = "O" OR nextChar2 = "A")) then
						GetSPCode = GetSPCode & "X"
					elseif (nextChar = "H") then
						GetSPCode = GetSPCode & "X"
					else
						GetSPCode = GetSPCode & "S"
					end if
				elseif (ch = "T") then
					if (i > 2 AND nextChar = "I" AND (nextChar2 = "O" OR nextChar2 = "A")) then
						GetSPCode = GetSPCode & "X"
					elseif (nextChar = "H") then    'the=0, tho=T, withrow=0
						if (i > 1 OR (nextChar2 = "A" OR nextChar2 = "E" OR nextChar2 = "I" OR nextChar = "O" OR nextChar2 = "U")) then
							GetSPCode = GetSPCode & "0"
						else
							GetSPCode = GetSPCode & "T"
						end if
					elseif (NOT (i < (wordlen-2) AND nextChar = "C" AND nextChar2 = "H")) then
						GetSPCode = GetSPCode & "T"
					end if
				elseif (ch = "V") then
					GetSPCode = GetSPCode & "F"
				elseif (ch = "W" OR ch = "Y") then
					if (i < wordlen AND vowelAfter) then
						GetSPCode = GetSPCode & ch
					end if
				elseif (ch = "X") then
					GetSPCode = GetSPCode & "KS"
				elseif (ch = "Z") then
					GetSPCode = GetSPCode & "S"
				end if
			end if
		end if
		i = i + 1
	Loop
	if (Len(GetSPCode) = 0) then
		GetSPCode = ""
		Exit Function
	end if
end function

function Encode(str)
	Encode = str
	Encode = Replace(Encode, "&", "&#38;")
	Encode = Replace(Encode, "<", "&#60;")
	Encode = Replace(Encode, ">", "&#62;")
end function

function htmlspecialchars(str)
	htmlspecialchars = str
	htmlspecialchars = Replace(htmlspecialchars, "&", "&#38;")
	htmlspecialchars = Replace(htmlspecialchars, "<", "&#60;")
	htmlspecialchars = Replace(htmlspecialchars, ">", "&#62;")
	htmlspecialchars = Replace(htmlspecialchars, """", "&#34;")
	htmlspecialchars = Replace(htmlspecialchars, "'", "&#39;")
end function

function Ceil(byVal a)
	if (a - Int(a)) = 0 then
		Ceil = a
	else
		Ceil = Int(1 + a)
	end if
end function

function CheckBitInByteArray(bitnum, byteArray)
	Dim bytenum
	Dim newBitnum
		
	bytenum = Ceil((bitnum+1) / 8.0)
	
	if (bytenum > 1) then
		newBitnum = bitnum - ((bytenum-1)*8)
		bytenum = bytenum - 1
	else
		newBitnum = bitnum
		bytenum = 0
	end if
	
	if (bytenum >= NumCatBytes) then
		Response.Write("Error: Category number is invalid. Incorrect settings file used?")
		Response.End
	end if
			
	CheckBitInByteArray = CDbl(byteArray(bytenum)) AND CDbl(2)^CDbl(newBitnum)
end function

function RecLinkWordMatch(rec_word, rec_idx)
	RecLinkWordMatch = False
	sw = 0
	IsFound = 0
	do while (sw <= NumSearchWords AND IsFound = 0)
		if (sw = NumSearchWords) then
			bMatched = queryForSearch = rec_word
		else
			if (UseWildCards(sw) = 1) then
				patternStr = ""

				if (SearchAsSubstring = 0) then
					patternStr = patternStr & "^"
				end if

				' new keyword pattern to match for
				patternStr = patternStr & RegExpSearchWords(sw)

				if (SearchAsSubstring = 0) then
					patternStr = patternStr & "$"
				end if

				regExp.Pattern = patternStr
				bMatched = regExp.Test(rec_word)
			elseif (SearchAsSubstring = 0) then
				bMatched = SearchWords(sw) = rec_word
			else
				bMatched = InStr(rec_word, SearchWords(sw))
			end if

			if (bMatched = False) then
				if (InStr(rec_word, "*") <> 0 OR InStr(rec_word, "?") <> 0) then
					Dim RecWordRegExp
					RecWordRegExp = "^" & pattern2regexp(rec_word) & "$"
					regExp.Pattern = RecWordRegExp
					bMatched = regExp.Test(SearchWords(sw))
				end if
			end if

		end if
		if (bMatched) then
			RecLinkWordMatch = True
			if (num_recs_found = 0) then
				OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommended"">"
				OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommended_heading"">" & STR_RECOMMENDED & "</div>"
			end if
			pgdata = GetPageData(rec_idx)
			url = pgdata(PAGEDATA_URL)
			title = pgdata(PAGEDATA_TITLE)
			description = pgdata(PAGEDATA_DESC)
			if (UseZoomImage = 1) then
				zres_image = pgdata(PAGEDATA_IMG)
			end if
			urlLink = url
			if (GotoHighlight = 1) then
				if (SearchAsSubstring = 1) then
					urlLink = RecLinkAddParamToURL(urlLink, "zoom_highlightsub=" & queryForURL)
				else
					urlLink = RecLinkAddParamToURL(urlLink, "zoom_highlight=" & queryForURL)
				end if
			end if
			if (PdfHighlight = 1) then
				if (InStr(urlLink, ".pdf") <> False) then
					urlLink = urlLink & "#search=&quot;"&Replace(query, """", "")&"&quot;"
				end if
			end if
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommend_block"">"
			if (UseZoomImage = 1) then
				if (Len(zres_image) > 0) then
					OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommend_image"">"
					OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<a href=""" & urlLink & """"  & zoomtarget & "><img src="""&zres_image&""" alt="""" class=""recommend_image""></a>"
					OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "</div>"
				end if
			end if
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommend_title"">"
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<a href=""" & urlLink & """"  & zoomtarget & ">"
			if (Len(title) > 1) then
				OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & PrintHighlightDescription(title)
			else
				OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & PrintHighlightDescription(url)
			end if
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "</a></div>"
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommend_description"">"
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & PrintHighlightDescription(description)
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "</div>"
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "<div class=""recommend_infoline"">" & url & "</div>"
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "</div>"
			num_recs_found = num_recs_found + 1
			IsFound = 1
		end if
		sw = sw + 1
	loop

end function

' Debug stop watches to time performance of sub-sections
Dim StopWatch(10)
Dim TimerCount, DebugTimerSum
TimerCount = 0
DebugTimerSum = 0
sub StartTimer()
	StopWatch(TimerCount) = timer
	TimerCount = TimerCount + 1
end sub
function StopTimer()
	EndTime = Timer
	TimerCount = TimerCount - 1
	StopTimer = EndTime - StopWatch(TimerCount)
end function


' ----------------------------------------------------------------------------
' Main starts here
' ----------------------------------------------------------------------------

' For timing of the search
Dim StartTime, ElapsedTime, CheckTime
StartTime = Timer

' Read in the metafields query
Dim fieldnum, ddi, ddv
Dim tmpMetaQueryNameMulti, tmpMetaQueryName, tmpMetaArray
if (UseMetaFields = 1) then
	redim meta_query(NumMetaFields)
	for fieldnum = 0 to NumMetaFields-1
		if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI) then
			tmpMetaQueryNameMulti = metafields(fieldnum)(METAFIELD_NAME) & "[]"
			tmpMetaQueryName = metafields(fieldnum)(METAFIELD_NAME)
			if Request.QueryString(tmpMetaQueryNameMulti).Count <> 0 then
				Redim tmpMetaArray(Request.QueryString(tmpMetaQueryNameMulti).Count)
				Dim tmpMetaCount, mai, mqi
				tmpMetaCount = Request.QueryString(tmpMetaQueryNameMulti).Count
				mai = 0
				for mqi = 1 to tmpMetaCount
					if (IsNumeric(Request.QueryString(tmpMetaQueryNameMulti)(mqi))) then
						tmpMetaArray(mai) = Request.QueryString(tmpMetaQueryNameMulti)(mqi)
						mai = mai + 1
					end if
				next
			elseif Request.QueryString(tmpMetaQueryName).Count <> 0 AND IsNumeric(Request.QueryString(tmpMetaQueryName)) then
				Redim tmpMetaArray(1)
				tmpMetaArray = Array(Int(Request.QueryString(tmpMetaQueryName)))
			else
				Redim tmpMetaArray(1)
				tmpMetaArray = Array(-1)
			end if
			meta_query(fieldnum) = tmpMetaArray
		elseif (Request.QueryString(metafields(fieldnum)(METAFIELD_NAME)).Count <> 0) then
			meta_query(fieldnum) = Request.QueryString(metafields(fieldnum)(METAFIELD_NAME))
			if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_NUMERIC AND IsNumeric(meta_query(fieldnum))) then
				meta_query(fieldnum) = Int(meta_query(fieldnum))
			end if
		else
			meta_query(fieldnum) = ""
		end if
	next
end if

OutResBuf = OutResBuf & "<!--Zoom Search Engine " & Version & "-->" & VbCrLf

Dim ppo

' Replace the key text <!--ZOOMSEARCH--> with the following
if (FormFormat > 0) then
	' Insert the form
	OutBuf(OUTPUT_FORM_SEARCHBOX) = OutBuf(OUTPUT_FORM_SEARCHBOX) & "<input type=""text"" name=""zoom_query"" size=""50"" value=""" & htmlspecialchars(query) & """ id=""zoom_searchbox"" class=""zoom_searchbox"" autocorrect=""off"" autocapitalize=""off"" />" & VbCrlf
	OutBuf(OUTPUT_FORM_SEARCHBUTTON) = OutBuf(OUTPUT_FORM_SEARCHBUTTON) & "&nbsp;&nbsp;<input type=""submit"" value=""" & STR_FORM_SUBMIT_BUTTON & """ class=""zoom_button"" /><br />" & VbCrlf
	if (FormFormat = 2) then
		OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & "<span class=""zoom_results_per_page"">" & STR_FORM_RESULTS_PER_PAGE & VbCrlf
		OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & "<select name=""zoom_per_page"">" & VbCrlf
		For Each ppo In PerPageOptions
			OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & "<option"
			if (Int(ppo) = Int(per_page)) then
				OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & " selected=""selected"""
			end if
			OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & ">" & ppo & "</option>" & VbCrLf
		next
		OutBuf(OUTPUT_FORM_RESULTSPERPAGE) = OutBuf(OUTPUT_FORM_RESULTSPERPAGE) & "</select></span>" & VbCrlf

		if (UseCats = 1) then
			OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<span class=""zoom_categories"">" & VbCrlf
			OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & STR_FORM_CATEGORY & " " & VbCrlf
			if (SearchMultiCats = 1) then
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<ul>" & VbCrlf
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<li><input type=""checkbox"" name=""zoom_cat[]"" value=""-1"""
				if (zoomcat(0) = -1) then
					OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & " checked=""checked"""
				end if
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & ">" & STR_FORM_CATEGORY_ALL & "</input></li>"
				for zoomit = 0 to NumCats-1
					OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<li><input type=""checkbox"" name=""zoom_cat[]"" value=""" & zoomit & """"
					if (zoomcat(0) <> -1) then
						for catit = 0 to num_zoom_cats-1
							if (zoomit = zoomcat(catit)) then
								OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & " checked=""checked"""
								exit for
							end if
						next
					end if
					OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & ">" & catnames(zoomit) & "</input></li>" & VbCrlf
				next
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "</ul><br />" & VbCrlf
			else
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<select name=""zoom_cat[]"">" & VbCrlf
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<option value=""-1"">" & STR_FORM_CATEGORY_ALL & "</option>"
				for zoomit = 0 to NumCats-1
					OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "<option value=""" & zoomit & """"
					if (zoomit = zoomcat(0)) then
						OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & " selected=""selected"""
					end if
					OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & ">" & catnames(zoomit) & "</option>"
				Next
				OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "</select>&nbsp;&nbsp;" & VbCrlf
			end if
			OutBuf(OUTPUT_FORM_CATEGORIES) = OutBuf(OUTPUT_FORM_CATEGORIES) & "</span>" & VbCrlf
		end if
		if (UseMetaFields = 1) then
			OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "<span class=""zoom_metaform"">" & VbCrLf
			for fieldnum = 0 to NumMetaFields-1
				if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_NUMERIC) then
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & metafields(fieldnum)(METAFIELD_FORM) & ": <input type=""text"" name=""" & metafields(fieldnum)(METAFIELD_NAME) & """ size=""20"" value=""" & meta_query(fieldnum) & """ class=""zoom_metaform_numeric"" />" & VbCrLf
				elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_DROPDOWN) then
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & metafields(fieldnum)(METAFIELD_FORM) & " <select name=""" & metafields(fieldnum)(METAFIELD_NAME) & """ class=""zoom_metaform_dropdown"">" & VbCrLf
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "<option value=""-1"">" & STR_FORM_CATEGORY_ALL & "</option>"
					ddi = 0
					For Each ddv in metafields(fieldnum)(METAFIELD_DROPDOWN)
						OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "<option value=""" & ddi & """"
						if (IsNumeric(meta_query(fieldnum))) then
							if (ddi = Int(meta_query(fieldnum))) then
								OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & " selected=""selected"""
							end if
						end if
						OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & ">" & ddv & "</option>" & VbCrLf
						ddi = ddi + 1
					Next
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "</select>" & VbCrLf
				elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI) then
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & metafields(fieldnum)(METAFIELD_FORM) & " <select multiple name=""" & metafields(fieldnum)(METAFIELD_NAME) & "[]"" class=""zoom_metaform_dropdown"">" & VbCrLf
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "<option value=""-1"">" & STR_FORM_CATEGORY_ALL & "</option>"
					ddi = 0
					For Each ddv in metafields(fieldnum)(METAFIELD_DROPDOWN)
						OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "<option value=""" & ddi & """"
						for mqi = 0 to UBound(meta_query(fieldnum))-1
							if (ddi = Int(meta_query(fieldnum)(mqi))) then
								OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & " selected=""selected"""
							end if
						next
						OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & ">" & ddv & "</option>" & VbCrLf
						ddi = ddi + 1
					Next
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "</select>" & VbCrLf
				elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MONEY) then
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & metafields(fieldnum)(METAFIELD_FORM) & ": " & MetaMoneyCurrency & "<input type=""text"" name=""" & metafields(fieldnum)(METAFIELD_NAME) & """ size=""7"" value=""" & meta_query(fieldnum) & """ class=""zoom_metaform_money"" />" & VbCrLf
				else
					OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & metafields(fieldnum)(METAFIELD_FORM) & ": <input type=""text"" name=""" & metafields(fieldnum)(METAFIELD_NAME) & """ size=""20"" value=""" & meta_query(fieldnum) & """ class=""zoom_metaform_text"" />" & VbCrLf
				end if
			next
			OutBuf(OUTPUT_FORM_CUSTOMMETA) = OutBuf(OUTPUT_FORM_CUSTOMMETA) & "</span>" & VbCrLf
		end if
		OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<span class=""zoom_match"">" & STR_FORM_MATCH & VbCrlf
		if (andq = 0) then
			OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<input type=""radio"" name=""zoom_and"" value=""0"" checked=""checked"" />" & STR_FORM_ANY_SEARCH_WORDS & VbCrlf
			OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<input type=""radio"" name=""zoom_and"" value=""1"" />" & STR_FORM_ALL_SEARCH_WORDS & VbCrlf
		else
			OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<input type=""radio"" name=""zoom_and"" value=""0"" />" & STR_FORM_ANY_SEARCH_WORDS & VbCrlf
			OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<input type=""radio"" name=""zoom_and"" value=""1"" checked=""checked"" />" & STR_FORM_ALL_SEARCH_WORDS & VbCrlf
		end if
		OutBuf(OUTPUT_FORM_START) = OutBuf(OUTPUT_FORM_START) & "<input type=""hidden"" name=""zoom_sort"" value=""" & zoomsort & """ />" & VbCrLf
		OutBuf(OUTPUT_FORM_MATCH) = OutBuf(OUTPUT_FORM_MATCH) & "<br /></span>" & VbCrlf
	else
		OutBuf(OUTPUT_FORM_START) = OutBuf(OUTPUT_FORM_START) & "<input type=""hidden"" name=""zoom_per_page"" value=""" & per_page & """ />" & VbCrLf
		OutBuf(OUTPUT_FORM_START) = OutBuf(OUTPUT_FORM_START) & "<input type=""hidden"" name=""zoom_and"" value=""" & andq & """ />" & VbCrLf
		OutBuf(OUTPUT_FORM_START) = OutBuf(OUTPUT_FORM_START) & "<input type=""hidden"" name=""zoom_sort"" value=""" & zoomsort & """ />" & VbCrLf
	end if

end if

' Give up early if no search words provided
Dim NoSearch
NoSearch = 0
Dim IsEmptyMetaQuery
IsEmptyMetaQuery = False
if (Len(query) = 0) then
	if (UseMetaFields = 1) then
		if (IsZoomQuery = 1) then
			IsEmptyMetaQuery = True
		else
			NoSearch = 1
		end if
	else
		if (IsZoomQuery = 1) then
			OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<div class=""summary"">" & STR_NO_QUERY & "</div>"			
		end if
		'stop here, but finish off the html
		'call PrintEndOfTemplate
		'Response.End no longer used to allow for search.asp to follow through the original file
		'when it is used in in an #include
		NoSearch = 1
	end if
end if

if (NoSearch = 0) then

	' Load index data files (*.zdat) ----------------------------------------------
	Dim datefile, dates_count
	Dim dictfile, dict_count, dictline

	' load in recommended
	if (Recommended = 1) then
		recfile = split(ReadDatFile(zoomfso, "zoom_recommended.zdat"), chr(10))
		rec_count = UBound(recfile)
		dim rec()
		redim rec(2, rec_count)
		for zoomit = 0 to rec_count-1
			sep = InstrRev(recfile(zoomit), " ")
			if (sep > 0) then
				rec(0, zoomit) = Left(recfile(zoomit), sep)
				rec(1, zoomit) = Mid(recfile(zoomit), sep)
			end if
		next
		' re-value dict_count in case of errors in dict file
		rec_count = UBound(rec, 2)
	end if

	'Load the pageinfo file
	Dim bfp_pageinfo
	set bfp_pageinfo = CreateObject("ADODB.Stream")
	bfp_pageinfo.Type = 1    'Specify stream type - we want To get binary data.
	bfp_pageinfo.Open        'Open the stream
	bfp_pageinfo.LoadFromFile MapPath("zoom_pageinfo.zdat")

	pageinfo_count = NumPages
	dim recsize
	dim pgdataoffset()
	dim datetime()
	dim boost()
	dim filesize()
	dim linkaction()
	dim metavalues()
	dim metaTmpArray()
	dim valuesize, valueStr
	dim tmpCatValue()
	dim tmpMultiValues()
	dim bi
	redim pgdataoffset(pageinfo_count)
	redim datetime(pageinfo_count)
	redim filesize(pageinfo_count)
	redim boost(pageinfo_count)
	redim linkaction(pageinfo_count)
	redim catpages(pageinfo_count)
	if (UseMetaFields = 1) then
		redim metavalues(pageinfo_count)
	end if

	for zoomit = 0 to pageinfo_count-1

		if (bfp_pageinfo.EOS = True) then
			exit for
		end if

		recsize = GetBytes(bfp_pageinfo, 2)
		pgdataoffset(zoomit) = GetBytes(bfp_pageinfo, 5)
		filesize(zoomit) = GetBytes(bfp_pageinfo, 4)
		datetime(zoomit) = GetBytes(bfp_pageinfo, 4)
		boost(zoomit) = GetBytes(bfp_pageinfo, 1)
		linkaction(zoomit) = GetBytes(bfp_pageinfo, 1)
		
		if (UseCats = 1 AND NumCatBytes > 0) then
			redim catTmpValue(NumCatBytes)
			for bi = 0 to NumCatBytes-1
				catTmpValue(bi) = GetBytes(bfp_pageinfo, 1)				
			next
			catpages(zoomit) = catTmpValue
		end if

		if (UseMetaFields = 1) then
			' tmparray is necessary due to inability to redim 2d array in vbscript
			redim metaTmpArray(NumMetaFields)
			for fieldnum = 0 to NumMetaFields-1
				if metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_TEXT then
					valuesize = GetBytes(bfp_pageinfo, 1)
					if (valuesize > 0 AND valuesize <> METAFIELD_NOVALUE_MARKER) then
						valueStr = bfp_pageinfo.Read(valuesize)
						metaTmpArray(fieldnum) = ConvertBinaryToString(valueStr)
					else
						metaTmpArray(fieldnum) = ""
					end if
				elseif metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_DROPDOWN then
					metaTmpArray(fieldnum) = GetBytes(bfp_pageinfo, 1)
				elseif metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI then
					valuesize = GetBytes(bfp_pageinfo, 1)
					if (valuesize > 0 AND valuesize <> METAFIELD_NOVALUE_MULTI) then
						redim tmpMultiValues(valuesize+1)
						Dim mvi
						tmpMultiValues(0) = valuesize
						for mvi = 1 to valuesize
							tmpMultiValues(mvi) = GetBytes(bfp_pageinfo, 1)
						next
						metaTmpArray(fieldnum) = tmpMultiValues
					else
						redim tmpMultiValues(1)
						tmpMultiValues(0) = 0
						metaTmpArray(fieldnum) = tmpMultiValues
					end if
				else
					metaTmpArray(fieldnum) = GetBytes(bfp_pageinfo, 4)
				end if
				'Response.Write("text read: " & CStr(metaTmpArray(fieldnum)) & "<br>")
				'tmpArray(fieldnum) = pageinfoline(PAGEINFO_METAFIRST+fieldnum)
			next
			metavalues(zoomit) = metaTmpArray
		end if
	next
	
	' open the pagedata file
	set fp_pagedata = CreateObject("ADODB.Stream")
	fp_pagedata.Type = 1   ' stream type = binary
	fp_pagedata.Open       ' open stream
	fp_pagedata.LoadFromFile MapPath("zoom_pagedata.zdat")  'load file to stream

	' load in pagetext file
	if (DisplayContext = 1 OR AllowExactPhrase = 1) then
		Dim bin_pagetext, tmpstr
		set bin_pagetext = CreateObject("ADODB.Stream")
		bin_pagetext.Type = 1   ' stream type = binary
		bin_pagetext.Open       ' open stream
		bin_pagetext.LoadFromFile MapPath("zoom_pagetext.zdat")  'load file to stream

		'check for blank message
		tmpstr = CStr(bin_pagetext.Read(8))
		if (tmpstr = "This") then
			Response.Write("<b>Zoom config error:</b> The zoom_pagetext.zdat file is not properly created for the search settings specified.<br />Please check that you have re-indexed your site with the search settings selected in the configuration window.<br />")
			Response.End
		end if
	end if

	' load in dictionary file
	dictfile = split(ReadDatFile(zoomfso, "zoom_dictionary.zdat"), chr(10))
	dict_count = UBound(dictfile)
	dim dict()
	redim dict(4, dict_count)
	dim variantsArray()
	dim vi, varline
	dictid = 0
	for zoomit = 0 to dict_count
		dictline = Split(dictfile(zoomit), " ")
		if (UBound(dictline) > 0) then
			dict(DICT_WORD, dictid) = dictline(0)
			if (Len(dictline(DICT_PTR)) > 0) then
				dict(DICT_PTR, dictid) = Int(dictline(DICT_PTR))
			else
				dict(DICT_PTR, dictid) = -1
			end if
			if (UBound(dictline) = 2) then
				dict(DICT_VARCOUNT, dictid) = Int(dictline(2))
				if (dict(DICT_VARCOUNT, dictid) > 0) then
					redim variantsArray(dict(DICT_VARCOUNT, dictid))
					for vi = 0 to dict(DICT_VARCOUNT, dictid)-1
						zoomit = zoomit + 1
						varline = dictfile(zoomit)
						if (Len(varline) > 0) then
							variantsArray(vi) = varline
						end if
					next
					dict(DICT_VARIANTS, dictid) = variantsArray
				end if
			end if
			dictid = dictid + 1
		end if
	next
	' re-value dict_count in case of errors in dict file
	dict_count = UBound(dict, 2)

	' load in wordmap file
	Dim bfp_wordmap
	set bfp_wordmap = CreateObject("ADODB.Stream")
	bfp_wordmap.Type = 1    'Specify stream type - we want To get binary data.
	bfp_wordmap.Open        'Open the stream
	bfp_wordmap.LoadFromFile MapPath("zoom_wordmap.zdat")

	'Initialise regular expression object
	Dim regExp
	set regExp = New RegExp
	regExp.Global = True
	if (ToLowerSearchWords = 0) then
		regExp.IgnoreCase = False
	else
		regExp.IgnoreCase = True
	end if

	' Prepare query for search -----------------------------------------------------

	'Split search phrase into words

	if (MapAccents = 1) then
		For zoomit = 0 to UBound(NormalChars)
			query = Replace(query, AccentChars(zoomit), NormalChars(zoomit))
		Next
	end if

	if (AllowExactPhrase = 0) then
		query = Replace(query, """", " ")
	end if
	if (InStr(WordJoinChars, ".") = False) then
		query = Replace(query, ".", " ")
	end if
	if (InStr(WordJoinChars, "-") = False) then
		regExp.Pattern = "(\S)-"
		query = regExp.Replace(query, "$1 ")
	end if
	if (InStr(WordJoinChars, "#") = False) then
		regExp.Pattern = "#(\S)"
		query = regExp.Replace(query, " $1")
	end if
	if (InStr(WordJoinChars, "+") = False) then
		regExp.Pattern = "[\+]+([^\+\s])"
		query = regExp.Replace(query, " $1")
		regExp.Pattern = "([^\+\s])\+\s"
		query = regExp.Replace(query, "$1 ")
	end if

	if (InStr(WordJoinChars, "_") = False) then
		query = Replace(query, "_", " ")
	end if
	if (InStr(WordJoinChars, "'") = False) then
		query = Replace(query, "'", " ")
	end if
	if (InStr(WordJoinChars, "$") = False) then
		query = Replace(query, "$", " ")
	end if
	if (InStr(WordJoinChars, ",") = False) then
		query = Replace(query, ",", " ")
	end if
	if (InStr(WordJoinChars, ":") = False) then
		query = Replace(query, ":", " ")
	end if
	if (InStr(WordJoinChars, "&") = False) then
		query = Replace(query, "&", " ")
	end if
	if (InStr(WordJoinChars, "/") = False) then
		query = Replace(query, "/", " ")
	end if
	if (InStr(WordJoinChars, "\") = False) then
		query = Replace(query, "\", " ")
	end if

	' Strip slashes, sloshes, parenthesis and other regexp elements
	' also strip any of the wordjoinchars if followed immediately by a space
	regExp.Pattern = "[\s\(\)\^\[\]\|\{\}\%\£\!]+|[\.\-\_\'\,\:\&\/\\](\s|$)"
	query = regExp.Replace(query, " ")

	' update the encoded/output query with our changes
	queryForHTML = htmlspecialchars(query)
	if (ToLowerSearchWords = 1) then
		queryForSearch = Lcase(query)
	else
		queryForSearch = query
	end if

	' Split exact phrase terms if found
	dim SearchWords, quote_terms, term, exclude_terms, tmp_query
	quote_terms = Array()
	exclude_terms = Array()
	tmp_query = queryForSearch
	if (InStr(queryForSearch, """")) then
		regExp.Pattern = """.*?""|-"".*?"""
		set quote_terms = regExp.Execute(queryForSearch)
		tmp_query = regExp.Replace(tmp_query, "")
	end if
	if (InStr(queryForSearch, "-")) then
		regExp.Pattern = "(\s|^)-.*?(?=\s|$)"
		set exclude_terms = regExp.Execute(tmp_query)
		tmp_query = regExp.Replace(tmp_query, "")
	end if
	tmp_query = Trim(tmp_query)
	regExp.Pattern = "[\s]+"
	tmp_query = regExp.Replace(tmp_query, " ")
	SearchWords = Split(tmp_query, " ")
	'SearchWords = SplitMulti(tmp_query, Array(" ", "_", "[", "]", "+", ","))

	zoomit = UBound(SearchWords)
	for each term in quote_terms
		zoomit = zoomit + 1
		redim preserve SearchWords(zoomit)
		SearchWords(zoomit) = Replace(term, """", "")
	next

	' add exclusion search terms (make sure we put them last)
	zoomit = UBound(SearchWords)
	for each term in exclude_terms
		zoomit = zoomit + 1
		redim preserve SearchWords(zoomit)
		SearchWords(zoomit) = Trim(term)
	next

	query_zoom_cats = ""

	'Print heading
	OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & "<div class=""searchheading"">" & STR_RESULTS_FOR & " <i>" & queryForHTML
	if (UseCats = 1) then
		if (zoomcat(0) = -1) then
			OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & " " & STR_RESULTS_IN_ALL_CATEGORIES
			query_zoom_cats = "&amp;zoom_cat=-1"
		else
			OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & " " & STR_RESULTS_IN_CATEGORY & " "
			for catit = 0 to num_zoom_cats-1
				if (catit > 0) then
					OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & ", "
				end if
				OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & """" & catnames(zoomcat(catit)) & """"
				query_zoom_cats = query_zoom_cats & "&amp;zoom_cat%5B%5D=" & zoomcat(catit)
			next
		end if
	end if
	OutBuf(OUTPUT_HEADING) = OutBuf(OUTPUT_HEADING) & "</i><br /></div>" & VbCrLf

	OutResBuf = OutResBuf & "<div class=""results"">" & VbCrLf

	' Begin main search loop ------------------------------------------------------
	Dim NumSearchWords, outputline, pagesCount, matches, relative_pos, current_pos
	Dim context_maxgoback
	Dim exclude_count, ExcludeTerm

	'Loop through all search words
	NumSearchWords = UBound(SearchWords)+1
	outputline = 0
	IsMaxLimitExceeded = 0
	wordsmatched = 0

	'default to use wildcards
	UseWildCards = 1

	' Check for skipped words in search query
	SkippedWords = 0
	SkippedOutputStr = ""
	SkippedExactPhrase = 0

	pagesCount = NumPages
	Dim res_table()
	Redim preserve res_table(6, pagesCount)

	matches = 0

	relative_pos = 0
	current_pos = 0

	dim data

	dim phrase_data_count()
	dim phrase_terms_data()
	dim xdata()
	dim countbytes

	exclude_count = 0
	context_maxgoback = 1

	redim sw_results(NumSearchWords)
	redim search_terms_ids(NumSearchWords)
	redim phrase_terms_ids(NumSearchWords)

	redim UseWildCards(NumSearchWords)
	redim RegExpSearchWords(NumSearchWords)
	
	' queryForURL is the query prepared to be passed in a URL.
	queryForURL = Server.URLEncode(query)

	' Find recommended links if any (before stemming)
	Dim num_recs_found
	Dim rec_multiwords, rec_multiwords_count
	Dim IsRecLinkFound	' only necessary because vbscript can't handle calling a function and ignoring its return value
	num_recs_found = 0
	if (Recommended = 1) then
		for rl = 0 to rec_count-1
			rec_word = Trim(rec(0, rl))
			if (ToLowerSearchWords = 1) then
				rec_word = Lcase(rec_word)
			end if
			rec_idx = rec(1, rl)
			' if split word here
			if (InStr(rec_word, ",") > 0) then
				rec_multiwords = Split(rec_word, ",")
				rec_multiwords_count = UBound(rec_multiwords)
				for each rec_mw in rec_multiwords
					if (RecLinkWordMatch(rec_mw, rec_idx) = True) then
						exit for
					end if
				next
			else
				IsRecLinkFound = RecLinkWordMatch(rec_word, rec_idx)
			end if
			' end block
			if (num_recs_found >= RecommendedMax) then
				exit for
			end if
		next
		if (num_recs_found > 0) then
			OutBuf(OUTPUT_RECOMMENDED) = OutBuf(OUTPUT_RECOMMENDED) & "</div>"
		end if
	end if

	for sw = 0 to NumSearchWords-1
		sw_results(sw) = 0
		UseWildCards(sw) = 0

		if (InStr(SearchWords(sw), "*") <> 0 OR InStr(SearchWords(sw), "?") <> 0) then
			RegExpSearchWords(sw) = pattern2regexp(SearchWords(sw))
			UseWildCards(sw) = 1
		end if

		if (Highlighting = 1 AND UseWildCards(sw) = 0) then
			RegExpSearchWords(sw) = SearchWords(sw)
			if (InStr(RegExpSearchWords(sw), "\")) then
				RegExpSearchWords(sw) = Replace(RegExpSearchWords(sw), "\", "\\")
			end if
		end if
	next

	Dim sw, bSkipped, ExactPhrase, patternStr, WordNotFound, word, ptr, bMatched, bytes_buffer, bytes_count
	Dim j, k, data_count, score, ipage, txtptr, prox, GotoNextPage, FoundPhrase, pageexists, xdictword, overlapProx

	for sw = 0 to NumSearchWords-1

		'initialize the sw_results here, since redim won't do it
		sw_results(sw) = 0

		bSkipped = False

		if (SearchWords(sw) = "") then
			bSkipped = True
		end if

		if (len(SearchWords(sw)) < MinWordLen) then
			SkipSearchWord(sw)
			bSkipped = True
		end if

		if (bSkipped = False) then

			ExactPhrase = 0
			ExcludeTerm = 0

			' Check exclusion searches
			if (Left(SearchWords(sw), 1) = "-") then
				SearchWords(sw) = Right(SearchWords(sw), len(SearchWords(sw))-1)
				SearchWords(sw) = Trim(SearchWords(sw))
				ExcludeTerm = 1
				exclude_count = exclude_count + 1
			end if

			' Stem the words if necessary (only AFTER stripping exclusion char)			
			if (UseStemming = 1) then
				if (AllowExactPhrase = 0 OR InStr(SearchWords(sw), " ") = 0) then
					' no exact phrase here
					SearchWords(sw) = GetStemWord(SearchWords(sw))
				end if
			end if
			
			if (AllowExactPhrase = 1 AND InStr(SearchWords(sw), " ") <> 0) then
				' initialise exact phrase matching for this search 'term'
				Dim phrase_terms, num_phrase_terms, tmpid, wordmap_row, xbi
				Dim terms_ids

				ExactPhrase = 1
				phrase_terms = Split(SearchWords(sw), " ")
				num_phrase_terms = UBound(phrase_terms)+1
				if (num_phrase_terms > context_maxgoback) then
					context_maxgoback = num_phrase_terms
				end if

				tmpid = 0
				WordNotFound = 0

				Redim terms_ids(num_phrase_terms)

				for j = 0 to num_phrase_terms-1

					if (UseStemming = 1) then
						phrase_terms(j) = GetStemWord(phrase_terms(j))
					end if

					tmpid = GetDictID(phrase_terms(j))
					if (tmpid = -1) then
						WordNotFound = 1
						exit for
					end if
					terms_ids(j) = tmpid

					wordmap_row = Int(dict(1, tmpid))
					if (wordmap_row <> -1) then
						bfp_wordmap.Position = wordmap_row
						if (bfp_wordmap.EOS = True) then
							exit for
						end if
						countbytes = GetBytes(bfp_wordmap, 2)
						redim preserve phrase_data_count(j)
						phrase_data_count(j) = countbytes
						redim xdata(3, countbytes)
						for xbi = 0 to countbytes-1
							xdata(0, xbi) = GetBytes(bfp_wordmap, 1)
							xdata(1, xbi) = GetBytes(bfp_wordmap, 1)
							xdata(2, xbi) = GetBytes(bfp_wordmap, 2)
							xdata(3, xbi) = GetBytes(bfp_wordmap, 4)
							redim preserve phrase_terms_data(j)
							phrase_terms_data(j) = xdata
						next
					else
						redim preserve phrase_data_count(j)
						phrase_data_count(j) = 0
					end if
				next
				terms_ids(j) = 0	' null terminate the list
				phrase_terms_ids(sw) = terms_ids
			' check whether there are any wildcards used
			elseif (UseWildCards(sw) = 1) then

				patternStr = ""

				if (SearchAsSubstring = 0) then
					patternStr = patternStr & "^"
				end if

				' new keyword pattern to match for
				patternStr = patternStr & RegExpSearchWords(sw)

				if (SearchAsSubstring = 0) then
					patternStr = patternStr & "$"
				end if

				regExp.Pattern = patternStr
			end if


			if (WordNotFound <> 1) then

				'Read in a line at a time from the keywords file
				for zoomit = 0 to dict_count

					word = dict(DICT_WORD, zoomit)
					ptr = dict(DICT_PTR, zoomit)

					if (ToLowerSearchWords = 1) then
						word = Lcase(word)
					end if

					if (ExactPhrase = 1) then
						'bMatched = phrase_terms(0) = word
						if (zoomit = phrase_terms_ids(sw)(0)) then
							bMatched = True
						else
							bMatched = False
						end if
					elseif (UseWildCards(sw) = 0) then
						if (SearchAsSubstring = 0) then
							bMatched = SearchWords(sw) = word
						else
							bMatched = InStr(word, SearchWords(sw))
						end if
					else
						bMatched = regExp.Test(word)
					end if

					' word found but indicated to be not indexed or skipped
					if (bMatched AND Int(ptr) = -1) then
						if (UseWildCards(sw) = 0 AND SearchAsSubstring = 0) then
							SkippedExactPhrase = 1
							SkipSearchWord(sw)
							exit for
						else
							'continue
							bMatched = False ' do nothing until next iteration
						end if
					end if

					if (bMatched) then
						'keyword found in dictionary
						wordsmatched = wordsmatched + 1
						if (ExcludeTerm = 0 AND wordsmatched > MaxMatches) then
							IsMaxLimitExceeded = 1
							exit for
						end if

						Dim ContextSeeks, maxptr, maxptr_term, xi, tmpdata, FoundFirstWord, pos
						Dim BufferLen, buffer_bytesread, xword_id, bytesread, dict_id, bytes

						' remember the dictionary ID for this matched search term
						search_terms_ids(sw) = zoomit

						if (ExactPhrase = 1) then
							data_count = phrase_data_count(0)
							redim data(3, data_count)
							data = phrase_terms_data(0)
							ContextSeeks = 0
						else
							bfp_wordmap.Position = ptr
							if (bfp_wordmap.EOS = True) then
								exit for
							end if
							'first 2 bytes is data count
							data_count = GetBytes(bfp_wordmap, 2)
							redim data(3, data_count)
							for j = 0 to data_count-1
								'redim preserve data(3, j)
								data(0, j) = GetBytes(bfp_wordmap, 1)   'score
								data(1, j) = GetBytes(bfp_wordmap, 1)	'prox
								data(2, j) = GetBytes(bfp_wordmap, 2)   'pagenum
								data(3, j) = GetBytes(bfp_wordmap, 4)   'ptr
							next
						end if

						sw_results(sw) = sw_results(sw) + data_count

						for j = 0 to data_count-1
							score = Int(data(0, j))
							prox = data(1, j)
							ipage = data(2, j)  'pagenum
							txtptr = data(3, j)
							GotoNextPage = 0
							FoundPhrase = 0

							if (boost(ipage) <> 0) then
								score = score * (boost(ipage) / 10)
							end if

							if (score = 0) then
								GotoNextPage = 1
							end if

							if (ExactPhrase = 1) then
								maxptr = txtptr
								maxptr_term = 0

								' check if all of the other words in the phrase appears on this page
								for xi = 1 to num_phrase_terms-1
									' see if this word appears at all on this page, if not, we stop scanning page
									' do not check for skipped words (data count value of zero)
									if (phrase_data_count(xi) <> 0) then
										' check wordmap for this search phrase to see if it appears on the current page
										tmpdata = phrase_terms_data(xi)
										for xbi = 0 to phrase_data_count(xi)-1
											if (tmpdata(2, xbi) = data(2, j)) then
												overlapProx = tmpdata(1, xbi) * 2
												if ((data(1, j) AND tmpdata(1, xbi)) = 0 AND (data(1,j) AND overlapProx) = 0) then
													GotoNextPage = 1
												else
													' intersection, this term appears on both pages, goto next term
													' remember biggest pointer
													if (tmpdata(3, xbi) > maxptr) then
														maxptr = tmpdata(3, xbi)
														maxptr_term = xi
													end if
													score = score + tmpdata(0, xbi)
												end if
												exit for
											end if
										next
										if (xbi >= phrase_data_count(xi)) then ' if not found
											GotoNextPage = 1
										end if
										if (GotoNextPage = 1) then
											exit for
										end if
									end if
								next

								if (GotoNextPage <> 1) then

									ContextSeeks = ContextSeeks + 1
									if (ContextSeeks > MaxContextSeeks) then
										IsMaxLimitExceeded = 1										
										exit for
									end if

									' ok so this page contains all the words in the phrase
									FoundPhrase = 0
									FoundFirstWord = 0

									' we goto the first occurance of the first word in pagetext
									pos = maxptr - ((maxptr_term+3) * DictIDLen) ' assume 3 possible punct.
									' do not seek further back than the occurance of the first word (avoid wrong page)
									if (pos < txtptr) then
										pos = txtptr
									end if
									bin_pagetext.Position = pos

									bytes_buffer = ""
									BufferLen = 120*DictIDLen ' we need a multiple of our DictIDLen (previous value: 256)
									buffer_bytesread = BufferLen

									' now we look for the phrase within the context of this page
									Do
										for xi = 0 to num_phrase_terms-1
											do
												xword_id = 0
												bytesread = 0

												if (buffer_bytesread >= BufferLen) then
													bytes_buffer = bin_pagetext.Read(BufferLen)
													buffer_bytesread = 0
												end if
												dict_id = 0
												bytes = Midb(bytes_buffer, buffer_bytesread+1, DictIDLen)
												if (bytes = "") then
													OutResBuf = OutResBuf & "Error: Expected range outside pagetext file. Make sure ALL index files have been updated."
													exit for
												end if
												for k = 1 to DictIDLen-1 '-1 to exclude variant byte
													dict_id = dict_id + Ascb(Midb(bytes, k, 1)) * (256^(k-1))
												next
												xword_id = xword_id + dict_id
												buffer_bytesread = buffer_bytesread + DictIDLen
												bytesread = bytesread + DictIDLen

												pos = pos + bytesread
												if (xword_id = 0 OR xword_id = 1 OR xword_id > dict_count) then
													exit for
												end if
												' if punct. keep reading.
											loop while (xword_id <= DictReservedLimit AND pos < bin_pagetext.Size)

											'xdictword = dict(0, xword_id)
											'if (MapAccents = 1) then
											'	For xch = 0 to UBound(NormalChars)
											'        xdictword = Replace(xdictword, AccentChars(xch), NormalChars(xch))
											'    Next
											'end if

											' if the words are not the same, we break out
											'if (Lcase(xdictword) <> phrase_terms(xi)) then
											if (xword_id <> phrase_terms_ids(sw)(xi)) then
												' also check against first word
												'if (xi <> 0 AND Lcase(xdictword) = phrase_terms(0)) then
												if (xi <> 0 AND xword_id = phrase_terms_ids(sw)(0)) then
													xi = 0	' matched first word
												else
													exit for
												end if
											end if

											if (xi = 0) then
												FoundFirstWord = FoundFirstWord + 1
												' remember the position of the 'start' of this phrase
												txtptr = pos - bytesread
											end if
										next

										if (xi = num_phrase_terms) then
											' exact phrase found
											FoundPhrase = 1
										end if
									Loop while xword_id <> 0 AND FoundPhrase = 0 AND FoundFirstWord <= score
								end if

								if (FoundPhrase <> 1) then
									GotoNextPage = 1
								end if
								
								CheckTime = Timer - StartTime
								CheckTime = Round(CheckTime, 3)
								if (CheckTime > MaxSearchTime) then
									IsMaxLimitExceeded = 1
									exit for
								end if

							end if

							' check whether we should skip to next page or not

							if (GotoNextPage <> 1) then

								'Check if page is already in output list
								pageexists = 0

								if ipage < 0 OR ipage > pagesCount then
									OutResBuf = OutResBuf & "Error: Page number too big. Make sure ALL index files are updated."
									exit for
								end if

								if (ExcludeTerm = 1) then
									' we clear out the score entry so that it'll be excluded
									res_table(0, ipage) = Int(0)
								elseif (Int(res_table(0, ipage)) = 0) then
									matches = matches + 1
									res_table(0, ipage) = score
									if (res_table(0, ipage) <= 0) then
										OutResBuf = OutResBuf & "Score should not be negative: " & score & "<br />"
									end if
									res_table(2, ipage) = txtptr
									res_table(6, ipage) = prox
								else
									if (Int(res_table(0, ipage)) > 10000) then
										' take it easy if its too big (to prevent huge scores)
										res_table(0, ipage) = Int(res_table(0, ipage)) + 1
									else
										res_table(0, ipage) = Int(res_table(0, ipage)) + score
									end if

									'store the next two searchword matches
									if (Int(res_table(1, ipage)) > 0 AND Int(res_table(1, ipage)) < MaxContextKeywords) then
										if (Int(res_table(3, ipage)) = 0) then
											res_table(3, ipage) = txtptr
										elseif (Int(res_table(4, ipage)) = 0) then
											res_table(4, ipage) = txtptr
										end if
									end if
									res_table(6, ipage) = res_table(6, ipage) AND prox
								end if

								' store the 'total terms matched' value
								res_table(1, ipage) = Int(res_table(1, ipage)) + 1

								' store the 'AND search terms matched' value
								if (res_table(5, ipage) = sw OR res_table(5, ipage) = sw-SkippedWords-exclude_count) then
									res_table(5, ipage) = Int(res_table(5, ipage)) + 1
								end if

							end if
						next

						if (UseWildCards(sw) = 0 AND SearchAsSubstring = 0) then
							exit for
						end if
					end if
				next
			end if
		end if

		if (sw <> NumSearchWords-1) then
			bfp_wordmap.Position = 1
		end if
	next

	'Close the keywords file that was being used
	bfp_wordmap.Close

	if SkippedWords > 0 then
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<div class=""summary"">" & STR_SKIPPED_FOLLOWING_WORDS & " " & SkippedOutputStr & ".<br />"
		if (SkippedExactPhrase = 1) then
			OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & STR_SKIPPED_PHRASE & ".<br />"
		end if
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<br /></div>"
	end if
	
	metaParams = ""
	' append to queryForURL with other query parameters for custom meta fields?
	if (UseMetaFields = 1) then
		for fieldnum = 0 to NumMetaFields-1
			if (IsArray(meta_query(fieldnum))) then
				for mqi = 0 to UBound(meta_query(fieldnum))-1
					metaParams = metaParams & "&amp;" & metafields(fieldnum)(METAFIELD_NAME) & "[]=" & meta_query(fieldnum)(mqi)
				next
			else
				if (meta_query(fieldnum) <> "") then
					metaParams = metaParams & "&amp;" & metafields(fieldnum)(METAFIELD_NAME) & "=" & meta_query(fieldnum)
				end if
			end if
		next
	end if	

	'Do this after search form so we can keep the search form value the same as the way the user entered it
	if (UseMetaFields = 1 AND MetaMoneyShowDec = 1) then
		for fieldnum = 0 to NumMetaFields-1
			if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MONEY AND IsNumeric(meta_query(fieldnum))) then
				meta_query(fieldnum) = meta_query(fieldnum) * 100
			end if
		next
	end if
	

	Dim oline, fullmatches, full_numwords, SomeTermMatches, num_multi_query
	Dim IsFiltered, IsAnyDropdown

	oline = 0
	fullmatches = 0

	dim output()

	Dim proxScale, baseScale, finalScale
	baseScale = 1.3
	proxScale = 1.7
	if (WeightProximity <> 0) then
		proxScale = proxScale + (WeightProximity/10)
	end if

	Dim CatCounter()
	Dim CatCounterFilled
	CatCounterFilled = 0
	if (UseCats = 1 AND DisplayCatSummary = 1) then
		if (zoomcat(0) = -1 OR num_zoom_cats > 1) then
			Redim CatCounter(NumCats)
			for catit = 0 to NumCats-1
				CatCounter(catit) = 0
			next
		else
			DisplayCatSummary = 0
		end if
	end if

	full_numwords = NumSearchWords - SkippedWords - exclude_count
	for zoomit = 0 to pagesCount-1
		IsFiltered = False
		if (res_table(0, zoomit) > 0 OR IsEmptyMetaQuery = True) then

			if (UseMetaFields = 1 AND IsFiltered = False) then
				Dim tmpQueryVal

				for fieldnum = 0 to NumMetaFields-1

					IsAnyDropdown = False

					if (IsArray(meta_query(fieldnum))) then
						tmpQueryVal = meta_query(fieldnum)(0)
					else
						tmpQueryVal = meta_query(fieldnum)
					end if

					if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_DROPDOWN OR metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI) then
						if (tmpQueryVal = "" OR tmpQueryVal = "-1") then
							IsAnyDropdown = True
						end if
					end if

					if (tmpQueryVal <> "" AND IsAnyDropdown = False) then
						if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_TEXT) then
							if Len(metavalues(zoomit)(fieldnum)) = 0 then
								IsFiltered = True
							elseif (metafields(fieldnum)(METAFIELD_METHOD) = METAFIELD_METHOD_SUBSTRING) then
								if (InStr(Lcase(metavalues(zoomit)(fieldnum)), Lcase(meta_query(fieldnum))) = False) then
									IsFiltered = True								
								end if
							else
								if (Lcase(metavalues(zoomit)(fieldnum)) <> Lcase(meta_query(fieldnum))) then
									IsFiltered = True
								end if
							end if
						elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_DROPDOWN) then
							if (metavalues(zoomit)(fieldnum) = METAFIELD_NOVALUE_MARKER) then
								IsFiltered = True
							else
								if (Int(metavalues(zoomit)(fieldnum)) <> Int(meta_query(fieldnum))) then
									IsFiltered = True
								end if
							end if
						elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI) then
							IsFiltered = True
							if (metavalues(zoomit)(fieldnum)(0) > 0) then
								num_multi_query = UBound(meta_query(fieldnum))-1
								for mqi = 0 to num_multi_query
									for mvi = 0 to metavalues(zoomit)(fieldnum)(0)-1
										if (metavalues(zoomit)(fieldnum)(mvi+1) = CInt(meta_query(fieldnum)(mqi))) then
											IsFiltered = False
											exit for
										end if
									next
									if (IsFiltered = False) then
										exit for
									end if
								next
							end if
						else
							if (metavalues(zoomit)(fieldnum) = METAFIELD_NOVALUE_MARKER) then
								IsFiltered = True
							else
								' numeric comparison here
								Dim bRet
								if (metafields(fieldnum)(METAFIELD_METHOD) = METAFIELD_METHOD_LESSTHAN) then
									bRet = metavalues(zoomit)(fieldnum) < meta_query(fieldnum)
								elseif (metafields(fieldnum)(METAFIELD_METHOD) = METAFIELD_METHOD_LESSTHANORE) then
									bRet = metavalues(zoomit)(fieldnum) <= meta_query(fieldnum)
								elseif (metafields(fieldnum)(METAFIELD_METHOD) = METAFIELD_METHOD_GREATERTHAN) then
									bRet = metavalues(zoomit)(fieldnum) > meta_query(fieldnum)
								elseif (metafields(fieldnum)(METAFIELD_METHOD) = METAFIELD_METHOD_GREATERTHANORE) then
									bRet = metavalues(zoomit)(fieldnum) >= meta_query(fieldnum)
								else
									bRet = metavalues(zoomit)(fieldnum) = meta_query(fieldnum)
								end if

								if (bRet = False) then
									IsFiltered = True
								end if
							end if
						end if
					end if

					if (IsEmptyMetaQuery = True AND IsFiltered = False) then
						res_table(0, zoomit) = Int(res_table(0, zoomit)) + 1
						res_table(1, zoomit) = Int(res_table(1, zoomit)) + 1
					end if

					if (IsFiltered = True) then
						exit for
					end if
				next
			end if

			if (IsFiltered = False) then
				if (res_table(5, zoomit) < full_numwords AND andq = 1) then					
					' AND search, filter out non-matching results
					IsFiltered = True
				end if
			end if
			
			if (UseCats = 1 AND zoomcat(0) <> -1 AND IsFiltered = False) then
				Dim IsFoundCat
				IsFoundCat = False
				for cati = 0 to num_zoom_cats-1
					'if ((CDbl(catpages(zoomit)) AND CDbl(2)^CDbl(zoomcat(cati))) <> 0) then
					if (CheckBitInByteArray(zoomcat(cati), catpages(zoomit)) <> 0) then
						if (DisplayCatSummary = 1) then
							CatCounter(zoomcat(cati)) = CatCounter(zoomcat(cati)) + 1
							CatCounterFilled = 1
						end if
						IsFoundCat = True
						exit for
					end if
				next
				if (IsFoundCat = False) then
					IsFiltered = True
				end if
			end if

			if (IsFiltered = False) then
				
				if (res_table(5, zoomit) >= full_numwords) then
					fullmatches = fullmatches + 1				
				end if
				
				' copy if not filtered out
				redim preserve output(5, oline)
				output(0, oline) = zoomit

				'scale score
				finalScale = ((res_table(6, zoomit) / 255.0) * proxScale) + baseScale

				if (res_table(1, zoomit) > 1) then
					if (res_table(1, zoomit) <= 10) then
						finalScale = (finalScale ^ (res_table(1, zoomit)-1))
					else
						finalScale = (finalScale ^ 10)
						finalScale = finalScale + (res_table(1, zoomit)-10)
					end if
				end if

				if (UseCats = 1 AND DisplayCatSummary = 1 AND zoomcat(0) = -1) then
					'if we are doing an All category search AND we're showing cat summary
					for cati = 0 to NumCats-1
						'if ((CDbl(catpages(zoomit)) AND CDbl(2)^CDbl(cati)) <> 0) then
						if (CheckBitInByteArray(cati, catpages(zoomit)) <> 0) then
							CatCounter(cati) = CatCounter(cati) + 1
							CatCounterFilled = 1
						end if
					next
				end if

				' final score
				output(1, oline) = Round(res_table(0, zoomit) * finalScale)
				output(2, oline) = res_table(1, zoomit)
				output(3, oline) = res_table(2, zoomit)
				output(4, oline) = res_table(3, zoomit)
				output(5, oline) = res_table(4, zoomit)
				oline = oline + 1
			end if
		end if
	Next

	matches = oline

	' Sort the results
	if (matches > 1) then
		if (zoomsort = 1 AND UseDateTime = 1) then
			call ShellSortByDate(output, datetime)
		else
			call ShellSort(output)
		end if
	end if

	'Display search results
	OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<div class=""summary"">"
	
	if (IsMaxLimitExceeded = 1) then
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & STR_PHRASE_CONTAINS_COMMON_WORDS & "<br />"
	end if
	
	if matches = 0 Then
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & STR_SUMMARY_NO_RESULTS_FOUND
	elseif NumSearchWords > 1 AND andq = 0 then
		SomeTermMatches = matches - fullmatches
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & PrintNumResults(fullmatches) & " " & STR_SUMMARY_FOUND_CONTAINING_ALL_TERMS & " "
		if (SomeTermMatches > 0) then
			OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & PrintNumResults(SomeTermMatches) & " " & STR_SUMMARY_FOUND_CONTAINING_SOME_TERMS
		end if
	elseif NumSearchWords > 1 AND andq = 1 then
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & PrintNumResults(fullmatches) & " " & STR_SUMMARY_FOUND_CONTAINING_ALL_TERMS
	else
		OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & PrintNumResults(matches) & " " & STR_SUMMARY_FOUND
	end if
	OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<br /></div>" & VbCrlf

	if (matches < 3) then
		if (andq = 1 AND NumSearchWords > 1) then
			OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<div class=""suggestion""><br />" & STR_POSSIBLY_GET_MORE_RESULTS & " <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=0" & "&amp;zoom_sort=" & zoomsort & """>" & STR_ANY_OF_TERMS & "</a>.</div>"
		elseif (UseCats = 1 AND zoomcat(0) <> -1) then
			OutBuf(OUTPUT_SUMMARY) = OutBuf(OUTPUT_SUMMARY) & "<div class=""suggestion""><br />" & STR_POSSIBLY_GET_MORE_RESULTS & " <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_per_page=" & per_page & "&amp;zoom_cat=-1" & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & STR_ALL_CATS & "</a>.</div>"
		end if
	end if

	'Show category summary
	if (UseCats = 1 AND DisplayCatSummary = 1 AND CatCounterFilled = 1) then
		OutBuf(OUTPUT_CATSUMMARY) = OutBuf(OUTPUT_CATSUMMARY) & "<div class=""cat_summary""><br />" & STR_CAT_SUMMARY & "<ul>"
		Dim catSummaryItemCount
		catSummaryItemCount = 0
		for catit = 0 to NumCats-1			
			' if all the results found belonged in this current category, then we don't show it in the summary
			if (CatCounter(catit) > 0) then
				if (CatCounter(catit) <> matches) then
					catSummaryItemCount = catSummaryItemCount + 1
					OutBuf(OUTPUT_CATSUMMARY) = OutBuf(OUTPUT_CATSUMMARY) & "<li><a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_cat[]=" & catit & "&amp;zoom_per_page=" & per_page & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & catnames(catit)
					OutBuf(OUTPUT_CATSUMMARY) = OutBuf(OUTPUT_CATSUMMARY) & "</a> (" & CatCounter(catit) & ")</li>"
				end if
			end if
		next
		
		if (catSummaryItemCount = 0) then			
			OutBuf(OUTPUT_CATSUMMARY) = ""
		else
			OutBuf(OUTPUT_CATSUMMARY) = OutBuf(OUTPUT_CATSUMMARY) & "</ul></div>"
		end if
	end if

	if (Spelling = 1) then
		Dim spellfile, spell_count, sp_line, sp_linenum, sw_spcode, spcode
		Dim SuggestionsCount, SuggestionFound, SuggestStr, word1, word2, word3

		' load in spellings file
		spellfile = split(ReadDatFile(zoomfso, "zoom_spelling.zdat"), chr(10))
		spell_count = UBound(spellfile)-1
		dim spell()
		redim spell(4, spell_count)
		for zoomit = 0 to spell_count
			sp_line = Split(spellfile(zoomit), " ", 4)
			sp_linenum = UBound(sp_line)
			if (sp_linenum > 0) then
				spell(0, zoomit) = sp_line(0)
				spell(1, zoomit) = sp_line(1)
				spell(2, zoomit) = 0
				spell(3, zoomit) = 0
				if (sp_linenum > 1) then
					spell(2, zoomit) = sp_line(2)
					if (sp_linenum > 2) then
						spell(3, zoomit) = sp_line(3)
					end if
				end if
			end if
		next
		' re-value spell_count in case of errors in dict file
		spell_count = UBound(spell, 2)

		Dim dictid, nextsuggest, tmpWordStr

		SuggestionsCount = 0
		SuggestStr = ""
		word1 = ""
		word2 = ""
		word3 = ""
		tmpWordStr = ""

		for sw = 0 to NumSearchWords-1

			if (sw_results(sw) >= SpellingWhenLessThan) then
				' this word has enough results
				if (sw > 0) then
					SuggestStr = SuggestStr & " "
				end if
				SuggestStr = SuggestStr & SearchWords(sw)
			else
				' this word returned less results than threshold, and requires spelling suggestions
				sw_spcode = GetSPCode(SearchWords(sw))

				if (Len(sw_spcode) > 0) then
					SuggestionFound = 0
					for zoomit = 0 to spell_count

						spcode = spell(0, zoomit)

						if (spcode = sw_spcode) then
							j = 0
							do while (SuggestionFound = 0 AND j < 3)
								if (spell(1+j, zoomit) = 0) then
									exit do
								end if

								dictid = CLng(spell(1+j, zoomit))
								word1 = GetSpellingWord(dictid)
								tmpWordStr = word1
								if (ToLowerSearchWords = 1) then
									tmpWordStr = Lcase(tmpWordStr)
								end if
								if (UseStemming = 1) then
									tmpWordStr = GetStemWord(tmpWordStr)
								end if

								if (tmpWordStr = SearchWords(sw)) then
									' Check that it is not the same word
									SuggestionFound = 0
								else
									SuggestionFound = 1
									SuggestionsCount = SuggestionsCount + 1
									if (NumSearchWords = 1) then  ' single word search
										nextsuggest = j+1
										if (j < 1) then
											if (spell(1+nextsuggest, zoomit) <> 0) then
												dictid = spell(1+nextsuggest, zoomit)
												word2 = GetSpellingWord(dictid)
												tmpWordStr = word2
												if (ToLowerSearchWords = 1) then
													tmpWordStr = Lcase(tmpWordStr)
												end if
												if (UseStemming = 1) then
													tmpWordStr = GetStemWord(tmpWordStr)
												end if
												if (tmpWordStr = SearchWords(sw)) then
													word2 = ""
												end if
											end if
										end if
										nextsuggest = nextsuggest+1
										if (j < 2) then
											if (spell(1+nextsuggest, zoomit) <> 0) then
												dictid = spell(1+nextsuggest, zoomit)
												word3 = GetSpellingWord(dictid)
												tmpWordStr = word3
												if (ToLowerSearchWords = 1) then
													tmpWordStr = Lcase(tmpWordStr)
												end if
												if (UseStemming = 1) then
													tmpWordStr = GetStemWord(tmpWordStr)
												end if
												if (tmpWordStr = SearchWords(sw)) then
													word3 = ""
												end if
											end if
										end if
									end if
								end if
								j = j + 1
							loop
						elseif (spcode > sw_spcode) then
							exit for
						end if
						if (SuggestionFound = 1) then
							exit for
						end if
					next

					if (SuggestionFound = 1) then
						if (sw > 0) then
							SuggestStr = SuggestStr & " "
						end if
						SuggestStr = SuggestStr & word1  ' add string AFTER so we can preserve order of words
					end if
				end if
			end if

		next

		if (SuggestionsCount > 0) then
			OutBuf(OUTPUT_SUGGESTION) = OutBuf(OUTPUT_SUGGESTION) & "<div class=""suggestion""><br />" & STR_DIDYOUMEAN & " <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & Server.URLEncode(SuggestStr) & metaParams & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=0&amp;zoom_sort=" & zoomsort & """>" & SuggestStr & "</a>"
			if (Len(word2) > 0) then
				OutBuf(OUTPUT_SUGGESTION) = OutBuf(OUTPUT_SUGGESTION) & " " & STR_OR & " <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & Server.URLEncode(word2) & metaParams & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & word2 & "</a>"
			end if
			if (Len(word3) > 0) then
				OutBuf(OUTPUT_SUGGESTION) = OutBuf(OUTPUT_SUGGESTION) & " " & STR_OR & " <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & Server.URLEncode(word3) & metaParams & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & word3 & "</a>"
			end if
			OutBuf(OUTPUT_SUGGESTION) = OutBuf(OUTPUT_SUGGESTION) & "?</div>"
		end if
	end if

	' Number of pages of results
	Dim num_pages	
	num_pages = Ceil(matches / per_page)	
	if (num_pages > 1) then
		OutBuf(OUTPUT_PAGESCOUNT) = OutBuf(OUTPUT_PAGESCOUNT) & "<div class=""result_pagescount"">" & num_pages & " " & STR_PAGES_OF_RESULTS & "</div>" & VbCrlf
	end if

	Dim pgdata, url, title, description, ddarray

	' Show sorting options
	if (matches > 1 AND UseDateTime = 1) then
		OutBuf(OUTPUT_SORTING) = OutBuf(OUTPUT_SORTING) & "<div class=""sorting"">"
		if (zoomsort = 1) then
			OutBuf(OUTPUT_SORTING) = OutBuf(OUTPUT_SORTING) & "<a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_page=" & zoompage & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=0"">" & STR_SORTBY_RELEVANCE & "</a> / <b>" & STR_SORTEDBY_DATE & "</b>"
		else
			OutBuf(OUTPUT_SORTING) = OutBuf(OUTPUT_SORTING) & "<b>" & STR_SORTEDBY_RELEVANCE & "</b> / <a href=""" & SelfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_page=" & zoompage & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=1"">" & STR_SORTBY_DATE & "</a>"
		end if
		OutBuf(OUTPUT_SORTING) = OutBuf(OUTPUT_SORTING) & "</div>"
	end if

	Dim arrayline, result_limit, urlLink

	' Determine current line of result from the $output array
	if (zoompage = 1) then
		arrayline = 0
	else
		arrayline = (zoompage - 1) * per_page
	end if

	' The last result to show on this page
	result_limit = arrayline + per_page

	' Display the results
	do while (arrayline < matches AND arrayline < result_limit)
		ipage = output(0, arrayline)
		score = output(1, arrayline)

		pgdata = GetPageData(ipage)
		url = pgdata(PAGEDATA_URL)
		title = pgdata(PAGEDATA_TITLE)
		description = pgdata(PAGEDATA_DESC)

		urlLink = url
		if (GotoHighlight = 1) then
			if (SearchAsSubstring = 1) then
				urlLink = AddParamToURL(urlLink, "zoom_highlightsub=" & queryForURL)
			else
				urlLink = AddParamToURL(urlLink, "zoom_highlight=" & queryForURL)
			end if
		end if
		if (PdfHighlight = 1) then
			if (InStr(Lcase(urlLink), ".pdf") <> False) then
				urlLink = urlLink & "#search=&quot;"&Replace(query, """", "")&"&quot;"
			end if
		end if

		if (arrayline Mod 2 = 0) then
			OutResBuf = OutResBuf & "<div class=""result_block"">"
		else
			OutResBuf = OutResBuf & "<div class=""result_altblock"">"
		end if

		if (linkaction(ipage) = 1) then
			zres_target = " target=""blank"""
		else
			zres_target = zoomtarget
		end if

		if (UseZoomImage = 1) then
			zres_image = pgdata(PAGEDATA_IMG)
			if (Len(zres_image) > 0) then
				OutResBuf = OutResBuf & "<div class=""result_image"">"
				OutResBuf = OutResBuf & "<a href=""" & urlLink & """"  & zres_target & "><img src="""&zres_image&""" alt="""" class=""result_image"" /></a>"
				OutResBuf = OutResBuf & "</div>"
			end if
		end if

		OutResBuf = OutResBuf & "<div class=""result_title"">"
		if (DisplayNumber = 1) then
			OutResBuf = OutResBuf & "<b>" & (arrayline+1) & ".</b>&nbsp;"
		end if

		if (DisplayTitle = 1) then
			OutResBuf = OutResBuf & "<a href=""" & urlLink & """"  & zres_target & ">"
			OutResBuf = OutResBuf & PrintHighlightDescription(title)
			OutResBuf = OutResBuf & "</a>"
		else
			OutResBuf = OutResBuf & "<a href=""" & urlLink & """"  & zres_target & ">" & url & "</a>"
		end if

		if (UseCats = 1) then
			OutResBuf = OutResBuf & " <span class=""category"">"
			for catindex = 0 to NumCats-1
				'if ((CDbl(catpages(ipage)) AND CDbl(2)^CDbl(catindex)) <> 0) then
				if (CheckBitInByteArray(catindex, catpages(ipage)) <> 0) then
					OutResBuf = OutResBuf & " [" & catnames(catindex) & "]"
				end if
			next			
			OutResBuf = OutResBuf & "</span>"
		end if
		OutResBuf = OutResBuf & "</div>" & VbCrlf

		if (UseMetaFields = 1 AND DisplayMetaFields = 1) then
			Dim cssFieldName, cssValueName
			for fieldnum = 0 to NumMetaFields-1
				cssFieldName = "result_metaname_" & metafields(fieldnum)(METAFIELD_NAME)
				cssValueName = "result_metavalue_" & metafields(fieldnum)(METAFIELD_NAME)
				if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MULTI) then
					if (metavalues(ipage)(fieldnum)(0) > 0) then
						OutResBuf = OutResBuf & "<div class=""result_custommeta"">"
						OutResBuf = OutResBuf & "<span class="""&cssFieldName&""">"&metafields(fieldnum)(METAFIELD_SHOW)&": </span>"
						OutResBuf = OutResBuf & "<span class="""&cssValueName&""">"
						ddarray = metafields(fieldnum)(METAFIELD_DROPDOWN)
						for mvi = 0 to metavalues(ipage)(fieldnum)(0)-1
							if (mvi > 0) then
								OutResBuf = OutResBuf & ", "
							end if
							OutResBuf = OutResBuf & ddarray(metavalues(ipage)(fieldnum)(mvi+1))
						next
						OutResBuf = OutResBuf & "</span>"
						OutResBuf = OutResBuf & "</div>"
					end if
				else
					if (metavalues(ipage)(fieldnum) <> METAFIELD_NOVALUE_MARKER AND metavalues(ipage)(fieldnum) <> METAFIELD_NOVALUE_MULTI AND Len(metavalues(ipage)(fieldnum)) > 0) then
						if (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_DROPDOWN) then
							OutResBuf = OutResBuf & "<div class=""result_custommeta"">"
							OutResBuf = OutResBuf & "<span class="""&cssFieldName&""">"&metafields(fieldnum)(METAFIELD_SHOW)&": </span>"
							ddarray = metafields(fieldnum)(METAFIELD_DROPDOWN)
							OutResBuf = OutResBuf & "<span class="""&cssValueName&""">"
							OutResBuf = OutResBuf & ddarray(metavalues(ipage)(fieldnum)) & "</span>"
							OutResBuf = OutResBuf & "</div>"
						elseif (metafields(fieldnum)(METAFIELD_TYPE) = METAFIELD_TYPE_MONEY) then
							OutResBuf = OutResBuf & "<div class=""result_custommeta"">"
							OutResBuf = OutResBuf & "<span class="""&cssFieldName&""">"&metafields(fieldnum)(METAFIELD_SHOW)&": </span>"
							Dim tmpMoneyStr
							if (MetaMoneyShowDec = 1) then
								tmpMoneyStr = FormatNumber(metavalues(ipage)(fieldnum)/100, 2, -1, 0, 0)
							else
								tmpMoneyStr = metavalues(ipage)(fieldnum)
							end if
							OutResBuf = OutResBuf & "<span class="""&cssValueName&""">" & MetaMoneyCurrency & tmpMoneyStr &"</span>"
							OutResBuf = OutResBuf & "</div>"
						else
							OutResBuf = OutResBuf & "<div class=""result_custommeta"">"
							OutResBuf = OutResBuf & "<span class="""&cssFieldName&""">"&metafields(fieldnum)(METAFIELD_SHOW)&": </span>"
							OutResBuf = OutResBuf & "<span class="""&cssValueName&""">" & metavalues(ipage)(fieldnum)&"</span>"
							OutResBuf = OutResBuf & "</div>"
						end if
					end if
				end if
			next
		end if

		if (DisplayMetaDesc = 1) then
			' print meta description
			if (Len(description) > 2) then
				OutResBuf = OutResBuf & "<div class=""description"">"
				OutResBuf = OutResBuf & PrintHighlightDescription(description)
				OutResBuf = OutResBuf & "</div>" & VbCrlf
			end if
		end if

		if (DisplayContext = 1 AND output(2, arrayline) > 0 AND IsEmptyMetaQuery = False) then
			Dim context_keywords, context_word_count, goback, gobackbytes, context_str
			Dim last_startpos, last_endpos, origpos, startpos, first_startpos, word_id, prev_word_id
			Dim noSpaceForNextChar, noGoBack, FoundContext
			Dim last_bytesread, cti, variant_index
			Dim contextArray, highlightArray

			' extract contextual page description
			context_keywords = output(2, arrayline)
			if (context_keywords > MaxContextKeywords) then
				context_keywords = MaxContextKeywords
			end if

			context_word_count = Ceil(ContextSize / context_keywords)

			goback = Int(context_word_count / 2)
			gobackbytes = goback * DictIDLen

			last_startpos = 0
			last_endpos = 0
			first_startpos = 0
			FoundContext = 0

			OutResBuf = OutResBuf & "<div class=""context"">" & VbCrLf
			for j = 0 to (context_keywords - 1) Step 1

				origpos = output(3+j, arrayline)
				startpos = origpos

				if (gobackbytes < startpos) then
					startpos = startpos - gobackbytes
					noGoBack = 0
				else
					noGoBack = 1
				end if

				' do not overlap with previous extract
				if ((startpos > last_startpos OR startpos > first_startpos) AND startpos < last_endpos) then
					startpos = last_endpos
				end if

				bin_pagetext.Position = startpos
				if (bin_pagetext.EOS = True) then
					exit for
				end if

				'remember last start position
				last_startpos = startpos
				if (j = 0) then
					first_startpos = startpos
				end if

				bytesread = 0
				last_bytesread = 0

				word_id = GetNextDictWord(bin_pagetext)
				variant_index = GetNextVariant(bin_pagetext)
				bytesread = bytesread + DictIDLen

				Redim contextArray(2, context_word_count)
				Redim highlightArray(context_word_count)

				for cti = 0 to context_word_count
					if (word_id = 0 OR word_id = 1 OR word_id > dict_count) then
						'if (zoomit > goback OR noGoBack = 1) then
						if (noGoBack = 1 OR bin_pagetext.Position > origpos) then
							exit for
						else
							Redim contextArray(2, context_word_count)
							Redim highlightArray(context_word_count)
							cti = 0
						end if
					else
						if (word_id >= NumKeywords) then
							OutResBuf = OutResBuf & "Critical error with pagetext file. Check that your files are from the same indexing session."
						else
							if (Highlighting = 1 AND IsEmptyMetaQuery = False AND (startpos+last_bytesread) = origpos) then
								highlightArray(cti) = 1
							end if

							contextArray(0, cti) = word_id
							contextArray(1, cti) = variant_index
						end if
					end if
					last_bytesread = bytesread

					word_id = GetNextDictWord(bin_pagetext)
					variant_index = GetNextVariant(bin_pagetext)
					bytesread = bytesread + DictIDLen
				next
				
				' rememeber the last end position
				if (word_id <> 0) then
					last_endpos = bin_pagetext.Position
				end if

				if (Highlighting = 1) then
					HighlightContextArray(context_word_count)
				end if

				prev_word_id = 0
				context_str = ""
				noSpaceForNextChar = False

				for cti = 0 to context_word_count

					word_id = contextArray(0, cti)
					variant_index = contextArray(1, cti)

					if (noSpaceForNextChar = False) then
						'No space for reserved words (punctuation, etc)
						if (word_id > DictReservedNoSpaces) then
							if (prev_word_id <= DictReservedPrefixes OR prev_word_id > DictReservedNoSpaces) then
								context_str = context_str & " "
							end if
						elseif (word_id > DictReservedSuffixes AND word_id <= DictReservedPrefixes) then
							context_str = context_str & " "
							noSpaceForNextChar = True
						elseif (word_id > DictReservedPrefixes) then
							noSpaceForNextChar = True
						end if
					else
						noSpaceForNextChar = False
					end if

					if (word_id > 0) then
						if (Highlighting = 1 AND (highlightArray(cti) = HIGHLIGHT_SINGLE OR highlightArray(cti) = HIGHLIGHT_START)) then
							context_str = context_str & "<span class=""highlight"">"
						end if

						context_str = context_str & GetDictionaryWord(word_id, variant_index)

						if (Highlighting = 1 AND (highlightArray(cti) = HIGHLIGHT_SINGLE OR highlightArray(cti) = HIGHLIGHT_END)) then
							context_str = context_str & "</span>"
						end if

						prev_word_id = word_id
					end if
				next

				if (Trim(title) = Trim(context_str)) then
					context_str = ""
				end if

				if (context_str <> "") then
					OutResBuf = OutResBuf & " <b>...</b> "
					FoundContext = 1
					OutResBuf = OutResBuf & context_str
				end if
			next
			if (FoundContext = 1) then
				OutResBuf = OutResBuf & " <b>...</b>"
			end if
			OutResBuf = OutResBuf & "</div>" & VbCrLf
		end if

		Dim info_str, tmpdate, tmpfilesize
		info_str = ""
		if (DisplayTerms = 1) then
			info_str = info_str & STR_RESULT_TERMS_MATCHED & " " & output(2, arrayline)
		end if

		if (DisplayScore = 1) then
			if (len(info_str) > 0) then
				info_str = info_str & "&nbsp; - &nbsp;"
			end if
			info_str = info_str & STR_RESULT_SCORE & " " & score
		end if

		if (DisplayDate = 1) then
			if (datetime(ipage) > 0) then
				if (len(info_str) > 0) then
					info_str = info_str & "&nbsp; - &nbsp;"
				end if
				tmpdate = unUDate(datetime(ipage))
				info_str = info_str & DatePart("d", tmpdate) & " " & MonthName(DatePart("m", tmpdate), true) & " " & DatePart("yyyy", tmpdate)
			end if
		end if

		if (DisplayFilesize = 1) then
			if (len(info_str) > 0) then
				info_str = info_str & "&nbsp; - &nbsp;"
			end if
			tmpfilesize = CLng(filesize(ipage) / 1024)
			if (tmpfilesize = 0) then
				tmpfilesize = 1
			end if
			info_str = info_str & tmpfilesize & "k"
		end if

		if (DisplayURL = 1) then
			if (len(info_str) > 0) then
				info_str = info_str & "&nbsp; - &nbsp;"
			end if
			if (TruncateShowURL > 0) then
				if (len(url) > TruncateShowURL) then
					url = Left(url, TruncateShowURL) & "..."
				end if
			end if
			info_str = info_str & STR_RESULT_URL & " " & url
		end if

		OutResBuf = OutResBuf & "<div class=""infoline"">"
		OutResBuf = OutResBuf & info_str
		OutResBuf = OutResBuf & "</div>" & VbCrlf
		OutResBuf = OutResBuf & "</div>" & VbCrlf
		arrayline = arrayline + 1
	loop

	if (DisplayContext = 1 OR AllowExactPhrase = 1) then
		bin_pagetext.Close
	end if

	fp_pagedata.Close

	'Show links to other result pages
	if (num_pages > 1) then
		Dim start_range, end_range
		' 10 results to the left of the current page
		start_range = zoompage - 10
		if (start_range < 1) then
			start_range = 1
		end if

		' 10 to the right
		end_range = zoompage + 10
		if (end_range > num_pages) then
			end_range = num_pages
		end if

		OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & "<div class=""result_pages""><b>" & STR_RESULT_PAGES & "</b> "
		if (zoompage > 1) then
			OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & "<a href=""" & selfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_page=" & (zoompage-1) & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>&lt;&lt; " & STR_RESULT_PAGES_PREVIOUS & "</a> "
		end if
		'for zoomit = 1 to num_pages
		for zoomit = start_range to end_range
			if (Int(zoomit) = Int(zoompage)) then
				OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & zoompage & " "
			else
				OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & "<a href=""" & selfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_page=" & zoomit & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & zoomit & "</a> "
			end if
		next
		if (Int(zoompage) <> Int(num_pages)) then
			OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & "<a href=""" & selfURL & LinkBackJoinChar & "zoom_query=" & queryForURL & metaParams & "&amp;zoom_page=" & (zoompage+1) & "&amp;zoom_per_page=" & per_page & query_zoom_cats & "&amp;zoom_and=" & andq & "&amp;zoom_sort=" & zoomsort & """>" & STR_RESULT_PAGES_NEXT & " &gt;&gt;</a> "
		end if
		OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & "</div>"
	end if

	OutResBuf = OutResBuf & "</div>" & VbCrLf   ' end results style tag

	' Time the searching
	if (Timing = 1 OR Logging = 1) then
		ElapsedTime = Timer - StartTime
		ElapsedTime = Round(ElapsedTime, 3)
		if (Timing = 1) then
			OutBuf(OUTPUT_SEARCHTIME) = OutBuf(OUTPUT_SEARCHTIME) & "<div class=""searchtime""><br />" &  STR_SEARCH_TOOK & " " & ElapsedTime & " " & STR_SECONDS & ".</div>"
		end if
	end if

	'Log the search words, if required
	if (Logging = 1) then
		LogQuery = Replace(query, """", """""")
		DateString = Year(Now) & "-" & Right("0" & Month(Now), 2) & "-" & Right("0" & Day(Now), 2)  & ", " & Right("0" & Hour(Now), 2) & ":" & Right("0" & Minute(Now), 2) & ":" & Right("0" & Second(Now), 2)
		LogString = DateString & ", " & Request.ServerVariables("REMOTE_ADDR") & ", """ & LogQuery & """, Matches = " & matches

		if (andq = 1) then
			LogString = LogString & ", AND"
		else
			LogString = LogString & ", OR"
		end if

		if (NewSearch = 1) then
			zoompage = 0
		end if

		LogString = LogString & ", PerPage = " & per_page & ", PageNum = " & zoompage

		if (UseCats = 0) then
			LogString = LogString & ", No cats"
		else
			if (zoomcat(0) = -1) then
				LogString = LogString & ", ""Cat = All"""
			else
				LogString = LogString & ", ""Cat = "
				for cati = 0 to num_zoom_cats-1
					if (cati > 0) then
						LogString = LogString & ", "
					end if
					logCatStr = catnames(zoomcat(cati))
					logCatStr = Replace(logCatStr, """", """""")    ' replace " with ""
					LogString = LogString & logCatStr
				next
				LogString = LogString & """"
			end if
		end if

		' avoid problems with languages with "," as decimal pt breaking log file format.
		ElapsedTime = Replace(ElapsedTime, ",", ".")
		LogString = LogString & ", Time = " & ElapsedTime

		LogString = LogString & ", Rec = " & num_recs_found

		' end of record
		LogString = LogString & VbCrLf

		on error resume next
		Dim logPath
		if (Mid(LogFileName, 2, 2) = ":\") then
			logPath = LogFileName
		else
			logPath = MapPath(LogFileName)
		end if		
		set logfile = zoomfso.OpenTextFile(logPath, 8, True, 0)
		if (Err.Number <> 0) then
			Response.Write("Unable to write to log file (" & logPath & "). Check that you have specified the correct log filename in your Indexer settings and that you have the required file permissions set.<br />")
		else
			logfile.Write(LogString)
			logfile.Close
		end if
		on error goto 0
	end if  ' Logging
end if  ' NoSearch

'Let others know about Zoom.
if (ZoomInfo = 1) then
	OutBuf(OUTPUT_PAGENUMBERS) = OutBuf(OUTPUT_PAGENUMBERS) & VbCrLf & "<center><p class=""zoom_advertising""><small>" & STR_POWEREDBY & " <a href=""http://www.wrensoft.com/zoom/"" target=""_blank""><b>Zoom Search Engine</b></a></small></p></center>"
end if

'Print out the end of the template
call ShowTemplate


' ----------------------------------------------------------------------------
' Porter Stemming Algorithm by Dr Martin Porter
' ASP implementation based on code by Christos Attikos.
' ----------------------------------------------------------------------------

Function GetStemWord(str)
	Dim StemStopChars
	StemStopChars = "`1234567890\-=\[\]\\;\',\./~!@#\$%\^&\*_\+|:""<>?"
	regExp.Pattern = "[" & StemStopChars & "]"
	'only strings greater than 2 are stemmed
	If Len(Trim(str)) > 2 AND regExp.Test(str) = False Then
		str = porterAlgorithmStep1(str)
		str = porterAlgorithmStep2(str)
		str = porterAlgorithmStep3(str)
		str = porterAlgorithmStep4(str)
		str = porterAlgorithmStep5(str)
	End If
	GetStemWord = str
End Function


Function porterAlgorithmStep1(str)
	Dim i
	Dim j
	Dim step1a(3, 1)
	step1a(0, 0) = "sses"
	step1a(0, 1) = "ss"
	step1a(1, 0) = "ies"
	step1a(1, 1) = "i"
	step1a(2, 0) = "ss"
	step1a(2, 1) = "ss"
	step1a(3, 0) = "s"
	step1a(3, 1) = ""
	For i = 0 To 3 Step 1
		If porterEndsWith(str, step1a(i, 0)) Then
			str = porterTrimEnd(str, Len(step1a(i, 0)))
			str = porterAppendEnd(str, step1a(i, 1))
			Exit For
		End If
	Next
	Dim m
	Dim temp
	Dim second_third_success
	second_third_success = False
	'(m>0) EED -> EE..else..(*v*) ED  ->(*v*) ING  ->
	If porterEndsWith(str, "eed") Then
		'counting the number of m's
		temp = porterTrimEnd(str, Len("eed"))
		m = porterCountm(temp)

		If m > 0 Then
				str = porterTrimEnd(str, Len("eed"))
				str = porterAppendEnd(str, "ee")
		End If
	ElseIf porterEndsWith(str, "ed") Then
		'trim and check for vowel
		temp = porterTrimEnd(str, Len("ed"))
		If porterContainsVowel(temp) Then
			str = porterTrimEnd(str, Len("ed"))
			second_third_success = True
		End If
	ElseIf porterEndsWith(str, "ing") Then
		'trim and check for vowel
		temp = porterTrimEnd(str, Len("ing"))
		If porterContainsVowel(temp) Then
			str = porterTrimEnd(str, Len("ing"))
			second_third_success = True
		End If
	End If

	If second_third_success = True Then             'If the second or third of the rules in Step 1b is SUCCESSFUL
		If porterEndsWith(str, "at") Then           'AT -> ATE
			str = porterTrimEnd(str, Len("at"))
			str = porterAppendEnd(str, "ate")
		ElseIf porterEndsWith(str, "bl") Then       'BL -> BLE
			str = porterTrimEnd(str, Len("bl"))
			str = porterAppendEnd(str, "ble")
		ElseIf porterEndsWith(str, "iz") Then       'IZ -> IZE
			str = porterTrimEnd(str, Len("iz"))
			str = porterAppendEnd(str, "ize")
		ElseIf porterEndsDoubleConsonent(str) Then  '(*d and not (*L or *S or *Z))-> single letter
			If Not (porterEndsWith(str, "l") Or porterEndsWith(str, "s") Or porterEndsWith(str, "z")) Then
				str = porterTrimEnd(str, 1)
			End If
		ElseIf porterCountm(str) = 1 Then                           '(m=1 and *o) -> E
			If porterEndsCVC(str) Then
				str = porterAppendEnd(str, "e")
			End If
		End If
	End If

	If porterEndsWith(str, "y") Then
		'trim and check for vowel
		temp = porterTrimEnd(str, 1)

		If porterContainsVowel(temp) Then
			str = porterTrimEnd(str, Len("y"))
			str = porterAppendEnd(str, "i")
		End If
	End If

	porterAlgorithmStep1 = str
End Function

Function porterAlgorithmStep2(str)
	Dim step2(20, 1)
	Dim i
	Dim temp

	step2(0, 0) = "ational"
	step2(0, 1) = "ate"
	step2(1, 0) = "tional"
	step2(1, 1) = "tion"
	step2(2, 0) = "enci"
	step2(2, 1) = "ence"
	step2(3, 0) = "anci"
	step2(3, 1) = "ance"
	step2(4, 0) = "izer"
	step2(4, 1) = "ize"
	step2(5, 0) = "bli"
	step2(5, 1) = "ble"
	step2(6, 0) = "alli"
	step2(6, 1) = "al"
	step2(7, 0) = "entli"
	step2(7, 1) = "ent"
	step2(8, 0) = "eli"
	step2(8, 1) = "e"
	step2(9, 0) = "ousli"
	step2(9, 1) = "ous"
	step2(10, 0) = "ization"
	step2(10, 1) = "ize"
	step2(11, 0) = "ation"
	step2(11, 1) = "ate"
	step2(12, 0) = "ator"
	step2(12, 1) = "ate"
	step2(13, 0) = "alism"
	step2(13, 1) = "al"
	step2(14, 0) = "iveness"
	step2(14, 1) = "ive"
	step2(15, 0) = "fulness"
	step2(15, 1) = "ful"
	step2(16, 0) = "ousness"
	step2(16, 1) = "ous"
	step2(17, 0) = "aliti"
	step2(17, 1) = "al"
	step2(18, 0) = "iviti"
	step2(18, 1) = "ive"
	step2(19, 0) = "biliti"
	step2(19, 1) = "ble"
	step2(20, 0) = "logi"
	step2(20, 1) = "log"

	For i = 0 To 20 Step 1
		If porterEndsWith(str, step2(i, 0)) Then
				temp = porterTrimEnd(str, Len(step2(i, 0)))
				If porterCountm(temp) > 0 Then
					str = porterTrimEnd(str, Len(step2(i, 0)))
					str = porterAppendEnd(str, step2(i, 1))
				End If
				Exit For
		End If
	Next
	porterAlgorithmStep2 = str
End Function

Function porterAlgorithmStep3(str)
	Dim i
	Dim temp
	Dim step3(6, 1)

	step3(0, 0) = "icate"
	step3(0, 1) = "ic"
	step3(1, 0) = "ative"
	step3(1, 1) = ""
	step3(2, 0) = "alize"
	step3(2, 1) = "al"
	step3(3, 0) = "iciti"
	step3(3, 1) = "ic"
	step3(4, 0) = "ical"
	step3(4, 1) = "ic"
	step3(5, 0) = "ful"
	step3(5, 1) = ""
	step3(6, 0) = "ness"
	step3(6, 1) = ""

	For i = 0 To 6 Step 1
		If porterEndsWith(str, step3(i, 0)) Then
				temp = porterTrimEnd(str, Len(step3(i, 0)))
				If porterCountm(temp) > 0 Then
					str = porterTrimEnd(str, Len(step3(i, 0)))
					str = porterAppendEnd(str, step3(i, 1))
				End If
				Exit For
		End If
	Next

	porterAlgorithmStep3 = str
End Function

Function porterAlgorithmStep4(str)
	'declaring local variables
	Dim i
	Dim temp
	Dim step4(18)

	'initializing contents of 2D array
	step4(0) = "al"
	step4(1) = "ance"
	step4(2) = "ence"
	step4(3) = "er"
	step4(4) = "ic"
	step4(5) = "able"
	step4(6) = "ible"
	step4(7) = "ant"
	step4(8) = "ement"
	step4(9) = "ment"
	step4(10) = "ent"
	step4(11) = "ion"
	step4(12) = "ou"
	step4(13) = "ism"
	step4(14) = "ate"
	step4(15) = "iti"
	step4(16) = "ous"
	step4(17) = "ive"
	step4(18) = "ize"

	'checking word
	For i = 0 To 18 Step 1
		If porterEndsWith(str, step4(i)) Then
			temp = porterTrimEnd(str, Len(step4(i)))
			If porterCountm(temp) > 1 Then
				If porterEndsWith(str, "ion") Then
					If porterEndsWith(temp, "s") Or porterEndsWith(temp, "t") Then
						str = porterTrimEnd(str, Len(step4(i)))
						str = porterAppendEnd(str, "")
					End If
				Else
					str = porterTrimEnd(str, Len(step4(i)))
					str = porterAppendEnd(str, "")
				End If
			End If
			Exit For
		End If
	Next
	'retuning the word
	porterAlgorithmStep4 = str
End Function

 Function porterAlgorithmStep5(str)
	Dim i
	Dim temp
	If porterEndsWith(str, "e") Then            'word ends with e
		temp = porterTrimEnd(str, 1)
		If porterCountm(temp) > 1 Then          'm>1
			str = porterTrimEnd(str, 1)
		ElseIf porterCountm(temp) = 1 Then      'm=1
			If Not porterEndsCVC(temp) Then     'not *o
				str = porterTrimEnd(str, 1)
			End If
		End If
	End If
	If porterCountm(str) > 1 Then
		If porterEndsDoubleConsonent(str) And porterEndsWith(str, "l") Then
			str = porterTrimEnd(str, 1)
		End If
	End If
	'retuning the word
	porterAlgorithmStep5 = str
End Function

Function porterEndsWith(str, ends)
	Dim length_str
	Dim length_ends
	Dim hold_ends

	'finding the length of the string
	length_str = Len(str)
	length_ends = Len(ends)

	'if length of str is greater than the length of length_ends, only then proceed..else return false
	If length_ends >= length_str Then
		porterEndsWith = False
	Else
		'extract characters from right of str
		hold_ends = Right(str, length_ends)

		'comparing to see whether hold_ends=ends
		If StrComp(hold_ends, ends) = 0 Then
			porterEndsWith = True
		Else
			porterEndsWith = False
		End If
	End If
End Function

Function porterContains(str, present)
	If InStr(str, present) = 0 Then
		porterContains = False
	Else
		porterContains = True
	End If
End Function

Function porterContainsVowel(str)
	Dim i
	Dim pattern
	If Len(str) >= 0 Then
		'find out the CVC pattern
		pattern = returnCVCpattern(str)
		'check to see if the return pattern contains a vowel
		If InStr(pattern, "v") = 0 Then
			porterContainsVowel = False
		Else
			porterContainsVowel = True
		End If
	Else
		porterContainsVowel = False
	End If
End Function

Function porterEndsDoubleConsonent(str)
	Dim holds_ends
	Dim hold_third_last
	'first check whether the size of the word is >= 2
	If Len(str) >= 2 Then
		'extract 2 characters from right of str
		holds_ends = Right(str, 2)
		'checking if both the characters are same
		If Mid(holds_ends, 1, 1) = Mid(holds_ends, 2, 1) then
			'check for double consonent
			If holds_ends = "aa" Or holds_ends = "ee" Or holds_ends = "ii" Or holds_ends = "oo" Or holds_ends = "uu" Then
				porterEndsDoubleConsonent = False
			Else
				'if the second last character is y, and there are atleast three letters in str
				If holds_ends = "yy" And Len(str) > 2 Then
					'extracting the third last character
					hold_third_last = Right(str, 3)
					hold_third_last = Left(str, 1)
					If Not (hold_third_last = "a" Or hold_third_last = "e" Or hold_third_last = "i" Or hold_third_last = "o" Or hold_third_last = "u") Then
						porterEndsDoubleConsonent = False
					Else
						porterEndsDoubleConsonent = True
					End If
				Else
					porterEndsDoubleConsonent = True
				End If
			End If
		Else
			porterEndsDoubleConsonent = False
		End If
	Else
		porterEndsDoubleConsonent = False
	End If
End Function

Function porterEndsCVC(str)
	Dim const_vowel
	Dim i
	Dim pattern
	Dim lastchar
	'check to see if atleast 3 characters are present
	If Len(str) >= 3 Then
		'find out the CVC pattern
		pattern = returnCVCpattern(str)
		'we need to check only the last three characters
		pattern = Right(pattern, 3)
		lastchar = Mid(str, Len(str))
		'check to see if the letters in str match the sequence cvc
		If pattern = "cvc" Then
			If Not (lastchar = "w" Or lastchar = "x" Or lastchar = "y") Then
				porterEndsCVC = True
			Else
				porterEndsCVC = False
			End If
		Else
			porterEndsCVC = False
		End If
	Else
		porterEndsCVC = False
	End If
End Function

Function porterTrimEnd(str, length)
	'returning the trimmed string
	porterTrimEnd = Left(str, Len(str) - length)
End Function

Function porterAppendEnd(str, ends)
	'returning the appended string
	porterAppendEnd = str + ends
End Function

Function porterCountm(str)
	Dim const_vowel
	Dim i
	Dim m
	Dim flag
	Dim pattern
	Dim patlen
	Dim ch
	const_vowel = ""
	m = 0
	flag = False
	If Not Len(str) = 0 Then
		'find out the CVC pattern
		pattern = returnCVCpattern(str)
		patlen = Len(pattern)
		'counting the number of m's...
		For i = 0 To patlen-1 Step 1
			ch = Mid(pattern, i+1, 1)
			If ch = "v" Or flag = True Then
				flag = True
				If ch = "c" Then
					m = m + 1
					flag = False
				End If
			End If
		Next
	End If
	porterCountm = m
End Function

Function returnCVCpattern(str)
	Dim const_vowel
	Dim i
	Dim ch, last_char
	Dim strlen
	strlen = Len(str)
	'checking each character to see if it is a consonent or a vowel. also inputs the information in const_vowel
	For i = 0 To strlen-1 Step 1
		ch = Mid(str, i+1, 1)
		If ch = "a" Or ch = "e" Or ch = "i" Or ch = "o" Or ch = "u" Then
			const_vowel = const_vowel + "v"
		ElseIf ch = "y" Then
			'if y is not the first character, only then check the previous character
			If i > 0 Then
				last_char = Mid(str, i, 1)
				'check to see if previous character is a consonent
				If Not (last_char = "a" Or last_char = "e" Or last_char = "i" Or last_char = "o" Or last_char = "u") Then
					const_vowel = const_vowel + "v"
				Else
					const_vowel = const_vowel + "c"
				End If
			Else
				const_vowel = const_vowel + "c"
			End If
		Else
			const_vowel = const_vowel + "c"
		End If
	Next
	returnCVCpattern = const_vowel
End Function

%>
