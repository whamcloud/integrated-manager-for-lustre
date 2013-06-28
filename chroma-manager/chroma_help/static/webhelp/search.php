<?php
// ----------------------------------------------------------------------------
// Zoom Search Engine 6.0 (23/Dec/2011)
// PHP search script
// A fast custom website search engine using pre-indexed data files.
// Copyright (C) Wrensoft 2000 - 2011
//
// This script is designed for PHP 4.2+ only.
//
// NOTE: YOU SHOULD NOT NEED TO MODIFY THIS SCRIPT. If you wish to customize
// the appearance of the search page, you should change the contents of the
// "search_template.html" file. See chapter 6 of the Users Guide for more
// details: http://www.wrensoft.com/zoom/usersguide.html
// 
// IF YOU NEED TO ADD PHP TO THE SEARCH PAGE, see this FAQ:
// http://www.wrensoft.com/zoom/support/faq_ssi.html
//
// zoom@wrensoft.com
// http://www.wrensoft.com
// ----------------------------------------------------------------------------

if(strcmp('4.2.0', phpversion()) > 0)
	die("This version of the Zoom search script requires PHP 4.2.0 or higher.<br />You are currently using: PHP " . phpversion() . "<br />");
	
if ((version_compare(PHP_VERSION, '5.3.5') > 0 && version_compare(PHP_VERSION, '5.3.5') < 0) ||
	(version_compare(PHP_VERSION, '5.2.17') < 0))
{
	// Protection from floating point bug in PHP engine
	if (strpos(str_replace('.', '', serialize($_REQUEST)), '22250738585072011') !== false)
	{
		header('Status: 422 Unprocessable Entity');
		die();
	}
}

$SETTINGSFILE = dirname(__FILE__)."/settings.php";
$WORDMAPFILE = dirname(__FILE__)."/zoom_wordmap.zdat";
$DICTIONARYFILE = dirname(__FILE__)."/zoom_dictionary.zdat";
$PAGEDATAFILE = dirname(__FILE__)."/zoom_pagedata.zdat";
$SPELLINGFILE = dirname(__FILE__)."/zoom_spelling.zdat";
$PAGETEXTFILE = dirname(__FILE__)."/zoom_pagetext.zdat";
$PAGEINFOFILE = dirname(__FILE__)."/zoom_pageinfo.zdat";
$RECOMMENDEDFILE = dirname(__FILE__)."/zoom_recommended.zdat";

// Check for dependent files
if (!file_exists($SETTINGSFILE) || !file_exists($WORDMAPFILE) || !file_exists($DICTIONARYFILE))
{
	print("<b>Zoom files missing error:</b> Zoom is missing one or more of the required index data files.<br />Please make sure the generated index files are uploaded to the same path as this search script.<br />");
	return;
}

require($SETTINGSFILE);

if ($Spelling == 1 && !file_exists($SPELLINGFILE))
	print("<b>Zoom files missing error:</b> Zoom is missing the 'zoom_spelling.zdat' file required for the Spelling Suggestion feature which has been enabled.<br />");

// ----------------------------------------------------------------------------
// Settings
// ----------------------------------------------------------------------------

// The options available in the dropdown menu for number of results
// per page
$PerPageOptions = array(10, 20, 50, 100);

/*
// For foreign language support, setlocale may be required on the server for
// wildcards and highlighting to work. Uncomment the following lines and specify
// the appropriate locale information
//if (setlocale(LC_ALL, "ru_RU.cp1251") == false) // for russian
//  print("Failed to change locale setting or locale setting invalid");
*/

// Index format information
$PAGEDATA_URL = 0;
$PAGEDATA_TITLE = 1;
$PAGEDATA_DESC = 2;
$PAGEDATA_IMG = 3;

$MaxPageDataLineLen = 5178;

$METAFIELD_TYPE = 0;
$METAFIELD_NAME = 1;
$METAFIELD_SHOW = 2;
$METAFIELD_FORM = 3;
$METAFIELD_METHOD = 4;
$METAFIELD_DROPDOWN = 5;

$METAFIELD_TYPE_NUMERIC = 0;
$METAFIELD_TYPE_TEXT = 1;
$METAFIELD_TYPE_DROPDOWN = 2;
$METAFIELD_TYPE_MULTI = 3;
$METAFIELD_TYPE_MONEY = 4;

$METAFIELD_METHOD_EXACT = 0;
$METAFIELD_METHOD_LESSTHAN = 1;
$METAFIELD_METHOD_LESSTHANORE = 2;
$METAFIELD_METHOD_GREATERTHAN = 3;
$METAFIELD_METHOD_GREATERTHANORE = 4;
$METAFIELD_METHOD_SUBSTRING = 5;

$METAFIELD_NOVALUE_MARKER = 4294967295;


// ----------------------------------------------------------------------------
// Parameter initialisation
// ----------------------------------------------------------------------------

// Send HTTP header to define meta charset
if (isset($Charset) && $NoCharset == 0)
	header("Content-Type: text/html; charset=" . $Charset);

// For versions of PHP before 4.1.0
// we will emulate the superglobals by creating references
// NOTE: references created are NOT superglobals
if (!isset($_SERVER) && isset($HTTP_SERVER_VARS))
	$_SERVER = &$HTTP_SERVER_VARS;
if (!isset($_GET) && isset($HTTP_GET_VARS))
	$_GET = &$HTTP_GET_VARS;
if (!isset($_POST) && isset($HTTP_POST_VARS))
	$_POST = &$HTTP_POST_VARS;

// fix get/post variables if magic quotes are enabled
if (get_magic_quotes_gpc() == 1)
{
	if (isset($_GET))
		while (list($key, $value) = each($_GET))
		{
			if (!is_array($value))
				$_GET["$key"] = stripslashes($value);
		}
	if (isset($_POST))
		while (list($key, $value) = each($_POST))
			$_POST["$key"] = stripslashes($value);
}

// check magic_quotes for runtime stuff (reading from files, etc)
if (get_magic_quotes_runtime() == 1)
	set_magic_quotes_runtime(0);

// we use the method=GET and 'query' parameter now (for sub-result pages etc)
$IsZoomQuery = 0;
if (isset($_GET['zoom_query']))
{
	$query = $_GET['zoom_query'];
	$IsZoomQuery = 1;
}
else
	$query = "";

// number of results per page, defaults to 10 if not specified
if (isset($_GET['zoom_per_page']))
{
	$per_page = intval($_GET['zoom_per_page']);
	if ($per_page < 1)
		$per_page = 1;
}
else
	$per_page = 10;

// current result page number, defaults to the first page if not specified
$NewSearch = 0;
if (isset($_GET['zoom_page']))
{
	$page = intval($_GET['zoom_page']);
	if ($page < 1)
		$page = 1;
}
else
{
	$page = 1;
	$NewSearch = 1;
}

// AND operator.
// 1 if we are searching for ALL terms
// 0 if we are searching for ANY terms (default)
if (isset($_GET['zoom_and']))
	$and = intval($_GET['zoom_and']);
elseif (isset($DefaultToAnd) && $DefaultToAnd == 1)
	$and = 1;
else
	$and = 0;

// for category support
if ($UseCats == 1)
{
	if (isset($_GET['zoom_cat']))
	{
		if (is_array($_GET['zoom_cat']))
			$cat = $_GET['zoom_cat'];
		else
			$cat = array($_GET['zoom_cat']);
		$cat = array_filter($cat, "is_numeric");
	}
	else
		$cat = array(-1);  // default to search all categories

	$num_zoom_cats = count($cat);
	if ($num_zoom_cats == 0)
		$cat = array(-1);  // default to search all categories
}

// for sorting options
// zero is default (relevance)
// 1 is sort by date (if Date/Time is available)
if (isset($_GET['zoom_sort']))
	$sort = intval($_GET['zoom_sort']);
else
	$sort = 0;

$LinkBackJoinChar = "?";
if (isset($LinkBackURL) == false || strlen($LinkBackURL) < 1)
	$SelfURL = htmlspecialchars($_SERVER['PHP_SELF']);
else
{
	$SelfURL = $LinkBackURL;
}

if (strchr($SelfURL, '?'))
	$LinkBackJoinChar = "&amp;";

// init. link target string
$zoom_target = "";
if ($UseLinkTarget == 1 && isset($LinkTarget))
	$zoom_target = " target=\"" . $LinkTarget . "\" ";

$UseMBFunctions = 0;
if ($UseUTF8 == 1)
{
	if (function_exists('mb_strtolower'))
		$UseMBFunctions = 1;
}

if ($UseStemming == 1)
{
	$porterStemmer = new PorterStemmer();
}	

// ----------------------------------------------------------------------------
// Template buffers
// ----------------------------------------------------------------------------

// defines for output elements
$OUTPUT_FORM_START = 0;
$OUTPUT_FORM_END = 1;
$OUTPUT_FORM_SEARCHBOX = 2;
$OUTPUT_FORM_SEARCHBUTTON = 3;
$OUTPUT_FORM_RESULTSPERPAGE = 4;
$OUTPUT_FORM_MATCH = 5;
$OUTPUT_FORM_CATEGORIES = 6;
$OUTPUT_FORM_CUSTOMMETA = 7;

$OUTPUT_HEADING = 8;
$OUTPUT_SUMMARY = 9;
$OUTPUT_SUGGESTION = 10;
$OUTPUT_PAGESCOUNT = 11;
$OUTPUT_SORTING = 12;
$OUTPUT_SEARCHTIME = 13;
$OUTPUT_RECOMMENDED = 14;
$OUTPUT_PAGENUMBERS = 15;
$OUTPUT_CATSUMMARY = 16;

$OUTPUT_TAG_COUNT = 17;

$OutputBuffers = array_fill(0, $OUTPUT_TAG_COUNT, "");
$OutputResultsBuffer = "";

$TemplateShowTags = array(
"<!--ZOOM_SHOW_FORMSTART-->",
"<!--ZOOM_SHOW_FORMEND-->",
"<!--ZOOM_SHOW_SEARCHBOX-->",
"<!--ZOOM_SHOW_SEARCHBUTTON-->",
"<!--ZOOM_SHOW_RESULTSPERPAGE-->",
"<!--ZOOM_SHOW_MATCHOPTIONS-->",
"<!--ZOOM_SHOW_CATEGORIES-->",
"<!--ZOOM_SHOW_CUSTOMMETAOPTIONS-->",
"<!--ZOOM_SHOW_HEADING-->",
"<!--ZOOM_SHOW_SUMMARY-->",
"<!--ZOOM_SHOW_SUGGESTION-->",
"<!--ZOOM_SHOW_PAGESCOUNT-->",
"<!--ZOOM_SHOW_SORTING-->",
"<!--ZOOM_SHOW_SEARCHTIME-->",
"<!--ZOOM_SHOW_RECOMMENDED-->",
"<!--ZOOM_SHOW_PAGENUMBERS-->",
"<!--ZOOM_SHOW_CATSUMMARY-->"
);

$TemplateDefaultTag = "<!--ZOOMSEARCH-->";
$TemplateDefaultTagLen = strlen($TemplateDefaultTag);
$TemplateSearchFormTag = "<!--ZOOM_SHOW_SEARCHFORM-->";
$TemplateSearchFormTagLen = strlen($TemplateSearchFormTag);
$TemplateResultsTag = "<!--ZOOM_SHOW_RESULTS-->";
$TemplateResultsTagLen = strlen($TemplateResultsTag);
$TemplateQueryTag = "<!--ZOOM_SHOW_QUERY-->";
$TemplateQueryTagLen = strlen($TemplateQueryTag);

$OutputBuffers[$OUTPUT_FORM_START] = "<form method=\"get\" action=\"".$SelfURL."\" class=\"zoom_searchform\">";
$OutputBuffers[$OUTPUT_FORM_END] = "</form>";

// Indexes for dict structure
$DICT_WORD = 0;
$DICT_PTR = 1;
$DICT_VARCOUNT = 2;
$DICT_VARIANTS = 3;

// ----------------------------------------------------------------------------
// Functions
// ----------------------------------------------------------------------------
function ShowDefaultForm()
{
	global $OutputBuffers;
	global $OUTPUT_FORM_SEARCHBOX, $OUTPUT_FORM_SEARCHBUTTON, $OUTPUT_FORM_RESULTSPERPAGE;
	global $OUTPUT_FORM_MATCH, $OUTPUT_FORM_CATEGORIES, $OUTPUT_FORM_CUSTOMMETA;
	global $OUTPUT_FORM_START, $OUTPUT_FORM_END;

	print($OutputBuffers[$OUTPUT_FORM_START]);
	print($OutputBuffers[$OUTPUT_FORM_SEARCHBOX]);
	print($OutputBuffers[$OUTPUT_FORM_SEARCHBUTTON]);
	print($OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE]);
	print($OutputBuffers[$OUTPUT_FORM_MATCH]);
	print($OutputBuffers[$OUTPUT_FORM_CATEGORIES]);
	print($OutputBuffers[$OUTPUT_FORM_CUSTOMMETA]);
	print($OutputBuffers[$OUTPUT_FORM_END]);
}

function ShowDefaultSearchPage()
{
	global $OutputResultsBuffer;
	global $OutputBuffers;
	global $OUTPUT_HEADING, $OUTPUT_SUMMARY, $OUTPUT_SUGGESTION, $OUTPUT_PAGESCOUNT;
	global $OUTPUT_RECOMMENDED, $OUTPUT_SORTING, $OUTPUT_PAGENUMBERS, $OUTPUT_SEARCHTIME;
	global $OUTPUT_CATSUMMARY;

	ShowDefaultForm();
	// now show the default results layout
	print($OutputBuffers[$OUTPUT_HEADING]);
	print($OutputBuffers[$OUTPUT_SUMMARY]);
	print($OutputBuffers[$OUTPUT_CATSUMMARY]);
	print($OutputBuffers[$OUTPUT_SUGGESTION]);
	print($OutputBuffers[$OUTPUT_PAGESCOUNT]);
	print($OutputBuffers[$OUTPUT_RECOMMENDED]);
	print($OutputBuffers[$OUTPUT_SORTING]);
	print($OutputResultsBuffer);
	print($OutputBuffers[$OUTPUT_PAGENUMBERS]);
	print($OutputBuffers[$OUTPUT_SEARCHTIME]);
}


function ShowTemplate()
{
	global $ZoomInfo;
	global $OutputBuffers;
	global $TemplateShowTags;
	global $OUTPUT_TAG_COUNT;
	global $TemplateSearchFormTag, $TemplateSearchFormTagLen;
	global $TemplateDefaultTag, $TemplateDefaultTagLen;
	global $TemplateResultsTag, $TemplateResultsTagLen;
	global $OutputResultsBuffer;
	global $TemplateQueryTag, $TemplateQueryTagLen, $queryForHTML;

	// DO NOT MODIFY THE TEMPLATE FILENAME BELOW:
	$TemplateFilename = "search_template.html";
	// Note that there is no practical need to change the TemplateFilename. This file
	// is not visible to the end user. The search link on your website should point to
	// "search.php", and not the template file.
	//
	// Note also that you cannot change the filename to a PHP or ASP file.
	// The template file will only be treated as a static HTML page and changing the
	// extension will not alter this behaviour. Please see this FAQ support page
	// for a solution: http://www.wrensoft.com/zoom/support/faq_ssi.html

	//Open and print start of result page template
	$TemplateFilename = dirname(__FILE__) . "/" . $TemplateFilename;
	$template = file ($TemplateFilename);
	$numtlines = count($template); //Number of lines in the template
	$template_line = 0;
	$templatePtr = $template[$template_line];

	while ($template_line < $numtlines && $templatePtr != "")
	{
		$tagPos = strpos($templatePtr, "<!--ZOOM");
		if ($tagPos === FALSE)
			$tagPtr = "";
		else
		{
			if ($tagPos == 0)
				$tagPtr = $templatePtr;
			else
			{
				print(substr($templatePtr,0, $tagPos));
				$tagPtr = substr($templatePtr, $tagPos);
			}
		}

		if ($tagPtr == "")
		{
			print($templatePtr);
			$templatePtr = "";
		}
		else if (strncasecmp($tagPtr, $TemplateDefaultTag, $TemplateDefaultTagLen) == 0)
		{
			ShowDefaultSearchPage();
			$templatePtr = substr($tagPtr, $TemplateDefaultTagLen);
		}
		else if (strncasecmp($tagPtr, $TemplateSearchFormTag, $TemplateSearchFormTagLen) == 0)
		{
			ShowDefaultForm();
			$templatePtr = substr($tagPtr, $TemplateSearchFormTagLen);
		}
		else if (strncasecmp($tagPtr, $TemplateResultsTag, $TemplateResultsTagLen) == 0)
		{
			print($OutputResultsBuffer);
			$templatePtr = substr($tagPtr, $TemplateResultsTagLen);
		}
		else if (strncasecmp($tagPtr, $TemplateQueryTag, $TemplateQueryTagLen) == 0)
		{
			if (strlen($queryForHTML) > 0)
				print($queryForHTML);
			$templatePtr = substr($tagPtr, $TemplateQueryTagLen);
		}		
		else
		{
			for ($tagnum = 0; $tagnum < $OUTPUT_TAG_COUNT; $tagnum++)
			{
				$tagLen = strlen($TemplateShowTags[$tagnum]);
				if (strncasecmp($tagPtr, $TemplateShowTags[$tagnum], $tagLen) == 0)
				{
					print($OutputBuffers[$tagnum]);
					$templatePtr = substr($tagPtr, $tagLen);
					break;
				}
			}
			if ($tagnum == $OUTPUT_TAG_COUNT)
			{
				print($tagPtr);
				$templatePtr = "";
			}
		}

		if (strlen(trim($templatePtr)) == 0)
		{
			$template_line++;
			if ($template_line < $numtlines)
				$templatePtr = $template[$template_line];
		}
	}
}

function PrintHighlightDescription($line)
{
	global $Highlighting;
	global $HighlightColor;
	global $RegExpSearchWords;
	global $NumSearchWords;
	global $SearchAsSubstring;

	if ($Highlighting == 0)
	{
		return $line;
	}

	$res = $line;

	for ($i = 0; $i < $NumSearchWords; $i++)
	{
		if (strlen($RegExpSearchWords[$i]) < 1)
			continue;

		// replace with marker text, assumes [;:] and [:;] is not the search text...
		if ($SearchAsSubstring == 1)
			$res = preg_replace("/(" .$RegExpSearchWords[$i] . ")/i", "[;:]$1[:;]", $res);
		else
			$res = preg_replace("/(\W|\A|\b)(" .$RegExpSearchWords[$i] . ")(\W|\Z|\b)/i", "$1[;:]$2[:;]$3", $res);
	}
	// replace the marker text with the html text
	// this is to avoid finding previous <span>'ed text.
	$res = str_replace("[;:]", "<span class=\"highlight\">", $res);
	$res = str_replace("[:;]", "</span>", $res);
	return $res;
}


function GetDictionaryWord($word_id, $variant_index)
{
	global $dict, $DICT_VARIANTS, $DICT_WORD, $DICT_VARCOUNT;

	if ($variant_index > 0 && $variant_index <= $dict[$word_id][$DICT_VARCOUNT])
		return $dict[$word_id][$DICT_VARIANTS][$variant_index-1];
	else
		return $dict[$word_id][$DICT_WORD];
}

function GetSpellingWord($word_id)
{
	global $dict, $DICT_VARIANTS, $DICT_WORD, $DICT_VARCOUNT;

	if ($dict[$word_id][$DICT_VARCOUNT] > 0)
		return $dict[$word_id][$DICT_VARIANTS][0];
	else
		return $dict[$word_id][$DICT_WORD];
}


$HIGHLIGHT_NONE = 0;
$HIGHLIGHT_SINGLE = 1;
$HIGHLIGHT_START = 2;
$HIGHLIGHT_END = 3;

function HighlightContextArray($context_word_count)
{
	global $highlightArray;
	global $contextArray;
	global $NumSearchWords;
	global $SearchWords, $UseWildCards, $RegExpSearchWords;
	global $phrase_terms_ids, $search_terms_ids;
	global $HIGHLIGHT_NONE, $HIGHLIGHT_SINGLE, $HIGHLIGHT_START, $HIGHLIGHT_END;
	global $SearchAsSubstring, $DictReservedLimit;

	for ($i = 0; $i < $context_word_count; $i++)
	{
		if ($contextArray[$i] == 0)
			continue;

		$word_id = $contextArray[$i][0];
		$variant_index = $contextArray[$i][1];

		for ($sw = 0; $sw < $NumSearchWords; $sw++)
		{
			if (strpos($SearchWords[$sw], " ") !== false)
			{
				// this is an exact phrase and has its phrase terms stored in SearchPhrases[sw]
				$termNum = $i;
				$pterm = 0;
				while ($phrase_terms_ids[$sw][$pterm] != 0 && $termNum < $context_word_count)
				{
					// only compare this word in the context if it is NOT a punctuation word
					// or if it is the first word we are looking at in this phrase
					if ($termNum == $i || $contextArray[$termNum][0] > $DictReservedLimit)
					{
						if ($phrase_terms_ids[$sw][$pterm] != $contextArray[$termNum][0])
							break;	// we break out of looking at each term of the phrase if we don't match
						$pterm++;
					}
					$termNum++;
				}

				if ($pterm > 0 && $phrase_terms_ids[$sw][$pterm] == 0)
				{
					$highlightArray[$i] = $HIGHLIGHT_START;
					$highlightArray[$termNum-1] = $HIGHLIGHT_END;
				}
			}
			else
			{
				$res = 0;
				if ($UseWildCards[$sw] == 1)
				{
					$res = preg_match("/\A(".$RegExpSearchWords[$sw].")\Z/i", GetDictionaryWord($word_id, 0));
				}
				else
				{
					if ($search_terms_ids[$sw] == $word_id)
						$res = 1;
				}
				if ($res > 0)
				{
					if ($highlightArray[$i] == $HIGHLIGHT_NONE)
						$highlightArray[$i] = $HIGHLIGHT_SINGLE;
				}
			}
		}
	}
}

function PrintNumResults($num)
{
	global $STR_NO_RESULTS, $STR_RESULT, $STR_RESULTS;
	global $IsMaxLimitExceeded, $STR_MORETHAN;
	if ($num == 0)
		return $STR_NO_RESULTS;
	else if ($num == 1)
		return $num . " " . $STR_RESULT;
	else
	{
		if ($IsMaxLimitExceeded)
			return $STR_MORETHAN . " " . $num . " " . $STR_RESULTS;
		return $num . " " . $STR_RESULTS;
	}
}

function RecLinkAddParamToURL($url, $paramStr)
{
	// add GET parameters to URL depending on
	// whether there are any existing parameters
	if (strpos($url, "?") !== false)
		return $url . "&amp;" . $paramStr;
	else
	{				
		$hashPos = strpos($url, "#");
		if ($hashPos !== false)
			return substr($url, 0, $hashPos) . "?" . $paramStr . substr($url, $hashPos);
		else
			return $url . "?" . $paramStr;
	}
}

function AddParamToURL($url, $paramStr)
{
	// add GET parameters to URL depending on
	// whether there are any existing parameters
	// Note: we don't need to worry about hash anchors here like RecLinkAddParamToURL
	// because they are stripped for non-recommended link.
	if (strpos($url, "?") !== false)
		return $url . "&amp;" . $paramStr;
	else
		return $url . "?" . $paramStr;
}


// ----------------------------------------------------------------------------
// Compares the two values, used for sorting output results
// Results that match all search terms are put first, highest score
// ----------------------------------------------------------------------------
function SortCompare ($a, $b)
{
	if ($a[2] < $b[2])
		return 1;
	else
	if ($a[2] > $b[2])
		return -1;
	else
	{
		if ($a[1] < $b[1])
			return 1;
		else
		if ($a[1] > $b[1])
			return -1;
		else
			return 0;
	}
}

function SortByDate ($a, $b)
{
	global $pageinfo;
	if ($pageinfo[$a[0]]["datetime"] < $pageinfo[$b[0]]["datetime"])
		return 1;
	else
	if ($pageinfo[$a[0]]["datetime"] > $pageinfo[$b[0]]["datetime"])
		return -1;
	else
	{
		// if equal dates/time, return based on sw matched and score
		return SortCompare($a, $b);
	}
}

function sw_compare ($a, $b)
{
	if ($a[0] == '-')
		return 1;

	if ($b[0] == '-')
		return -1;

	return 0;
}


// ----------------------------------------------------------------------------
// Translates a typical shell wildcard pattern ("zoo*" => "zoom" etc.)
// to a regular expression pattern. Supports only '*' and '?' characters.
// ----------------------------------------------------------------------------
function pattern2regexp($pattern)
{
	$i = 0;
	$len = strlen($pattern);

	if (strpos($pattern, "$") !== false)
		str_replace($pattern, "$", "\$");
	if (strpos($pattern, "#") !== false)
		str_replace($pattern, "#", "\#");

	$res = "";

	while ($i < $len) {
		$c = $pattern[$i];
		if ($c == '*')
			$res = $res . "[\d\S]*";
		else
		if ($c == '?')
			$res = $res . ".";
		else
		if ($c == '.')
			$res = $res . "\.";
		else
			$res = $res . preg_quote($c, '/');
		$i++;
	}
	return $res;
}

function wordcasecmp($word1, $word2)
{
	global $UseUTF8;
	global $UseMBFunctions;
	global $ToLowerSearchWords;
	
	if ($ToLowerSearchWords == 0)
		return strcmp($word1, $word2);

	if ($UseUTF8 == 1 && $UseMBFunctions == 1)
	{
		// string length compare for speed reasons, only use mb_strtolower when absolutely necessary
		// assumes that the lowercase variant of multibyte characters are same length as their uppercase variant
		if (strlen($word1) == strlen($word2))
		{
			if (preg_match('/^[\x80-\xff]/', $word1) || preg_match('/^[\x80-\xff]/', $word2))
				return strcmp(mb_strtolower($word1, "UTF-8"), mb_strtolower($word2, "UTF-8"));
			else
				return strcasecmp($word1, $word2);
		}
		else
			return 1;
	}
	else
		return strcasecmp($word1, $word2);
}

function mystristr($word1, $word2)
{
	global $UseUTF8;
	global $UseMBFunctions;

	if ($UseUTF8 == 1 && $UseMBFunctions == 1)
	{
		if (preg_match('/^[\x80-\xff]/', $word1) || preg_match('/^[\x80-\xff]/', $word2))
			return strstr(mb_strtolower($word1, "UTF-8"), mb_strtolower($word2, "UTF-8"));
	}
	
	return stristr($word1, $word2);
}


// This function is unable to return any values larger than a signed int
// is capable of holding, due to PHP's bitwise operators only working
// with signed ints.
function GetBytes($binfile, $numbytes)
{
	global $METAFIELD_NOVALUE_MARKER;

	$ffcount = 0;
	$ret = 0;
	$bytes_buffer = fread($binfile, $numbytes);
	for ($k = 0; $k < $numbytes; $k++)
	{
		if ($bytes_buffer[$k] == chr(0xFF))
			$ffcount++;
		$ret = $ret | ord($bytes_buffer[$k])<<(8*$k);
	}
	if ($ffcount == $numbytes)
		$ret = (float) $METAFIELD_NOVALUE_MARKER;
	return $ret;
}

function GetDictID($word)
{
	global $dict;
	global $dict_count;
	for ($i = 0; $i < $dict_count; $i++) {
		if (wordcasecmp($dict[$i][0], $word) == 0)
			return $i;
	}
	return -1;  // not found
}

function GetNextDictWord($fp_pagetext)
{
	global $DictIDLen;
	$dict_id = 0;
	$variant_index = 0;

	$bytes_buffer = fread($fp_pagetext, $DictIDLen);
	if ($bytes_buffer != "")
	{
		for ($i = 0; $i < $DictIDLen-1; $i++)
		{
			$dict_id = $dict_id | ord($bytes_buffer[$i])<<(8*$i);
		}
		$variant_index = ord($bytes_buffer[$DictIDLen-1]);
	}
	else
	{
		$dict_id = 0;
		$variant_index = 0;
	}

	return array($dict_id,$variant_index);
}

function CheckBitInByteArray($bitnum, $byteArray)
{
	global $NumCatBytes;
	
	$bytenum = 0;
	$newBitnum = 0;
	
	$bytenum = ceil(($bitnum+1) / 8.0);

	if ($bytenum > 1)
	{
		$newBitnum = $bitnum - (($bytenum-1)*8);
		$bytenum = $bytenum - 1;
	}
	else
	{
		$newBitnum = $bitnum;
		$bytenum = 0;
	}

	if ($bytenum >= $NumCatBytes)
	{			
		exit("Error: Category number is invalid. Incorrect settings file used?");
	}

	return ($byteArray[$bytenum] & (1 << $newBitnum));
}

function SkipSearchWord($sw)
{
	global $SearchWords;
	global $SkippedWords;
	global $SkippedOutputStr;
	global $RegExpSearchWords;
	global $Highlighting;
	global $UseWildCards;
	if ($SearchWords[$sw] != "")
	{
		if ($SkippedWords > 0)
			$SkippedOutputStr .= ", ";
		$SkippedOutputStr .= "\"<b>" . $SearchWords[$sw] . "</b>\"";
		$SearchWords[$sw] = "";
		if ($Highlighting == 1 || $UseWildCards[$sw] == 1)
			$RegExpSearchWords[$sw] = "";
	}
	$SkippedWords++;
}

function GetSPCode($word)
{
	$Vowels = "AEIOU";
	$FrontV = "EIY";
	$VarSound = "CSPTG";
	$Dbl = ".";

	$metalen = 4;

	$tmpword = strtoupper($word);

	$wordlen = strlen($tmpword);
	if ($wordlen < 1)
		return "";

	// if ae, gn, kn, pn, wr then drop the first letter
	$strPtr = substr($tmpword, 0, 2);
	if ($strPtr == "AE" || $strPtr == "GN" || $strPtr == "KN" || $strPtr == "PN" || $strPtr == "WR")
		$tmpword = substr($tmpword, 1);

	// change x to s
	if ($tmpword{0} == "X")
		$tmpword = "S" . substr($tmpword, 1);

	// get rid of the 'h' in "wh"
	if (substr($tmpword, 0, 2) == "WH")
		$tmpword = "W" . substr($tmpword, 2);

	// update the word length
	$wordlen = strlen($tmpword);
	$lastChar = $wordlen-1;

	// remove an 's' from the end of the string
	if ($tmpword{$lastChar} == "S")
	{
		$tmpword = substr($tmpword, 0, $wordlen-1);
		$wordlen = strlen($tmpword);
		$lastChar = $wordlen-1;
	}

	$metaph = "";
	$Continue = false;

	for ($i = 0; strlen($metaph) < $metalen && $i < $wordlen; $i++)
	{
		$char = $tmpword{$i};
		$vowelBefore = false;
		$continue = false;
		if ($i > 0)
		{
			$prevChar = $tmpword{$i-1};
			if (strpos($Vowels, $prevChar) !== FALSE)
				$vowelBefore = true;
		}
		else
		{
			$prevChar = " ";
			if (strpos($Vowels, $char) !== FALSE)
			{
				$metaph  .= $tmpword{0};
				continue;
			}
		}

		$vowelAfter = false;
		$frontvAfter = false;
		$nextChar = " ";
		if ($i < $lastChar)
		{
			$nextChar = $tmpword{$i+1};
			if (strpos($Vowels, $nextChar) !== FALSE)
				$vowelAfter = true;
			if (strpos($FrontV, $nextChar) !== FALSE)
				$frontvAfter = true;
		}

		// skip double letters except ones in list
		if ($char == $nextChar && $nextChar != $Dbl)
			continue;

		$nextChar2 = " ";
		if ($i < ($lastChar-1))
			$nextChar2 = $tmpword{$i+2};

		$nextChar3 = " ";
		if ($i < ($lastChar-2))
			$nextChar3 = $tmpword{$i+3};

		switch ($char)
		{
		case "B":
			$silent = false;
			if ($i == $lastChar && $prevChar == "M")
				$silent = true;
			if ($silent == false)
				$metaph .= $char;
			break;
		case "C":
			if (!($i > 1 && $prevChar == "S" && $frontvAfter))
			{
				if ($i > 0 && $nextChar == "I" && $nextChar2 == "A")
					$metaph .= "X";
				elseif ($frontvAfter)
					$metaph .= "S";
				elseif ($i > 1 && $prevChar == "S" && $nextChar == "H")
					$metaph .= "K";
				elseif ($nextChar == "H")
				{
					if ($i == 0 && strpos($Vowels, $nextChar2) === FALSE)
						$metaph .= "K";
					else
						$metaph .= "X";
				}
				elseif ($prevChar == "C")
					$metaph .= "C";
				else
					$metaph .= "K";
			}
			break;
		case "D":
			if ($nextChar == "G" && strpos($FrontV, $nextChar2) !== FALSE)
				$metaph .= "J";
			else
				$metaph .= "T";
			break;
		case "G":
			$silent = false;
			if ( ($i < ($lastChar-1) && $nextChar == "H") &&
				 (strpos($Vowels, $nextChar2) == FALSE))
				 $silent = true;

			if ( ($i == ($lastChar-3)) && $nextChar == "N" && $nextChar == "E" && $nextChar == "D")
				$silent = true;
			elseif ( ($i == ($lastChar-1)) && $nextChar == "N")
				$silent = true;

			if ($prevChar == "D" && $frontvAfter)
				$silent = true;

			if ($prevChar == "G")
				$hard = true;
			else
				$hard = false;

			if (!$silent)
			{
				if ($frontvAfter && (!$hard))
					$metaph .= "J";
				else
					$metaph .= "K";
			}
			break;
		case "H":
			$silent = false;
			if (strpos($VarSound, $prevChar) !== FALSE)
				$silent = true;
			if ($vowelBefore && !$vowelAfter)
				$silent = true;
			if (!$silent)
				$metaph .= $char;
			break;
		case "F":
		case "J":
		case "L":
		case "M":
		case "N":
		case "R":
			$metaph .= $char;
			break;
		case "K":
			if ($prevChar != "C")
				$metaph .= $char;
			break;
		case "P":
			if ($nextChar == "H")
				$metaph .= "F";
			else
				$metaph .= "P";
			break;
		case "Q":
			$metaph .= "K";
			break;
		case "S":
			if ($i > 1 && $nextChar == "I" && ($nextChar2 == "O" || $nextChar2 == "A"))
				$metaph .= "X";
			elseif ($nextChar == "H")
				$metaph .= "X";
			else
				$metaph .= "S";
			break;
		case "T":
			if ($i > 1 && $nextChar == "I" && ($nextChar2 == "O" || $nextChar2 == "A"))
				$metaph .= "X";
			elseif ($nextChar == "H")
			{
				if ($i > 0 || (strpos($Vowels, $nextChar2) !== FALSE))
					$metaph .= "0";
				else
					$metaph .= "T";
			}
			elseif (!($i < ($lastChar-2) && $nextChar == "C" && $nextChar2 == "H"))
				$metaph .= "T";
			break;
		case "V":
			$metaph .= "F";
			break;
		case "W":
		case "Y":
			if ($i < $lastChar && $vowelAfter)
				$metaph .= $char;
			break;
		case "X":
			$metaph .= "KS";
			break;
		case "Z":
			$metaph .= "S";
			break;
		}
	}
	if (strlen($metaph) == 0)
		return "";
	return $metaph;
}

function GetPageData($index)
{
	global $fp_pagedata, $pageinfo, $MaxPageDataLineLen;
	fseek($fp_pagedata, intval($pageinfo[$index]["dataoffset"]));
	$pgdata = fgets($fp_pagedata, $MaxPageDataLineLen);
	return explode("|", $pgdata);
}

function QueryEntities($query)
{
	$query = str_replace("&", "&#38;", $query);
	$query = str_replace("<", "&#60;", $query);
	$query = str_replace(">", "&#62;", $query);
	return $query;
}

function uniord($u)
{
	$k = mb_convert_encoding($u, 'UCS-2LE', 'UTF-8');
	$k1 = ord(substr($k, 0, 1));
	$k2 = ord(substr($k, 1, 1));
	return $k2 * 256 + $k1;
}

function FixQueryForAsianWords($query)
{
	// check if the multibyte functions we need to use are available
	if (!function_exists('mb_convert_encoding') ||
		!function_exists('mb_strlen') ||
		!function_exists('mb_substr'))
		return $query;

	$currCharType = 0;
	$lastCharType = 0;	// 0 is normal, 1 is hiragana, 2 is katakana, 3 is "han"

	// check for hiragan/katakana splitting required
	$newquery = "";
	$query_len = mb_strlen($query, "UTF-8");
	for ($i = 0; $i < $query_len; $i++)
	{
		$ch = mb_substr($query, $i, 1, "UTF-8");
		$chVal = uniord($ch);

		if ($chVal >= 12352 && $chVal <= 12447)
			$currCharType = 1;
		else if ($chVal >= 12448 && $chVal <= 12543)
			$currCharType = 2;
		else if ($chVal >= 13312 && $chVal <= 44031)
			$currCharType = 3;
		else
			$currCharType = 0;

		if ($lastCharType != $currCharType && $ch != " ")
			$newquery .= " ";
		$lastCharType = $currCharType;
		$newquery .= $ch;
	}
	return $newquery;
}

// matches the recommended link word against the user search query
function RecLinkWordMatch($rec_word, $rec_idx)
{
	global $NumSearchWords, $queryForSearch, $queryForURL, $query, $num_rec_words;
	global $SearchWords, $UseWildCards, $SearchAsSubstring, $ToLowerSearchWords;
	global $OutputBuffers, $OUTPUT_RECOMMENDED;
	global $PAGEDATA_URL, $PAGEDATA_TITLE, $PAGEDATA_DESC, $PAGEDATA_IMG, $UseZoomImage;
	global $zoom_target, $GotoHighlight, $PdfHighlight;
	global $num_recs_found;
	global $STR_RECOMMENDED;

	$bRecLinkFound = false;

	for ($sw = 0; $sw <= $NumSearchWords; $sw++)
	{
		// if finished with last search word, check the full search query
		$result = 1;
		if ($sw == $NumSearchWords)
			$result = wordcasecmp($queryForSearch, $rec_word);
		else if (strlen($SearchWords[$sw]) > 0)
		{
			if ($UseWildCards[$sw] == 1)
			{
				$pattern = "/";

				// match entire word
				if ($SearchAsSubstring == 0)
					$pattern = $pattern . "\A";

				$pattern = $pattern . $RegExpSearchWords[$sw];

				if ($SearchAsSubstring == 0)
					$pattern = $pattern . "\Z";

				if ($ToLowerSearchWords != 0)
					$pattern = $pattern . "/i";
				else
					$pattern = $pattern . "/";

				$result = !(preg_match($pattern, $rec_word));
			}
			else if ($SearchAsSubstring == 0)
			{
				$result = wordcasecmp($SearchWords[$sw], $rec_word);
			}
			else
			{
				if (mystristr($rec_word, $SearchWords[$sw]) == FALSE)
					$result = 1;    // not matched
				else
					$result = 0;    // matched
			}

			if ($result != 0)
			{
				// if not matched, we check if the word is a wildcard
				if (strpos($rec_word, "*") !== false || strpos($rec_word, "?") !== false)
				{
					$RecWordRegExp = "/\A" . pattern2regexp($rec_word) . "\Z/i";
					$result = !(preg_match($RecWordRegExp, $SearchWords[$sw]));
				}
			}
		}

		if ($result == 0)
		{
			$bRecLinkFound = true;
			if ($num_recs_found == 0)
			{
				$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommended\">\n";
				$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommended_heading\">$STR_RECOMMENDED</div>\n";
			}
			$pgdata = GetPageData($rec_idx);
			$url = $pgdata[$PAGEDATA_URL];
			$title = $pgdata[$PAGEDATA_TITLE];
			$description = $pgdata[$PAGEDATA_DESC];
			if ($UseZoomImage)
				$image = $pgdata[$PAGEDATA_IMG];

			$urlLink = $url;
			//$urlLink = rtrim($urls[$rec_idx]);

			if ($GotoHighlight == 1)
			{
				if ($SearchAsSubstring == 1)
					$urlLink = RecLinkAddParamToURL($urlLink, "zoom_highlightsub=".$queryForURL);
				else
					$urlLink = RecLinkAddParamToURL($urlLink, "zoom_highlight=".$queryForURL);
			}
			if ($PdfHighlight == 1)
			{
				if (stristr($urlLink, ".pdf") != FALSE)
					$urlLink = $urlLink."#search=&quot;".str_replace("\"", "", $query)."&quot;";
			}
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommend_block\">\n";
			if ($UseZoomImage)
			{
				if (strlen($image) > 0)
				{
					$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommend_image\">";
					$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<a href=\"".$urlLink."\"" . $zoom_target . "><img src=\"$image\" alt=\"\" class=\"recommend_image\"></a>";
					$OutputBuffers[$OUTPUT_RECOMMENDED] .= "</div>";
				}
			}
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommend_title\">";
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<a href=\"".$urlLink."\"" . $zoom_target . ">";
			if (strlen($title) > 1)
				$OutputBuffers[$OUTPUT_RECOMMENDED] .= PrintHighlightDescription($title);
			else
				$OutputBuffers[$OUTPUT_RECOMMENDED] .= PrintHighlightDescription($pgdata[$PAGEDATA_URL]);
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "</a></div>\n";
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommend_description\">";
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= PrintHighlightDescription($description);
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "</div>\n";
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "<div class=\"recommend_infoline\">$url</div>\n";
			$OutputBuffers[$OUTPUT_RECOMMENDED] .= "</div>";
			$num_recs_found++;
			break;
		}
	}
	return $bRecLinkFound;
}

// ----------------------------------------------------------------------------
// Starts here
// ----------------------------------------------------------------------------

$mtime = explode(" ", microtime());
$starttime = doubleval($mtime[1]) + doubleval($mtime[0]);

// Read in the metafields query
if ($UseMetaFields == 1)
{
	for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
	{
		if (isset($_GET[$metafields[$fieldnum][$METAFIELD_NAME]]))
		{
			$meta_query[$fieldnum] = $_GET[$metafields[$fieldnum][$METAFIELD_NAME]];

			if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
			{
				if (!is_array($meta_query[$fieldnum]))
					$meta_query[$fieldnum] = array($meta_query[$fieldnum]);
				$meta_query[$fieldnum] = array_filter($meta_query[$fieldnum], "is_numeric");
			}
			/*
			if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN)
			{
				$ddi = 0;
				foreach ($metafields[$fieldnum][$METAFIELD_DROPDOWN] as $ddv)
				{
					// replace the query value string with the numeric index for faster matching
					if (strcasecmp($meta_query[$fieldnum], $ddv) == 0)
						$meta_query[$fieldnum] = $ddi;
					$ddi++;
				}
			}
			*/
		}
		else
			$meta_query[$fieldnum] = "";
	}
}

$OutputResultsBuffer .= "<!--Zoom Search Engine ".$Version."-->\n";

// Replace the key text <!--ZOOMSEARCH--> with the following
if ($FormFormat > 0)
{
	// Insert the form
	$OutputBuffers[$OUTPUT_FORM_SEARCHBOX] = " <input type=\"text\" name=\"zoom_query\" size=\"50\" value=\"".htmlspecialchars($query)."\" id=\"zoom_searchbox\" class=\"zoom_searchbox\" />\n";
	$OutputBuffers[$OUTPUT_FORM_SEARCHBUTTON] = "<input type=\"submit\" value=\"" . $STR_FORM_SUBMIT_BUTTON . "\" class=\"zoom_button\" /><br />\n";
	if ($FormFormat == 2)
	{
		$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] = "<span class=\"zoom_results_per_page\">" . $STR_FORM_RESULTS_PER_PAGE . "\n";
		$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] .= "<select name=\"zoom_per_page\">\n";
		reset($PerPageOptions);
		foreach ($PerPageOptions as $ppo)
		{
			$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] .= "<option";
			if ($ppo == $per_page)
				$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] .= " selected=\"selected\"";
			$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] .= ">". $ppo ."</option>\n";
		}
		$OutputBuffers[$OUTPUT_FORM_RESULTSPERPAGE] .= "</select></span>\n";
		if ($UseCats)
		{
			$OutputBuffers[$OUTPUT_FORM_CATEGORIES] = "<span class=\"zoom_categories\">\n";
			$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= $STR_FORM_CATEGORY . " ";
			if ($SearchMultiCats)
			{
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<ul>\n";
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<li><input type=\"checkbox\" name=\"zoom_cat[]\" value=\"-1\"";
				if ($cat[0] == -1)
					$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= " checked=\"checked\"";
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= ">$STR_FORM_CATEGORY_ALL</input></li>\n";
				for ($i = 0; $i < $NumCats; $i++)
				{
					$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<li><input type=\"checkbox\" name=\"zoom_cat[]\" value=\"$i\"";
					if ($cat[0] != -1)
					{
						for ($catit = 0; $catit < $num_zoom_cats; $catit++)
						{
							if ($i == $cat[$catit])
							{
								$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= " checked=\"checked\"";
								break;
							}
						}
					}
					$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= ">$catnames[$i]</input></li>\n";
				}
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "</ul><br /><br />\n";
			}
			else
			{
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<select name=\"zoom_cat[]\">";
				// 'all cats option
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<option value=\"-1\">" . $STR_FORM_CATEGORY_ALL . "</option>";
				for($i = 0; $i < $NumCats; $i++) {
					$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "<option value=\"". $i . "\"";
					if ($i == $cat[0])
						$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= " selected=\"selected\"";
					$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= ">". $catnames[$i] . "</option>";
				}
				$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "</select>&nbsp;&nbsp;\n";
			}
			$OutputBuffers[$OUTPUT_FORM_CATEGORIES] .= "</span>\n";
		}
		if ($UseMetaFields)
		{
			$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] = "<span class=\"zoom_metaform\">\n";
			for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
			{
				if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_NUMERIC)
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= $metafields[$fieldnum][$METAFIELD_FORM] . ": <input type=\"text\" name=\"".$metafields[$fieldnum][$METAFIELD_NAME]."\" size=\"20\" value=\"".$meta_query[$fieldnum]."\" class=\"zoom_metaform_numeric\" />\n";
				else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN)
				{
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= $metafields[$fieldnum][$METAFIELD_FORM] . ": <select name=\"".$metafields[$fieldnum][$METAFIELD_NAME]."\" class=\"zoom_metaform_dropdown\">\n";
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "<option value=\"-1\">" . $STR_FORM_CATEGORY_ALL . "</option>";
					$ddi = 0;
					foreach ($metafields[$fieldnum][$METAFIELD_DROPDOWN] as $ddv)
					{
						$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "<option value=\"" . $ddi . "\"";
						if ($meta_query[$fieldnum] !== "" && $ddi == floatval($meta_query[$fieldnum]))
							$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= " selected=\"selected\"";
						$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= ">". $ddv ."</option>\n";
						$ddi++;
					}
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "</select>\n";
				}
				else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
				{
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= $metafields[$fieldnum][$METAFIELD_FORM] . ": <select multiple name=\"".$metafields[$fieldnum][$METAFIELD_NAME]."[]\" class=\"zoom_metaform_multi\">\n";
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "<option value=\"-1\">" . $STR_FORM_CATEGORY_ALL . "</option>";
					$ddi = 0;
					$num_multi_query = 0;
					if (is_array($meta_query[$fieldnum]))
						$num_multi_query = count($meta_query[$fieldnum]);
					foreach ($metafields[$fieldnum][$METAFIELD_DROPDOWN] as $ddv)
					{
						$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "<option value=\"" . $ddi . "\"";
						for ($mqi = 0; $mqi < $num_multi_query; $mqi++)
						{
							if ($ddi == intval($meta_query[$fieldnum][$mqi]))
								$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= " selected=\"selected\"";
						}
						$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= ">". $ddv ."</option>\n";
						$ddi++;
					}
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "</select>\n";
				}
				else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MONEY)
				{
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= $metafields[$fieldnum][$METAFIELD_FORM] . ": " . $MetaMoneyCurrency . "<input type=\"text\" name=\"".$metafields[$fieldnum][$METAFIELD_NAME]."\" size=\"7\" value=\"".$meta_query[$fieldnum]."\" class=\"zoom_metaform_money\" />\n";
				}
				else
					$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= $metafields[$fieldnum][$METAFIELD_FORM] . ": <input type=\"text\" name=\"".$metafields[$fieldnum][$METAFIELD_NAME]."\" size=\"20\" value=\"".$meta_query[$fieldnum]."\" class=\"zoom_metaform_text\" />\n";
			}
			$OutputBuffers[$OUTPUT_FORM_CUSTOMMETA] .= "</span>\n";
		}
		$OutputBuffers[$OUTPUT_FORM_MATCH] = "<span class=\"zoom_match\">" . $STR_FORM_MATCH . " \n";
		if ($and == 0) {
			$OutputBuffers[$OUTPUT_FORM_MATCH] .= "<input type=\"radio\" name=\"zoom_and\" value=\"0\" checked=\"checked\" />" .	 $STR_FORM_ANY_SEARCH_WORDS . "\n";
			$OutputBuffers[$OUTPUT_FORM_MATCH] .= "<input type=\"radio\" name=\"zoom_and\" value=\"1\" />" . $STR_FORM_ALL_SEARCH_WORDS . "\n";
		} else {
			$OutputBuffers[$OUTPUT_FORM_MATCH] .= "<input type=\"radio\" name=\"zoom_and\" value=\"0\" />" . $STR_FORM_ANY_SEARCH_WORDS . "\n";
			$OutputBuffers[$OUTPUT_FORM_MATCH] .= "<input type=\"radio\" name=\"zoom_and\" value=\"1\" checked=\"checked\" />" . $STR_FORM_ALL_SEARCH_WORDS . "\n";
		}
		$OutputBuffers[$OUTPUT_FORM_START] .= "<input type=\"hidden\" name=\"zoom_sort\" value=\"" . $sort . "\" />\n";
		$OutputBuffers[$OUTPUT_FORM_MATCH] .= "<br /></span>\n";
	}
	else
	{
		$OutputBuffers[$OUTPUT_FORM_START] .= "<input type=\"hidden\" name=\"zoom_per_page\" value=\"" . $per_page . "\" />\n";
		$OutputBuffers[$OUTPUT_FORM_START] .= "<input type=\"hidden\" name=\"zoom_and\" value=\"" . $and . "\" />\n";
		$OutputBuffers[$OUTPUT_FORM_START] .= "<input type=\"hidden\" name=\"zoom_sort\" value=\"" . $sort . "\" />\n";
	}
}

// Give up early if no search words provided
$IsEmptyMetaQuery = false;
if (empty($query))
{
	$NoSearch = false;
	if ($UseMetaFields == 1)
	{
		if ($IsZoomQuery == 1)
			$IsEmptyMetaQuery = true;
		else
			$NoSearch = true;
	}
	else
	{
		// only display 'no query' line if no form is shown
		if ($IsZoomQuery == 1)
		{
			$OutputBuffers[$OUTPUT_SUMMARY] .= "<div class=\"summary\">" . $STR_NO_QUERY . "</div>";
		}

		$NoSearch = true;
	}
	if ($NoSearch)
	{
		//Let others know about Zoom.
		if ($ZoomInfo == 1)
			$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<center><p class=\"zoom_advertising\"><small>" . $STR_POWEREDBY . " <a href=\"http://www.wrensoft.com/zoom/\" target=\"_blank\"><b>Zoom Search Engine</b></a></small></p></center>";

		ShowTemplate();
		return;
	}
}

// Load index data files (*.zdat) ---------------------------------------------


// Open pagetext file
if ($DisplayContext == 1 || $AllowExactPhrase == 1)
{
	$fp_pagetext = fopen($PAGETEXTFILE, "rb");
	$teststr = fgets($fp_pagetext, 8);
	if ($teststr[0] == "T" && $teststr[2] == "h" && $teststr[4] == "i" && $teststr[6] == "s")
	{
		$OutputResultsBuffer .= "<b>Zoom config error:</b> The zoom_pagetext.zdat file is not properly created for the search settings specified.<br />Please check that you have re-indexed your site with the search settings selected in the configuration window.<br />";
		fclose($fp_pagetext);
		return;
	}
}

// Open recommended link file
if ($Recommended == 1)
{
	$fp_rec = fopen($RECOMMENDEDFILE, "rt");
	$i = 0;
	while (!feof($fp_rec))
	{
		$recline = fgets($fp_rec, $MaxKeyWordLineLen);
		if (strlen($recline) > 0)
		{
			$sep = strrpos($recline, " ");
			if ($sep !== false)
			{
				$rec[$i][0] = substr($recline, 0, $sep);
				$rec[$i][1] = substr($recline, $sep);
				$i++;
			}
		}
	}
	fclose($fp_rec);
	$rec_count = $i;
}

//Open pageinfo file
$fp_pageinfo = fopen($PAGEINFOFILE, "rb");
$pageinfo_count = $NumPages;
$rec_headersize = 2+5+4+4+1+1;
for ($i = 0; !feof($fp_pageinfo) && $i < $pageinfo_count; $i++)
{
	$bytes_buffer = fread($fp_pageinfo, $rec_headersize);
	$pageinfo[$i] = unpack("vrecsize/Vdataoffset/CextraByte/Vfilesize/Vdatetime/cboost/Clinkaction", $bytes_buffer);
	
	if ($UseCats == 1 && $NumCatBytes > 0)
	{
		$catpages[$i] = array();
		for ($byte = 0; $byte < $NumCatBytes; $byte++)
			$catpages[$i][$byte] = GetBytes($fp_pageinfo, 1);
	}

	if ($UseMetaFields == 1)
	{
		for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
		{
			if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_TEXT)
			{
				$valueSize = GetBytes($fp_pageinfo, 1);
				if ($valueSize > 0 && $valueSize != $METAFIELD_NOVALUE_MARKER)
					$metavalues[$i][$fieldnum] = fread($fp_pageinfo, $valueSize);
				else
					$metavalues[$i][$fieldnum] = "";
			}
			else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN)
			{
				// read in one byte
				$metavalues[$i][$fieldnum] = GetBytes($fp_pageinfo, 1);
			}
			else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
			{
				// read in one byte count then variable bytes
				$valueSize = GetBytes($fp_pageinfo, 1);
				if ($valueSize > 0 && $valueSize != $METAFIELD_NOVALUE_MARKER)
				{
					$tmpMultiValues = array($valueSize);
					for ($mvi = 0; $mvi < $valueSize; $mvi++)
						array_push($tmpMultiValues, GetBytes($fp_pageinfo, 1));
					$metavalues[$i][$fieldnum] = $tmpMultiValues;
				}
				else
					$metavalues[$i][$fieldnum] = $valueSize;// this will be METAFIELD_NOVALUE_MARKER
			}
			else
			{
				// numeric meta field type
				$metavalues[$i][$fieldnum] = (double)GetBytes($fp_pageinfo, 4);
			}
		}
	}
}

if ($Recommended == 1)
	$i += $rec_count;   // take into account the recommended links before verifying
if ($i < $NumPages)
{
	$OutputResultsBuffer .= ("<b>Zoom config error</b>: The zoom_pageinfo.zdat file is invalid or not up-to-date. Please make sure you have uploaded all files from the same indexing session.<br />");
	$UseDateTime = 0;
	$UseZoomImage = 0;
	$DisplayFilesize = 0;
}
fclose($fp_pageinfo);

// Open pagedata file
$fp_pagedata = fopen($PAGEDATAFILE, "rb");

// Open wordmap file
$fp_wordmap = fopen($WORDMAPFILE, "rb");

// Open dictionary file
$fp_dict = fopen($DICTIONARYFILE, "rb");
$i = 0;
while (!feof($fp_dict))
{
	$dictline = fgets($fp_dict, $MaxKeyWordLineLen);
	if (strlen($dictline) > 0)
	{
		$dict[$i] = explode(" ", $dictline, 3);
		if (isset($dict[$i][$DICT_VARCOUNT]))
		{
			if ($dict[$i][$DICT_VARCOUNT] > 0)
			{
				$variantsArray = array();
				// variants available
				for ($vi = 0; $vi < $dict[$i][$DICT_VARCOUNT]; $vi++)
				{
					$variantsArray[$vi] = rtrim(fgets($fp_dict, $MaxKeyWordLineLen));
				}
				$dict[$i][$DICT_VARIANTS] = $variantsArray;
			}
		}
		$i++;
	}
}
fclose($fp_dict);
$dict_count = $i;


// Prepare query for search ---------------------------------------------------

if ($MapAccents == 1) {
	$query = str_replace($AccentChars, $NormalChars, $query);
}

// Special query processing required when SearchAsSubstring is enabled
if ($SearchAsSubstring == 1 && $UseUTF8 == 1)
	$query = FixQueryForAsianWords($query);


// prepare search query, strip quotes, trim whitespace
if ($AllowExactPhrase == 0)
{
	$query = str_replace("\"", " ", $query);
}
if (strspn(".", $WordJoinChars) == 0)
	$query = str_replace(".", " ", $query);

if (strspn("-", $WordJoinChars) == 0)
	$query = preg_replace("/(\S)-/", "$1 ", $query);

if (strspn("#", $WordJoinChars) == 0)
	$query = preg_replace("/#(\S)/", " $1", $query);

if (strspn("+", $WordJoinChars) == 0)
{
	$query = preg_replace("/[\+]+([^\+\s])/", " $1", $query);
	$query = preg_replace("/([^\+\s])\+\s/", "$1 ", $query);
	$query = preg_replace("/\s\+\s/", " ", $query);
}

if (strspn("_", $WordJoinChars) == 0)
	$query = str_replace("_", " ", $query);

if (strspn("'", $WordJoinChars) == 0)
	$query = str_replace("'", " ", $query);

if (strspn("$", $WordJoinChars) == 0)
	$query = str_replace("$", " ", $query);

if (strspn(",", $WordJoinChars) == 0)
	$query = str_replace(",", " ", $query);

if (strspn(":", $WordJoinChars) == 0)
	$query = str_replace(":", " ", $query);

if (strspn("&", $WordJoinChars) == 0)
	$query = str_replace("&", " ", $query);

if (strspn("/", $WordJoinChars) == 0)
	$query = str_replace("/", " ", $query);

if (strspn("\\", $WordJoinChars) == 0)
	$query = str_replace("\\", " ", $query);

// strip consecutive spaces, parenthesis, etc.
// also strip any of the wordjoinchars if followed immediately by a space
$query = preg_replace("/[\s\(\)\^\[\]\|\{\}\%\£\!]+|[\-._',:&\/\\\](\s|$)/", " ", $query);
$query = trim($query);

$queryForHTML = htmlspecialchars($query);
if ($ToLowerSearchWords == 1)
{
	if ($UseUTF8 == 1 && $UseMBFunctions == 1)
		$queryForSearch = mb_strtolower($query, "UTF-8");
	else
		$queryForSearch = strtolower($query);
}
else
	$queryForSearch = $query;

//Split search phrase into words
preg_match_all("/\"(.*?)\"|\-\"(.*?)\"|[^\\s\"]+/", $queryForSearch, $SearchWords);
$SearchWords = preg_replace("/\"[\s]+|[\s]+\"|\"/", "", $SearchWords[0]);

//Sort search words if there are negative signs
if (strpos($queryForSearch, "-") !== false)
	usort($SearchWords, "sw_compare");

$NumSearchWords = count ($SearchWords);

$query_zoom_cats = "";

//Print heading
$OutputBuffers[$OUTPUT_HEADING] .= "<div class=\"searchheading\">" . $STR_RESULTS_FOR . " " . $queryForHTML;
if ($UseCats)
{
	if ($cat[0] == -1)
	{
		$OutputBuffers[$OUTPUT_HEADING] .= " " . $STR_RESULTS_IN_ALL_CATEGORIES;
		$query_zoom_cats = "&amp;zoom_cat%5B%5D=-1";
	}
	else
	{
		$OutputBuffers[$OUTPUT_HEADING] .= " " . $STR_RESULTS_IN_CATEGORY . " ";
		for ($catit = 0; $catit < $num_zoom_cats; $catit++)
		{
			if ($catit > 0)
				$OutputBuffers[$OUTPUT_HEADING] .= ", ";
			$OutputBuffers[$OUTPUT_HEADING] .= "\"". rtrim($catnames[$cat[$catit]]) . "\"";
			$query_zoom_cats .= "&amp;zoom_cat%5B%5D=".$cat[$catit];
		}
	}
}
$OutputBuffers[$OUTPUT_HEADING] .= "<br /></div>\n";

$OutputResultsBuffer .= "<div class=\"results\">\n";

// Begin main search loop -----------------------------------------------------

//$pagesCount = count($urls);
$pagesCount = $NumPages;
$outputline = 0;
$IsMaxLimitExceeded = 0;
$wordsmatched = 0;

// Initialise $res_table to be a 2D array of count($pages) long, filled with zeros.
//$res_table = array_fill(0, $pagesCount, array_fill(0, 6, 0));
$res_table = array();
for ($i = 0; $i < $pagesCount; $i++)
{
	$res_table[$i] = array();
	$res_table[$i][0] = 0;  // score
	$res_table[$i][1] = 0;  // num of sw matched
	$res_table[$i][2] = 0;  // pagetext ptr #1
	$res_table[$i][3] = 0;  // pagetext ptr #2
	$res_table[$i][4] = 0;  // pagetext ptr #3
	$res_table[$i][5] = 0;  // 'and' user search terms matched
	$res_table[$i][6] = 0;	// combined prox field
}

$exclude_count = 0;

// check if word is in skipword file
$SkippedWords = 0;
$context_maxgoback = 1;
$SkippedExactPhrase = 0;
$maxscore = 0;

// queryForURL is the query prepared to be passed in a URL.
$queryForURL = urlencode($query);

// Find recommended links if any (before stemming)
$num_recs_found = 0;
if ($Recommended == 1)
{
	for ($rl = 0; $rl < $rec_count && $num_recs_found < $RecommendedMax; $rl++)
	{
		$rec_word = $rec[$rl][0];
		$rec_idx = intval($rec[$rl][1]);
		if (strchr($rec_word, ','))
		{
			$rec_multiwords = explode(",", $rec_word);
			$rec_multiwords_count = count($rec_multiwords);
			for ($rlm = 0; $rlm < $rec_multiwords_count; $rlm++)
			{
				if (RecLinkWordMatch($rec_multiwords[$rlm], $rec_idx) == true)
					break;
			}
		}
		else
			RecLinkWordMatch($rec_word, $rec_idx);
	}
	if ($num_recs_found > 0)
		$OutputBuffers[$OUTPUT_RECOMMENDED] .= "</div>";
}


// Prepopulate some data for each searchword
$sw_results = array();
$search_terms_ids = array();
$phrase_terms_ids = array();
for ($sw = 0; $sw < $NumSearchWords; $sw++)
{
	$sw_results[$sw] = 0;
	$UseWildCards[$sw] = 0;

	// for main search terms
	$search_terms_ids[$sw] = array();
	// for exact phrases
	$phrase_terms_ids[$sw] = array();

	if (strpos($SearchWords[$sw], "*") !== false || strpos($SearchWords[$sw], "?") !== false)
	{
		$RegExpSearchWords[$sw] = pattern2regexp($SearchWords[$sw]);
		$UseWildCards[$sw] = 1;
	}

	if ($Highlighting == 1 && $UseWildCards[$sw] == 0)
	{
		$RegExpSearchWords[$sw] = $SearchWords[$sw];
		if (strpos($RegExpSearchWords[$sw], "\\") !== false)
			$RegExpSearchWords[$sw] = str_replace("\\", "\\\\", $RegExpSearchWords[$sw]);
		if (strpos($RegExpSearchWords[$sw], "/") !== false)
			$RegExpSearchWords[$sw] = str_replace("/", "\/", $RegExpSearchWords[$sw]);
		if (strpos($RegExpSearchWords[$sw], "+") !== false)
			$RegExpSearchWords[$sw] = str_replace("+", "\+", $RegExpSearchWords[$sw]);
	}
}

for ($sw = 0; $sw < $NumSearchWords; $sw++)
{
	if ($SearchWords[$sw] == "")
		continue;

	// check min length
	if (strlen($SearchWords[$sw]) < $MinWordLen)
	{
		SkipSearchWord($sw);
		continue;
	}

	$ExactPhrase = 0;
	$ExcludeTerm = 0;

	// Check exclusion searches
	if ($SearchWords[$sw][0] == "-")
	{
		$SearchWords[$sw] = substr($SearchWords[$sw], 1);
		$ExcludeTerm = 1;
		$exclude_count++;
	}
	
	// Stem the words if necessary (only AFTER stripping exclusion char)
	if ($UseStemming == 1)
	{
		if ($AllowExactPhrase == 0 || strpos($SearchWords[$sw], " ") === false)
			$SearchWords[$sw] = $porterStemmer->Stem($SearchWords[$sw]);
	}		

	if ($AllowExactPhrase == 1 && strpos($SearchWords[$sw], " ") !== false)
	{
		// Initialise exact phrase matching for this search term
		$ExactPhrase = 1;
		$phrase_terms = explode(" ", $SearchWords[$sw]);
		//$phrase_terms = preg_split("/\W+/", $SearchWords[$sw], -1, 0 /*PREG_SPLIT_DELIM_CAPTURE*/);
		$num_phrase_terms = count($phrase_terms);
		if ($num_phrase_terms > $context_maxgoback)
			$context_maxgoback = $num_phrase_terms;

		$phrase_terms_data = array();

		if ($UseStemming == 1)
		{
			for ($j = 0; $j < $num_phrase_terms; $j++)
				$phrase_terms[$j] = $porterStemmer->Stem($phrase_terms[$j]);
		}

		$tmpid = 0;
		$WordNotFound = 0;
		$j = 0;
		for ($j = 0; $j < $num_phrase_terms; $j++)
		{
			$tmpid = GetDictID($phrase_terms[$j]);
			if ($tmpid == -1)   // word is not in dictionary
			{
				$WordNotFound = 1;
				break;
			}
			$phrase_terms_ids[$sw][$j] = $tmpid;

			$wordmap_row = $dict[$tmpid][$DICT_PTR];
			if ($wordmap_row != -1)
			{
				fseek($fp_wordmap, $wordmap_row);
				$countbytes = fread($fp_wordmap, 2);
				$phrase_data_count[$j] = ord($countbytes[0]) | ord($countbytes[1])<<8;
				for ($xbi = 0; $xbi < $phrase_data_count[$j]; $xbi++) {
					$xbindata = fread($fp_wordmap, 8);
					if (strlen($xbindata) == 0)
						$OutputResultsBuffer .= "error in wordmap file: expected data not found";
					$phrase_terms_data[$j][$xbi] = unpack("Cscore/Cprox/vpagenum/Vptr", $xbindata);
				}
			}
			else
			{
				$phrase_data_count[$j] = 0;
				$phrase_terms_data[$j] = 0;
			}
		}
		$phrase_terms_ids[$sw][$j] = 0;	// null terminate the list

		if ($WordNotFound == 1)
			continue;
	}
	else if ($UseWildCards[$sw])
	{
		$pattern = "/";

		// match entire word
		if ($SearchAsSubstring == 0)
			$pattern = $pattern . "\A";

		$pattern = $pattern . $RegExpSearchWords[$sw];

		if ($SearchAsSubstring == 0)
			$pattern = $pattern . "\Z";

		if ($ToLowerSearchWords != 0)
			$pattern = $pattern . "/i";
		else
			$pattern = $pattern . "/";
	}

	for ($i = 0; $i < $dict_count; $i++)
	{
		$dictline = $dict[$i];
		$word = $dict[$i][$DICT_WORD];

		// if we're not using wildcards, direct match
		if ($ExactPhrase == 1)
		{
			// todo: move to next phrase term if first phrase term is skipped?
			// compare first term in exact phrase
			//$result = wordcasecmp($phrase_terms[0], $word);
			if ($i == $phrase_terms_ids[$sw][0])
				$result = 0;
			else
				$result = 1;
		}
		else if ($UseWildCards[$sw] == 0)
		{
			if ($SearchAsSubstring == 0)
				$result = wordcasecmp($SearchWords[$sw], $word);
			else
			{
				if (mystristr($word, $SearchWords[$sw]) == FALSE)
					$result = 1;    // not matched
				else
					$result = 0;    // matched
			}
		}
		else
		{
			// if we have wildcards...
			$result = !(preg_match($pattern, $word));
		}
		// result = 0 if matched, result != 0 if not matched.

		// word found but indicated to be not indexed or skipped
		if ($result == 0 && (is_numeric($dictline[$DICT_PTR]) == false || $dictline[$DICT_PTR] == -1))
		{
			if ($UseWildCards[$sw] == 0 && $SearchAsSubstring == 0)
			{
				if ($ExactPhrase == 1)
					$SkippedExactPhrase = 1;

				SkipSearchWord($sw);
				break;
			}
			else
				continue;
		}
		
		if ($result == 0)
		{
			// keyword found in the dictionary
			$wordsmatched++;
			if ($ExcludeTerm == false && $wordsmatched > $MaxMatches)
			{
				$IsMaxLimitExceeded = true;
				break;
			}

			/// remember the dictionary ID for this matched search term
			$search_terms_ids[$sw] = $i;

			if ($ExactPhrase == 1)
			{
				// we'll use the wordmap data for the first term that we have worked out earlier
				$data = $phrase_terms_data[0];
				$data_count = $phrase_data_count[0];
				$ContextSeeks = 0;
			}
			else
			{
				// seek to position in wordmap file
				fseek($fp_wordmap, $dictline[$DICT_PTR]);
				//print "seeking in wordmap: " . $dictline[1] . "<br />";

				// first 2 bytes is data count
				$countbytes = fread($fp_wordmap, 2);
				$data_count = ord($countbytes[0]) | ord($countbytes[1])<<8;
				//print "data count: " . $data_count . "<br />";

				for ($bi = 0; $bi < $data_count; $bi++)
				{
					$bindata = fread($fp_wordmap, 8);
					if (strlen($bindata) == 0)
						$OutputResultsBuffer .= "Error in wordmap file: expected data not found";
					$data[$bi] = unpack("Cscore/Cprox/vpagenum/Vptr", $bindata);
				}
			}
			$sw_results[$sw] += $data_count;

			// Go through wordmap for each page this word appears on
			for ($j = 0; $j < $data_count; $j++)
			{
				$score = $data[$j]["score"];
				$prox = $data[$j]["prox"];
				$txtptr = $data[$j]["ptr"];
				$ipage = $data[$j]["pagenum"];

				if ($score == 0)
					continue;

				if ($pageinfo[$ipage]["boost"] != 0)
				{
					$score *= ($pageinfo[$ipage]["boost"] / 10);
					$score = ceil($score);
				}

				if ($ExactPhrase == 1)
				{
					$maxptr = $data[$j]["ptr"];
					$maxptr_term = 0;
					$GotoNextPage = 0;

					// Check if all of the other words in the phrase appears on this page.
					for ($xi = 0; $xi < $num_phrase_terms && $GotoNextPage == 0; $xi++)
					{
						// see if this word appears at all on this page, if not, we stop scanning page.
						// do not check for skipped words (data count value of zero)
						if ($phrase_data_count[$xi] != 0)
						{
							// check wordmap for this search phrase to see if it appears on the current page.
							for ($xbi = 0; $xbi < $phrase_data_count[$xi]; $xbi++)
							{
								if ($phrase_terms_data[$xi][$xbi]["pagenum"] == $data[$j]["pagenum"])
								{
									// make sure that words appear in same proximity

									$overlapProx = $phrase_terms_data[$xi][$xbi]["prox"] << 1;

									if (($data[$j]["prox"] & $phrase_terms_data[$xi][$xbi]["prox"]) == 0 &&
										($data[$j]["prox"] & $overlapProx) == 0)
									{
										$GotoNextPage = 1;
									}
									else
									{
										// intersection, this term appears on both pages, goto next term
										// remember biggest pointer.
										if ($phrase_terms_data[$xi][$xbi]["ptr"] > $maxptr)
										{
											$maxptr = $phrase_terms_data[$xi][$xbi]["ptr"];
											$maxptr_term = $xi;
										}
										$score += $phrase_terms_data[$xi][$xbi]["score"];
									}
									break;
								}
							}
							if ($xbi == $phrase_data_count[$xi]) // if not found
							{
								$GotoNextPage = 1;
								break;  // goto next page
							}
						}
					}   // end phrase term for loop
					if ($GotoNextPage == 1)
					{
						continue;
					}

					// Check how many context seeks we have made.
					$ContextSeeks++;
					if ($ContextSeeks > $MaxContextSeeks)
					{						
						$IsMaxLimitExceeded = true;
						break;
					}

					// ok, so this page contains all of the words in the phrase
					$FoundPhrase = 0;
					$FoundFirstWord = 0;

					// we goto the first occurance of the first word in pagetext
					$pos = $maxptr - (($maxptr_term+3) * $DictIDLen);    // assume 3 possible punctuations.
					// do not seek further back than the occurance of the first word (avoid wrong page)
					if ($pos < $data[$j]["ptr"])
						$pos = $data[$j]["ptr"];

					fseek($fp_pagetext, $pos);

					// now we look for the phrase within the context of this page
					do
					{
						for ($xi = 0; $xi < $num_phrase_terms; $xi++)
						{
							// do...while loop to ignore punctuation marks in context phrase
							do
							{
								// Inlined (and unlooped) the following function for speed reasons
								//$xword_id = GetNextDictWord($fp_pagetext);
								$bytes_buffer = fread($fp_pagetext, $DictIDLen);
								if ($DictIDLen == 4)
								{
									$xword_id = ord($bytes_buffer[0]);
									$xword_id = $xword_id | ord($bytes_buffer[1]) << 8;
									$xword_id = $xword_id | ord($bytes_buffer[2]) << (8*2);
									$variant_index = $bytes_buffer[3];
								}
								else
								{
									$xword_id = ord($bytes_buffer[0]);
									$xword_id = $xword_id | ord($bytes_buffer[1]) << 8;
									$variant_index = $bytes_buffer[2];
								}
								$pos += $DictIDLen;
								// check if we are at the end of page (wordid = 0) or invalid $xword_id
								if ($xword_id == 0 || $xword_id == 1 || $xword_id >= $dict_count)
									break;
							} while ($xword_id <= $DictReservedLimit && !feof($fp_pagetext));

							if ($xword_id == 0 || $xword_id == 1 || $xword_id >= $dict_count)
								break;

							// if the words are NOT the same, we break out
							if ($xword_id != $phrase_terms_ids[$sw][$xi])
							{
								// also check against first word
								if ($xi != 0 && $xword_id == $phrase_terms_ids[$sw][0])
									$xi = 0;    // matched first word
								else
									break;
							}

							// remember how many times we find the first word on this page
							if ($xi == 0)
							{
								$FoundFirstWord++;
								// remember the position of the 'start' of this phrase
								$txtptr = $pos - $DictIDLen;
							}
						}
						if ($xi == $num_phrase_terms)
						{
							// exact phrase found!
							$FoundPhrase = 1;
						}
					} while ($xword_id != 0 && $FoundPhrase == 0 &&
							$FoundFirstWord <= $data[$j]["score"]);

					if ($FoundPhrase != 1)
						continue;   // goto next page.
						
					
					$checktime = time();
					$checkTimeDiff = abs($starttime - $checktime);
					if ($checkTimeDiff > $MaxSearchTime)
					{
						$IsMaxLimitExceeded = true;						
						break;
					}
				}

				//Check if page is already in output list
				$pageexists = 0;

				if ($ExcludeTerm == 1)
				{
					// we clear out the score entry so that it'll be excluded in the filtering stage
					$res_table[$ipage][0] = 0;
				}
				elseif ($res_table[$ipage][0] == 0)
				{
					// not in list, count this page as a unique match
					$res_table[$ipage][0] = $score;
					$res_table[$ipage][2] = $txtptr;
					$res_table[$ipage][6] = $prox;
				}
				else
				{
					// already in list
					if ($res_table[$ipage][0] > 10000)
					{
						// take it easy if its too big (to prevent huge scores)
						$res_table[$ipage][0] += 1;
					}
					else
					{
						$res_table[$ipage][0] += $score;    //Add in score
						//$res_table[$ipage][0] *= 2;         //Double Score as we have two words matching
					}

					// store the next two searchword matches
					if ($res_table[$ipage][1] > 0 && $res_table[$ipage][1] < $MaxContextKeywords)
					{
						if ($res_table[$ipage][3] == 0)
							$res_table[$ipage][3] = $txtptr;
						elseif ($res_table[$ipage][4] == 0)
							$res_table[$ipage][4] = $txtptr;
					}

					$res_table[$ipage][6] = $res_table[$ipage][6] & $prox;
				}
				$res_table[$ipage][1] += 1;

				if ($res_table[$ipage][0] > $maxscore)
					$maxscore = $res_table[$ipage][0];

				// store the 'and' user search terms matched' value
				if ($res_table[$ipage][5] == $sw || $res_table[$ipage][5] == $sw-$SkippedWords-$exclude_count)
					$res_table[$ipage][5] += 1;
			}

			if ($UseWildCards[$sw] == 0 && $SearchAsSubstring == 0)
				break;  //This search word was found, so skip to next
		}
	}
}
//Close the files
fclose($fp_wordmap);

if ($SkippedWords > 0)
{
	$OutputBuffers[$OUTPUT_SUMMARY] .= "<div class=\"summary\">" . $STR_SKIPPED_FOLLOWING_WORDS . " " . $SkippedOutputStr . ".<br />\n";		
	if ($SkippedExactPhrase == 1)
		$OutputBuffers[$OUTPUT_SUMMARY] .= $STR_SKIPPED_PHRASE . ".<br />\n";
	$OutputBuffers[$OUTPUT_SUMMARY] .=  "<br /></div>\n";
}

$metaParams = "";
// append to queryForURL with other query parameters for custom meta fields?
if ($UseMetaFields == 1)
{
	for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
	{
		if (is_array($meta_query[$fieldnum]))
		{
			$num_multi_query = count($meta_query[$fieldnum]);
			for ($mqi = 0; $mqi < $num_multi_query; $mqi++)
				$metaParams .= "&amp;".$metafields[$fieldnum][$METAFIELD_NAME]."[]=".$meta_query[$fieldnum][$mqi];
		}
		else
		{
			if ($meta_query[$fieldnum] !== "")
				$metaParams .= "&amp;".$metafields[$fieldnum][$METAFIELD_NAME]."=".$meta_query[$fieldnum];
		}
	}
}

// Do this after search form so we can keep the search form value the same as the way the user entered it
if ($UseMetaFields == 1 && $MetaMoneyShowDec == 1)
{
	for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
	{
		if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MONEY && $meta_query[$fieldnum] !== "")
			$meta_query[$fieldnum] = $meta_query[$fieldnum] * 100;
	}
}

//Count number of output lines that match ALL search terms
$oline = 0;
$fullmatches = 0;
$matches = 0;

$baseScale = 1.3;
$proxScale = 1.7;
if (isset($WeightProximity))
	$proxScale += ($WeightProximity/10);

$CatCounterFilled = 0;
if ($UseCats && $DisplayCatSummary == 1)
{
	if (($cat[0] == -1 || $num_zoom_cats > 1) && $NumCats > 0)
		$CatCounter = array_fill(0, $NumCats, 0);
	else
		$DisplayCatSummary = 0;
}

// Second pass, results filtering.
$full_numwords = $NumSearchWords - $SkippedWords - $exclude_count;
for ($i = 0; $i < $pagesCount; $i++)
{
	$IsFiltered = false;
	if ($res_table[$i][0] > 0 || $IsEmptyMetaQuery)
	{
		if ($UseMetaFields && $IsFiltered == false)
		{        	
			for ($fieldnum = 0; $fieldnum < $NumMetaFields && !$IsFiltered; $fieldnum++)
			{         		
				$IsAnyDropdown = false;
				if (is_array($meta_query[$fieldnum]))
					$tmpQueryVal = $meta_query[$fieldnum][0];
				else
					$tmpQueryVal = $meta_query[$fieldnum];
					

				if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN ||
					$metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
				{
					if ($tmpQueryVal == -1)
						$IsAnyDropdown = true;
				}

				if ($tmpQueryVal !== "" && $IsAnyDropdown == false)
				{
					if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_TEXT)
					{
						if (strlen($metavalues[$i][$fieldnum]) == 0)
							$IsFiltered = true;
						else if ($metafields[$fieldnum][$METAFIELD_METHOD] == $METAFIELD_METHOD_SUBSTRING)
						{
							if (mystristr($metavalues[$i][$fieldnum], $meta_query[$fieldnum]) === FALSE)
								$IsFiltered = true;
						}						
						else 						
						{
							if (strcasecmp($metavalues[$i][$fieldnum], $meta_query[$fieldnum]) !== 0)
								$IsFiltered = true;
						}						
					}
					else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN)
					{
						if ($metavalues[$i][$fieldnum] == $METAFIELD_NOVALUE_MARKER)
							$IsFiltered = true;
						else if ($metavalues[$i][$fieldnum] != floatval($meta_query[$fieldnum]))
							$IsFiltered = true;
					}
					else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
					{
						$IsFiltered = true;
						if ($metavalues[$i][$fieldnum] !== 0)
						{
							$num_multi_query = 0;
							if (is_array($meta_query[$fieldnum]))
								$num_multi_query = count($meta_query[$fieldnum]);
							for ($mqi = 0; $mqi < $num_multi_query && $IsFiltered; $mqi++)
							{
								for ($mvi = 0; $mvi < $metavalues[$i][$fieldnum][0]; $mvi++)
								{
									if ($metavalues[$i][$fieldnum][$mvi+1] == intval($meta_query[$fieldnum][$mqi]))
									{
										$IsFiltered = false;
										break;
									}
								}
							}
						}
					}
					else
					{
						// numeric comparison here
						if ($metavalues[$i][$fieldnum] == $METAFIELD_NOVALUE_MARKER)
						{
							$bRet = false;
						}
						else if ($metafields[$fieldnum][$METAFIELD_METHOD] == $METAFIELD_METHOD_LESSTHAN)
						{
							$bRet = $metavalues[$i][$fieldnum] < $meta_query[$fieldnum];
						}
						else if ($metafields[$fieldnum][$METAFIELD_METHOD] == $METAFIELD_METHOD_LESSTHANORE)
						{
							$bRet = $metavalues[$i][$fieldnum] <= $meta_query[$fieldnum];
						}
						else if ($metafields[$fieldnum][$METAFIELD_METHOD] == $METAFIELD_METHOD_GREATERTHAN)
						{
							$bRet = $metavalues[$i][$fieldnum] > $meta_query[$fieldnum];
						}
						else if ($metafields[$fieldnum][$METAFIELD_METHOD] == $METAFIELD_METHOD_GREATERTHANORE)
						{
							$bRet = $metavalues[$i][$fieldnum] >= $meta_query[$fieldnum];
						}
						else
						{
							// exact match
							$bRet = $metavalues[$i][$fieldnum] == $meta_query[$fieldnum];
						}

						if ($bRet == false)
							$IsFiltered = true;
					}
				}
				// only add to res_table if empty query!
				if ($IsEmptyMetaQuery == true && $IsFiltered == false)
				{
					$res_table[$i][0]++;
					$res_table[$i][1]++;
				}
			}
		}

		if ($IsFiltered == false)
		{
			if ($res_table[$i][5] < $full_numwords && $and == 1)
			{
				// if AND search, only copy AND results				
				$IsFiltered = true;
			}
		}
		
		if ($UseCats && $cat[0] != -1 && $IsFiltered == false)
		{
			// Using cats and not doing an "all cats" search
			$bFoundCat = false;
			for ($cati = 0; $cati < $num_zoom_cats; $cati++)
			{
				if (CheckBitInByteArray($cat[$cati], $catpages[$i]) !== 0)
				{
					if ($DisplayCatSummary == 1)
					{
						$CatCounter[$cat[$cati]]++;
						$CatCounterFilled = 1;
					}					
					$bFoundCat = true;
				}
			}
			//if ($cati == $num_zoom_cats)
			if ($bFoundCat == false)
				$IsFiltered = true;	
		}        
		
		if ($IsFiltered == false)
		{
			// we can only count our AND total here AFTER we've filtered out the cats
			if ($res_table[$i][5] >= $full_numwords)
				$fullmatches++;
				
			// copy if not filtered out
			$output[$oline][0] = $i;                    // page index

			$finalScale = (($res_table[$i][6] / 255.0) * $proxScale) + $baseScale;

			if ($res_table[$i][1] > 1)	// multiword search
			{
				if ($res_table[$i][1] <= 10)
				{
					$finalScale = pow($finalScale, $res_table[$i][1]-1);
				}
				else
				{
					$finalScale = pow($finalScale, 10);
					$finalScale += $res_table[$i][1] - 10;
				}
			}

			if ($UseCats && $DisplayCatSummary == 1 && $cat[0] == -1)
			{
				// if we are doing an All category search AND we're showing cat summary
				for ($cati = 0; $cati < $NumCats; $cati++)
				{
					//if (($pageinfo[$i]["catnumber"] & (1 << $cati)) !== 0)
					if (CheckBitInByteArray($cati, $catpages[$i]) !== 0)
					{
						$CatCounter[$cati]++;
						$CatCounterFilled = 1;
					}
				}				
			}

			// final score and rounding
			$output[$oline][1] = (int) ($res_table[$i][0] * $finalScale + 0.5);
			$output[$oline][2] = $res_table[$i][1];     // num of sw matched
			$output[$oline][3] = $res_table[$i][2];     // pagetext ptr #1
			$output[$oline][4] = $res_table[$i][3];     // pagetext ptr #2
			$output[$oline][5] = $res_table[$i][4];     // pagetext ptr #3
			$oline++;
		}
	}
}
$matches = $oline;

//Sort results in order of score, use the "SortCompare" function
if ($matches > 1)
{
	if ($sort == 1 && $UseDateTime == 1)
	{
		usort($output, "SortByDate");
	}
	else
	{
		// Default sort by relevance
		usort($output, "SortCompare");
	}
}

//Display search result information
$OutputBuffers[$OUTPUT_SUMMARY] .= "<div class=\"summary\">\n";

if ($IsMaxLimitExceeded)
	$OutputBuffers[$OUTPUT_SUMMARY] .= $STR_PHRASE_CONTAINS_COMMON_WORDS . "<br /><br />";

if ($matches == 0)
	$OutputBuffers[$OUTPUT_SUMMARY] .= $STR_SUMMARY_NO_RESULTS_FOUND;
elseif ($NumSearchWords > 1 && $and == 0)
{
	//OR
	$SomeTermMatches = $matches - $fullmatches;
	$OutputBuffers[$OUTPUT_SUMMARY] .= PrintNumResults($fullmatches) . " " . $STR_SUMMARY_FOUND_CONTAINING_ALL_TERMS . " ";
	if ($SomeTermMatches > 0)
		$OutputBuffers[$OUTPUT_SUMMARY] .= PrintNumResults($SomeTermMatches) . " " . $STR_SUMMARY_FOUND_CONTAINING_SOME_TERMS;
}
elseif ($NumSearchWords > 1 && $and == 1) //AND
	$OutputBuffers[$OUTPUT_SUMMARY] .= PrintNumResults($fullmatches) . " " . $STR_SUMMARY_FOUND_CONTAINING_ALL_TERMS;
else
	$OutputBuffers[$OUTPUT_SUMMARY] .= PrintNumResults($matches) . " " . $STR_SUMMARY_FOUND;

$OutputBuffers[$OUTPUT_SUMMARY] .= "<br />\n</div>\n";

if ($matches < 3)
{
	if ($and == 1 && $NumSearchWords > 1)
		$OutputBuffers[$OUTPUT_SUGGESTION] .= "<div class=\"suggestion\"><br />" . $STR_POSSIBLY_GET_MORE_RESULTS . " <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=0&amp;zoom_sort=".$sort."\">". $STR_ANY_OF_TERMS . "</a>.</div>";
	else if ($UseCats && $cat[0] != -1)
		$OutputBuffers[$OUTPUT_SUGGESTION] .= "<div class=\"suggestion\"><br />" . $STR_POSSIBLY_GET_MORE_RESULTS . " <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_per_page=".$per_page."&amp;zoom_cat=-1&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">" . $STR_ALL_CATS . "</a>.</div>";
}

// Show category summary
if ($UseCats == 1 && $DisplayCatSummary == 1 && $CatCounterFilled == 1)
{	
	$OutputBuffers[$OUTPUT_CATSUMMARY] .= "<div class=\"cat_summary\"><br />".$STR_CAT_SUMMARY."\n<ul>\n";
	$catSummaryItemCount = 0;
	for ($catit = 0; $catit < $NumCats; $catit++)
	{				
		if ($CatCounter[$catit] > 0)
		{
			// if all the results found belonged in this current category, then we don't show it in the summary
			if ($CatCounter[$catit] != $matches)
			{
				$catSummaryItemCount++;
				$OutputBuffers[$OUTPUT_CATSUMMARY] .= "<li><a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_cat=".$catit."&amp;zoom_per_page=".$per_page."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">".$catnames[$catit];
				$OutputBuffers[$OUTPUT_CATSUMMARY] .= "</a> (".$CatCounter[$catit].")</li>";
			}						
		}
	}
	
	if ($catSummaryItemCount == 0)
	{
		// Clear the cat summary if we decided we didn't need to show it afterall
		$OutputBuffers[$OUTPUT_CATSUMMARY] = "";
	}
	else
		$OutputBuffers[$OUTPUT_CATSUMMARY] .= "</ul>\n</div>\n";
}

if ($Spelling == 1)
{
	// load in spellings file
	$fp_spell = fopen($SPELLINGFILE, "rt");
	$i = 0;
	while (!feof($fp_spell))
	{
		$spline = fgets($fp_spell, $MaxKeyWordLineLen);
		if (strlen($spline) > 0)
		{
			$spell[$i] = explode(" ", $spline, 4);
			$i++;
		}
	}
	fclose($fp_spell);
	$spell_count = $i;

	$SuggestStr = "";
	$SuggestionFound = 0;
	$SuggestionCount = 0;

	$word = "";
	$word2 = "";
	$word3 = "";
	$tmpWordStr = "";	// for local stemming and comparison

	for ($sw = 0; $sw < $NumSearchWords; $sw++)
	{
		if ($sw_results[$sw] >= $SpellingWhenLessThan)
		{
			// this word has enough results
			if ($sw > 0)
				$SuggestStr = $SuggestStr . " ";
			$SuggestStr = $SuggestStr . $SearchWords[$sw];
		}
		else
		{
			// this word returned less results than threshold, and requires spelling suggestions
			$sw_spcode = GetSPCode($SearchWords[$sw]);			

			if (strlen($sw_spcode) > 0)
			{
				$SuggestionFound = 0;
				for ($i = 0; $i < $spell_count && $SuggestionFound == 0; $i++)
				{
					$spcode = $spell[$i][0];

					if ($spcode == $sw_spcode)
					{
						$j = 0;
						while ($SuggestionFound == 0 && $j < 3 && isset($spell[$i][1+$j]))
						{
							$dictid = intval($spell[$i][1+$j]);
							$word = GetSpellingWord($dictid);
							$tmpWordStr = $word;
							if ($UseStemming == 1)
							{
								$tmpWordStr = strtolower($tmpWordStr);
								$tmpWordStr = $porterStemmer->Stem($tmpWordStr);
							}

							if (wordcasecmp($tmpWordStr, $SearchWords[$sw]) == 0)
							{
								// Check that it is not a skipped word or the same word
								$SuggestionFound = 0;
							}
							else
							{
								$SuggestionFound = 1;
								$SuggestionCount++;
								if ($NumSearchWords == 1) // if single word search
								{
									if ($j < 1 && isset($spell[$i][1+$j+1]))
									{
										$dictid = intval($spell[$i][1+$j+1]);
										$word2 = GetSpellingWord($dictid);
										$tmpWordStr = $word2;
										if ($UseStemming == 1)
										{
											$tmpWordStr = strtolower($tmpWordStr);
											$tmpWordStr = $porterStemmer->Stem($tmpWordStr);
										}
										if (wordcasecmp($tmpWordStr, $SearchWords[$sw]) == 0)
											$word2 = "";
									}
									if ($j < 2 && isset($spell[$i][1+$j+2]))
									{
										$dictid = intval($spell[$i][1+$j+2]);
										$word3 = GetSpellingWord($dictid);
										$tmpWordStr = $word3;
										if ($UseStemming == 1)
										{
											$tmpWordStr = strtolower($tmpWordStr);
											$tmpWordStr = $porterStemmer->Stem($tmpWordStr);
										}
										if (wordcasecmp($tmpWordStr, $SearchWords[$sw]) == 0)
											$word3 = "";
									}
								}
							}
							$j++;
						}
					}
					elseif (strcmp($spcode, $sw_spcode) > 0)
					{
						break;
					}
				}

				if ($SuggestionFound == 1)
				{
					if ($sw > 0)
						$SuggestStr = $SuggestStr . " ";
					$SuggestStr = $SuggestStr . $word;  // add string AFTER so we can preserve order of words
				}
			}
		}
	}
	if ($SuggestionCount > 0)
	{
		$OutputBuffers[$OUTPUT_SUGGESTION] .= "<div class=\"suggestion\"><br />" . $STR_DIDYOUMEAN . " <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".urlencode($SuggestStr).$metaParams."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=0&amp;zoom_sort=".$sort."\">". $SuggestStr . "</a>";
		if (strlen($word2) > 0)
			$OutputBuffers[$OUTPUT_SUGGESTION] .= " $STR_OR <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".urlencode($word2).$metaParams."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">". $word2 . "</a>";
		if (strlen($word3) > 0)
			$OutputBuffers[$OUTPUT_SUGGESTION] .= " $STR_OR <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".urlencode($word3).$metaParams."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">". $word3 . "</a>";
		$OutputBuffers[$OUTPUT_SUGGESTION] .= "?</div>";
	}
}

// Number of pages of results
$num_pages = ceil($matches / $per_page);
if ($num_pages > 1)
	$OutputBuffers[$OUTPUT_PAGESCOUNT] .= "<div class=\"result_pagescount\"><br />" . $num_pages . " " . $STR_PAGES_OF_RESULTS . "</div>\n";

// Show sorting options
if ($matches > 1)
{
	if ($UseDateTime == 1)
	{
		$OutputBuffers[$OUTPUT_SORTING] .= "<div class=\"sorting\">";
		if ($sort == 1)
			$OutputBuffers[$OUTPUT_SORTING] .= "<a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_page=".$page."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=0\">". $STR_SORTBY_RELEVANCE . "</a> / <b>". $STR_SORTEDBY_DATE . "</b>";
		else
			$OutputBuffers[$OUTPUT_SORTING] .= "<b>". $STR_SORTEDBY_RELEVANCE . "</b> / <a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_page=".$page."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=1\">". $STR_SORTBY_DATE . "</a>";
		$OutputBuffers[$OUTPUT_SORTING] .= "</div>";
	}
}

// Determine current line of result from the $output array
if ($page == 1) {
	$arrayline = 0;
} else {
	$arrayline = (($page - 1) * $per_page);
}

// The last result to show on this page
$result_limit = $arrayline + $per_page;

// Display the results
while ($arrayline < $matches && $arrayline < $result_limit)
{
	$ipage = $output[$arrayline][0];
	$score = $output[$arrayline][1];

	$pgdata = GetPageData($ipage);
	$url = $pgdata[$PAGEDATA_URL];
	$title = $pgdata[$PAGEDATA_TITLE];
	$description = $pgdata[$PAGEDATA_DESC];

	$urlLink = $url;

	//$urlLink = rtrim($urls[$ipage]);
	if ($GotoHighlight == 1)
	{
		if ($SearchAsSubstring == 1)
			$urlLink = AddParamToURL($urlLink, "zoom_highlightsub=".$queryForURL);
		else
			$urlLink = AddParamToURL($urlLink, "zoom_highlight=".$queryForURL);
	}
	if ($PdfHighlight == 1)
	{
		if (stristr($urlLink, ".pdf") != FALSE)
			$urlLink = $urlLink."#search=&quot;".str_replace("\"", "", $query)."&quot;";
	}

	if ($arrayline % 2 == 0)
		$OutputResultsBuffer .= "<div class=\"result_block\">";
	else
		$OutputResultsBuffer .= "<div class=\"result_altblock\">";

	if ($pageinfo[$ipage]["linkaction"] == 1)
		$target = " target=\"_blank\"";
	else
		$target = $zoom_target;

	if ($UseZoomImage)
	{
		if (isset($pgdata[$PAGEDATA_IMG]))
			$image = $pgdata[$PAGEDATA_IMG];
		else
			$image = "";
		if (strlen($image) > 0)
		{
			$OutputResultsBuffer .= "<div class=\"result_image\">";
			$OutputResultsBuffer .= "<a href=\"".$urlLink."\"" . $target . "><img src=\"$image\" alt=\"\" class=\"result_image\" /></a>";
			$OutputResultsBuffer .= "</div>";
		}
	}

	$OutputResultsBuffer .= "<div class=\"result_title\">";
	if ($DisplayNumber == 1)
		$OutputResultsBuffer .= "<b>".($arrayline+1).".</b>&nbsp;";

	if ($DisplayTitle == 1)
	{
		$OutputResultsBuffer .= "<a href=\"".$urlLink."\"" . $target . ">";
		$OutputResultsBuffer .= PrintHighlightDescription(rtrim($title));
		$OutputResultsBuffer .= "</a>";
	}
	else
		$OutputResultsBuffer .= "<a href=\"".$urlLink."\"" . $target . ">".rtrim($url)."</a>";

	if ($UseCats)
	{
		$OutputResultsBuffer .= " <span class=\"category\">";
		for ($catit = 0; $catit < $NumCats; $catit++)
		{
			//if (($pageinfo[$ipage]["catnumber"] & (1 << $catit)) !== 0)
			if (CheckBitInByteArray($catit, $catpages[$ipage]) !== 0)
				$OutputResultsBuffer .= " [".trim($catnames[$catit])."]";
		}
		$OutputResultsBuffer .= "</span>";
	}
	$OutputResultsBuffer .= "</div>\n";

	if ($UseMetaFields == 1 && $DisplayMetaFields == 1)
	{
		for ($fieldnum = 0; $fieldnum < $NumMetaFields; $fieldnum++)
		{
			$cssFieldName = "result_metaname_" . $metafields[$fieldnum][$METAFIELD_NAME];
			$cssValueName = "result_metavalue_" . $metafields[$fieldnum][$METAFIELD_NAME];
			if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MULTI)
			{
				if ($metavalues[$ipage][$fieldnum][0] > 0)
				{
					$OutputResultsBuffer .= "<div class=\"result_custommeta\">";
					$OutputResultsBuffer .= "<span class=\"$cssFieldName\">".$metafields[$fieldnum][$METAFIELD_SHOW].": </span>";
					$OutputResultsBuffer .= "<span class=\"$cssValueName\">";
					$ddarray = $metafields[$fieldnum][$METAFIELD_DROPDOWN];
					for ($mvi = 0; $mvi < $metavalues[$ipage][$fieldnum][0]; $mvi++)
					{
						if ($mvi > 0)
							$OutputResultsBuffer .= ", ";
						$OutputResultsBuffer .= $ddarray[$metavalues[$ipage][$fieldnum][$mvi+1]];
					}
					$OutputResultsBuffer .= "</span>";
					$OutputResultsBuffer .= "</div>";
				}
			}
			else
			{		
				if ($metavalues[$ipage][$fieldnum] != $METAFIELD_NOVALUE_MARKER && strlen($metavalues[$ipage][$fieldnum]) > 0)
				{
					if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_DROPDOWN)
					{
						$OutputResultsBuffer .= "<div class=\"result_custommeta\">";
						$OutputResultsBuffer .= "<span class=\"$cssFieldName\">".$metafields[$fieldnum][$METAFIELD_SHOW].": </span>";
						$OutputResultsBuffer .= "<span class=\"$cssValueName\">";
						$ddarray = $metafields[$fieldnum][$METAFIELD_DROPDOWN];
						$OutputResultsBuffer .= $ddarray[$metavalues[$ipage][$fieldnum]]."</span>";
						$OutputResultsBuffer .= "</div>";
					}				
					else if ($metafields[$fieldnum][$METAFIELD_TYPE] == $METAFIELD_TYPE_MONEY)
					{
						$OutputResultsBuffer .= "<div class=\"result_custommeta\">";
						$OutputResultsBuffer .= "<span class=\"$cssFieldName\">".$metafields[$fieldnum][$METAFIELD_SHOW].": </span>";
						$OutputResultsBuffer .= "<span class=\"$cssValueName\">".$MetaMoneyCurrency;
						$tmpMoneyStr = "";
						if ($MetaMoneyShowDec == 1)
							$tmpMoneyStr = sprintf("%01.2f", $metavalues[$ipage][$fieldnum]/100);
						else
							$tmpMoneyStr = sprintf("%d", $metavalues[$ipage][$fieldnum]);
						$OutputResultsBuffer .= $tmpMoneyStr."</span>";
						$OutputResultsBuffer .= "</div>";
					}
					else
					{
						// just print it out
						$OutputResultsBuffer .= "<div class=\"result_custommeta\">";
						$OutputResultsBuffer .= "<span class=\"$cssFieldName\">".$metafields[$fieldnum][$METAFIELD_SHOW].": </span>";
						$OutputResultsBuffer .= "<span class=\"$cssValueName\">";
						$OutputResultsBuffer .= $metavalues[$ipage][$fieldnum]."</span>";
						$OutputResultsBuffer .= "</div>";
					}
				}
			}
		}
	}

	if ($DisplayMetaDesc == 1)
	{
		// Print meta description
		if (strlen($description) > 2) {
			$OutputResultsBuffer .= "<div class=\"description\">";
			$OutputResultsBuffer .= PrintHighlightDescription(rtrim($description));
			$OutputResultsBuffer .= "</div>\n";
		}
	}

	if ($DisplayContext == 1 && $output[$arrayline][2] > 0 && $IsEmptyMetaQuery == false)
	{
		// Extract contextual page content
		$context_keywords = $output[$arrayline][2]; // # of terms matched

		if ($context_keywords > $MaxContextKeywords)
			$context_keywords = $MaxContextKeywords;

		$context_word_count = ceil($ContextSize / $context_keywords);

		$goback = floor($context_word_count / 2);
		$gobackbytes = $goback * $DictIDLen;

		$last_startpos = 0;
		$first_startpos = 0;
		$last_endpos = 0;

		$FoundContext = 0;

		$OutputResultsBuffer .= "<div class=\"context\">\n";
		for ($j = 0; $j < $context_keywords && ($j == 0 || !feof($fp_pagetext)); $j++)
		{
			$origpos = $output[$arrayline][3 + $j];
			$startpos = $origpos;

			if ($gobackbytes < $startpos)
			{
				$startpos = $startpos - $gobackbytes;
				$noGoBack = false;
			}
			else
				$noGoBack = true;

			// Check that this will not overlap with previous extract
			if (($startpos > $last_startpos || $startpos > $first_startpos) && $startpos < $last_endpos)
				$startpos = $last_endpos;   // we will just continue last extract if so.

			// find the pagetext pointed to
			fseek($fp_pagetext, $startpos);

			// remember the last start position
			$last_startpos = $startpos;
			if ($j == 0)
				$first_startpos = $startpos;

			$last_bytesread = 0;
			$bytesread = 0;

			$retDict = GetNextDictWord($fp_pagetext);
			$word_id = $retDict[0];
			$variant_index = $retDict[1];
			$bytesread += $DictIDLen;

			$contextArray = array_fill(0, $context_word_count, 0);
			$highlightArray = array_fill(0, $context_word_count, 0);

			for ($cti = 0; $cti < $context_word_count && !feof($fp_pagetext); $cti++)
			{
				if ($word_id == 0 || $word_id == 1 || $word_id >= $dict_count)    // check if end of page or section
				{
					// if end of page occurs AFTER word pointer (ie: reached next page)
					if ($noGoBack || ($startpos+$bytesread) > $origpos)
						break;          // then we stop.
					else                // if end of page occurs BEFORE word pointer (ie: reached previous page)
					{
						//$context_str = "";// then we clear the existing context buffer we've created.
						$contextArray = array_fill(0, $context_word_count, 0);	// then we clear the existing context buffer we've created.
						$cti = 0;
					}
				}
				else
				{
					if ($word_id >= $NumKeywords)
					{
						$OutputResultsBuffer .= "Critical error with pagetext file.  Check that your files are from the same indexing session.";
					}
					else
					{
						if ($Highlighting == 1 && $IsEmptyMetaQuery == false && ($startpos+$last_bytesread) == $origpos)
							$highlightArray[$cti] = 1;

						$contextArray[$cti] = array();
						$contextArray[$cti][0] = $word_id;
						$contextArray[$cti][1] = $variant_index;
					}
				}
				$last_bytesread = $bytesread;

				$retDict = GetNextDictWord($fp_pagetext);
				$word_id = $retDict[0];
				$variant_index = $retDict[1];
				$bytesread += $DictIDLen;
			}

			// remember the last end position (if not already at end of page)
			if ($word_id != 0)
				$last_endpos = ftell($fp_pagetext);

			if ($Highlighting == 1)
			{
				HighlightContextArray($context_word_count);
			}

			$prev_word_id = 0;
			$context_str = "";
			$noSpaceForNextChar = false;

			for ($cti = 0; $cti < $context_word_count && !feof($fp_pagetext); $cti++)
			{
				if ($contextArray[$cti] == 0)
					continue;

				$word_id = $contextArray[$cti][0];
				$variant_index = $contextArray[$cti][1];

				if ($noSpaceForNextChar == false)
				{
					// No space for reserved words (punctuation, etc)
					if ($word_id > $DictReservedNoSpaces)
					{
						if ($prev_word_id <= $DictReservedPrefixes || $prev_word_id > $DictReservedNoSpaces)
							$context_str .= " ";
					}
					elseif  ($word_id > $DictReservedSuffixes && $word_id <= $DictReservedPrefixes)
					{
						// This is a Prefix character
						$context_str .= " ";
						$noSpaceForNextChar = true;
					}
					elseif ($word_id > $DictReservedPrefixes)   // this is a nospace character
						$noSpaceForNextChar = true;
				}
				else
					$noSpaceForNextChar = false;

				if ($word_id > 0)
				{
					if ($Highlighting == 1 &&
						($highlightArray[$cti] == $HIGHLIGHT_SINGLE || $highlightArray[$cti] == $HIGHLIGHT_START))
						$context_str .= "<span class=\"highlight\">";

					$context_str .= GetDictionaryWord($word_id, $variant_index);

					if ($Highlighting == 1 &&
						($highlightArray[$cti] == $HIGHLIGHT_SINGLE || $highlightArray[$cti] == $HIGHLIGHT_END))
						$context_str .= "</span>";

					$prev_word_id = $word_id;
				}
			}


			if (strcmp(trim($context_str), trim($title)) == 0)
			{
				$context_str = ""; // clear the string if its identical to the title
			}

			if ($context_str != "")
			{
				$OutputResultsBuffer .= " <b>...</b> ";
				$FoundContext = 1;
				//$context_str = htmlspecialchars($context_str);
				$OutputResultsBuffer .= $context_str;
				//$OutputResultsBuffer .= PrintHighlightDescription($context_str);
			}
		}
		if ($FoundContext == 1)
			$OutputResultsBuffer .= " <b>...</b>";
		$OutputResultsBuffer .= "</div>\n";
	}

	$info_str = "";

	if ($DisplayTerms == 1)
	{
		$info_str .= $STR_RESULT_TERMS_MATCHED . " ". $output[$arrayline][2];
	}

	if ($DisplayScore == 1)
	{
		if (strlen($info_str) > 0)
			$info_str .= "&nbsp; - &nbsp;";
		$info_str .= $STR_RESULT_SCORE . " " . $score;
	}

	if ($DisplayDate == 1 && $pageinfo[$ipage]["datetime"] > 0)
	{
		if (strlen($info_str) > 0)
			$info_str .= "&nbsp; - &nbsp;";
		$info_str .= date("j M Y", $pageinfo[$ipage]["datetime"]);
	}

	if ($DisplayFilesize == 1)
	{
		if (strlen($info_str) > 0)
			$info_str .= "&nbsp; - &nbsp;";
		$filesize = $pageinfo[$ipage]["filesize"]/1024;
		if ($filesize == 0)
			$filesize = 1;
		$info_str .= number_format($filesize) . "k";
	}

	if ($DisplayURL == 1)
	{
		if (strlen($info_str) > 0)
			$info_str .= "&nbsp; - &nbsp;";

		$url = rtrim($url);
		if ($TruncateShowURL > 0)
		{
			if (strlen($url) > $TruncateShowURL)
				$url = substr($url, 0, $TruncateShowURL) . "...";
		}
		$info_str .= $STR_RESULT_URL . " ".$url;
	}

	$OutputResultsBuffer .= "<div class=\"infoline\">";
	$OutputResultsBuffer .= $info_str;
	$OutputResultsBuffer .= "</div>\n";

	$OutputResultsBuffer .= "</div>";

	$arrayline++;
}

if ($DisplayContext == 1 || $AllowExactPhrase == 1)
	fclose($fp_pagetext);

fclose($fp_pagedata);

$OutputResultsBuffer .= "</div>"; // end of results style tag

// Show links to other result pages
if ($num_pages > 1)
{
	// 10 results to the left of the current page
	$start_range = $page - 10;
	if ($start_range < 1)
		$start_range = 1;

	// 10 to the right
	$end_range = $page + 10;
	if ($end_range > $num_pages)
		$end_range = $num_pages;

	$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<div class=\"result_pages\">\n" . $STR_RESULT_PAGES . " ";
	if ($page > 1)
		$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_page=".($page-1)."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">&lt;&lt; " . $STR_RESULT_PAGES_PREVIOUS . "</a> ";
	for ($i = $start_range; $i <= $end_range; $i++)
	{
		if ($i == $page)
			$OutputBuffers[$OUTPUT_PAGENUMBERS] .= $page." ";
		else
			$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_page=".($i)."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">".$i."</a> ";
	}
	if ($page != $num_pages)
		$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<a href=\"".$SelfURL.$LinkBackJoinChar."zoom_query=".$queryForURL.$metaParams."&amp;zoom_page=".($page+1)."&amp;zoom_per_page=".$per_page.$query_zoom_cats."&amp;zoom_and=".$and."&amp;zoom_sort=".$sort."\">" . $STR_RESULT_PAGES_NEXT . " &gt;&gt;</a> ";
	$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "</div>";
}

//Let others know about Zoom.
if ($ZoomInfo == 1)
	$OutputBuffers[$OUTPUT_PAGENUMBERS] .= "<center><p class=\"zoom_advertising\"><small>" . $STR_POWEREDBY . " <a href=\"http://www.wrensoft.com/zoom/\" target=\"_blank\"><b>Zoom Search Engine</b></a></small></p></center>";


if ($Timing == 1 || $Logging == 1)
{
	$mtime = explode(" ", microtime());
	$endtime   = doubleval($mtime[1]) + doubleval($mtime[0]);
	$difference = abs($starttime - $endtime);
	$timetaken = number_format($difference, 3, '.', '');
	if ($Timing == 1)
		$OutputBuffers[$OUTPUT_SEARCHTIME] .= "<div class=\"searchtime\"><br /><br />" . $STR_SEARCH_TOOK . " " . $timetaken . " " . $STR_SECONDS . ".</div>\n";
}

//Log the search words, if required
if ($Logging == 1)
{
	$LogQuery = str_replace("\"", "\"\"", $query);
	if (isset($_SERVER['HTTP_X_FORWARDED_FOR']))
	{
		$ip_addr = $_SERVER['HTTP_X_FORWARDED_FOR'];
		$ip_array = explode(",", $ip_addr);
		if (count($ip_array) > 0)
			$ip_addr = trim($ip_array[0]);	// get first IP if there are multiple addresses
	}
	else
		$ip_addr = $_SERVER['REMOTE_ADDR'];
	$LogString = Date("Y-m-d, H:i:s") . ", " . $ip_addr . ", \"" .$LogQuery  . "\", Matches = " . $matches;
	if ($and == 1)
		$LogString = $LogString . ", AND";
	else
		$LogString = $LogString . ", OR";

	if ($NewSearch == 1)
		$page = 0;

	$LogString = $LogString . ", PerPage = " . $per_page . ", PageNum = " . $page;

	if ($UseCats == 0)
		$LogString = $LogString . ", No cats";
	else
	{
		if ($cat[0] == -1)
			$LogString = $LogString . ", \"Cat = All\"";
		else
		{
			$LogString = $LogString . ", \"Cat = ";
			for ($cati = 0; $cati < $num_zoom_cats; $cati++)
			{
				if ($cati > 0)
					$LogString = $LogString . ", ";
				$logCatStr = trim($catnames[$cat[$cati]]);
				$logCatStr = str_replace("\"", "\"\"", $logCatStr);
				$LogString = $LogString . $logCatStr;
			}
			$LogString = $LogString . "\"";
		}
	}
	$LogString = $LogString . ", Time = " . $timetaken;

	$LogString = $LogString . ", Rec = " . $num_recs_found;

	// end of entry
	$LogString = $LogString . "\r\n";

	$fp = fopen ($LogFileName, "ab");
	if ($fp != false)
	{
		fputs ($fp, $LogString);
		fclose ($fp);
	}
	else
	{
		$OutputResultsBuffer .= "Unable to write to log file (" . $LogFileName . "). Check that you have specified the correct log filename in your Indexer settings and that you have the required file permissions set.<br />";
	}
}

//Print out the end of the template
ShowTemplate();


// ----------------------------------------------------------------------------------
// Porter Stemming algorithm by Dr Martin Porter.
// PHP5 implementation by Richard Heyes, copyright 2005.
// PHP4 support and additional features by Wrensoft, copyright 2009.
// The PorterStemmer class is available for use "free of charge for any purpose" as
// published on Martin Porter's website (http://tartarus.org/~martin/PorterStemmer/)
// ----------------------------------------------------------------------------------
class PorterStemmer
{
	var $regex_consonant = '(?:[bcdfghjklmnpqrstvwxz]|(?<=[aeiou])y|^y)';
	var $regex_vowel = '(?:[aeiou]|(?<![aeiou])y)';
	var $StemStopChars = '`1234567890-=[]\\;\',./~!@#$%^&*_+|:"<>?';

	function Stem($word)
	{
		if (strlen($word) <= 2) {
			return $word;
		}

		if (strcspn($word, $this->StemStopChars) < strlen($word))
			return $word;

		$word = $this->step1ab($word);
		$word = $this->step1c($word);
		$word = $this->step2($word);
		$word = $this->step3($word);
		$word = $this->step4($word);
		$word = $this->step5($word);

		return $word;
	}

	function step1ab($word)
	{
		// Part a
		if (substr($word, -1) == 's') {

			   $this->replace($word, 'sses', 'ss')
			OR $this->replace($word, 'ies', 'i')
			OR $this->replace($word, 'ss', 'ss')
			OR $this->replace($word, 's', '');
		}

		// Part b
		if (substr($word, -2, 1) != 'e' OR !$this->replace($word, 'eed', 'ee', 0)) { // First rule
			$v = $this->regex_vowel;

			// ing and ed
			if (   preg_match("#$v+#", substr($word, 0, -3)) && $this->replace($word, 'ing', '')
				OR preg_match("#$v+#", substr($word, 0, -2)) && $this->replace($word, 'ed', '')) { // Note use of && and OR, for precedence reasons

				// If one of above two test successful
				if (    !$this->replace($word, 'at', 'ate')
					AND !$this->replace($word, 'bl', 'ble')
					AND !$this->replace($word, 'iz', 'ize')) {

					// Double consonant ending
					if (    $this->doubleConsonant($word)
						AND substr($word, -2) != 'll'
						AND substr($word, -2) != 'ss'
						AND substr($word, -2) != 'zz') {

						$word = substr($word, 0, -1);

					} else if ($this->m($word) == 1 AND $this->cvc($word)) {
						$word .= 'e';
					}
				}
			}
		}
		return $word;
	}

	function step1c($word)
	{
		$v = $this->regex_vowel;

		if (substr($word, -1) == 'y' && preg_match("#$v+#", substr($word, 0, -1))) {
			$this->replace($word, 'y', 'i');
		}

		return $word;
	}

	function step2($word)
	{
		switch (substr($word, -2, 1)) {
			case 'a':
				   $this->replace($word, 'ational', 'ate', 0)
				OR $this->replace($word, 'tional', 'tion', 0);
				break;

			case 'c':
				   $this->replace($word, 'enci', 'ence', 0)
				OR $this->replace($word, 'anci', 'ance', 0);
				break;

			case 'e':
				$this->replace($word, 'izer', 'ize', 0);
				break;

			case 'g':
				$this->replace($word, 'logi', 'log', 0);
				break;

			case 'l':
				   $this->replace($word, 'entli', 'ent', 0)
				OR $this->replace($word, 'ousli', 'ous', 0)
				OR $this->replace($word, 'alli', 'al', 0)
				OR $this->replace($word, 'bli', 'ble', 0)
				OR $this->replace($word, 'eli', 'e', 0);
				break;

			case 'o':
				   $this->replace($word, 'ization', 'ize', 0)
				OR $this->replace($word, 'ation', 'ate', 0)
				OR $this->replace($word, 'ator', 'ate', 0);
				break;

			case 's':
				   $this->replace($word, 'iveness', 'ive', 0)
				OR $this->replace($word, 'fulness', 'ful', 0)
				OR $this->replace($word, 'ousness', 'ous', 0)
				OR $this->replace($word, 'alism', 'al', 0);
				break;

			case 't':
				   $this->replace($word, 'biliti', 'ble', 0)
				OR $this->replace($word, 'aliti', 'al', 0)
				OR $this->replace($word, 'iviti', 'ive', 0);
				break;
		}
		return $word;
	}

	function step3($word)
	{
		switch (substr($word, -2, 1)) {
			case 'a':
				$this->replace($word, 'ical', 'ic', 0);
				break;

			case 's':
				$this->replace($word, 'ness', '', 0);
				break;

			case 't':
				   $this->replace($word, 'icate', 'ic', 0)
				OR $this->replace($word, 'iciti', 'ic', 0);
				break;

			case 'u':
				$this->replace($word, 'ful', '', 0);
				break;

			case 'v':
				$this->replace($word, 'ative', '', 0);
				break;

			case 'z':
				$this->replace($word, 'alize', 'al', 0);
				break;
		}

		return $word;
	}

	function step4($word)
	{
		switch (substr($word, -2, 1)) {
			case 'a':
				$this->replace($word, 'al', '', 1);
				break;

			case 'c':
				   $this->replace($word, 'ance', '', 1)
				OR $this->replace($word, 'ence', '', 1);
				break;

			case 'e':
				$this->replace($word, 'er', '', 1);
				break;

			case 'i':
				$this->replace($word, 'ic', '', 1);
				break;

			case 'l':
				   $this->replace($word, 'able', '', 1)
				OR $this->replace($word, 'ible', '', 1);
				break;

			case 'n':
				   $this->replace($word, 'ant', '', 1)
				OR $this->replace($word, 'ement', '', 1)
				OR $this->replace($word, 'ment', '', 1)
				OR $this->replace($word, 'ent', '', 1);
				break;

			case 'o':
				if (substr($word, -4) == 'tion' OR substr($word, -4) == 'sion') {
				   $this->replace($word, 'ion', '', 1);
				} else {
					$this->replace($word, 'ou', '', 1);
				}
				break;

			case 's':
				$this->replace($word, 'ism', '', 1);
				break;

			case 't':
				   $this->replace($word, 'ate', '', 1)
				OR $this->replace($word, 'iti', '', 1);
				break;

			case 'u':
				$this->replace($word, 'ous', '', 1);
				break;

			case 'v':
				$this->replace($word, 'ive', '', 1);
				break;

			case 'z':
				$this->replace($word, 'ize', '', 1);
				break;
		}

		return $word;
	}

	function step5($word)
	{
		// Part a
		if (substr($word, -1) == 'e') {
			if ($this->m(substr($word, 0, -1)) > 1) {
				$this->replace($word, 'e', '');

			} else if ($this->m(substr($word, 0, -1)) == 1) {

				if (!$this->cvc(substr($word, 0, -1))) {
					$this->replace($word, 'e', '');
				}
			}
		}

		// Part b
		if ($this->m($word) > 1 AND $this->doubleConsonant($word) AND substr($word, -1) == 'l') {
			$word = substr($word, 0, -1);
		}

		return $word;
	}

	function replace(&$str, $check, $repl, $m = null)
	{
		$len = 0 - strlen($check);

		if (substr($str, $len) == $check) {
			$substr = substr($str, 0, $len);
			if (is_null($m) OR $this->m($substr) > $m) {
				$str = $substr . $repl;
			}

			return true;
		}

		return false;
	}

	function m($str)
	{
		$c = $this->regex_consonant;
		$v = $this->regex_vowel;

		$str = preg_replace("#^$c+#", '', $str);
		$str = preg_replace("#$v+$#", '', $str);

		preg_match_all("#($v+$c+)#", $str, $matches);

		return count($matches[1]);
	}

	function doubleConsonant($str)
	{
		$c = $this->regex_consonant;

		return preg_match("#$c{2}$#", $str, $matches) AND $matches[0]{0} == $matches[0]{1};
	}

	function cvc($str)
	{
		$c = $this->regex_consonant;
		$v = $this->regex_vowel;

		return     preg_match("#($c$v$c)$#", $str, $matches)
			   AND strlen($matches[1]) == 3
			   AND $matches[1]{2} != 'w'
			   AND $matches[1]{2} != 'x'
			   AND $matches[1]{2} != 'y';
	}
}

?>
