#include "cescape.h"
/*
comparison with cgi.escape:
	0.16 vs 0.30 seconds for bytes
	0.26 vs 0.61 seconds for unicode
cgi.escape can handle a little larger strings, where malloc in escape_html() would fail
on "'": http://stackoverflow.com/questions/2083754/why-shouldnt-apos-be-used-to-escape-single-quotes
*/

/** replaces &, <, >, ", ' with html character entities
	use it to sanitize user input on websites
	returns a new dynamically allocated string */
inline char* escape_html(char* bstr) {
	/*	worst case: only '"' characters, which would be replaced by "&quot;" each; */
	char *nstr = (char *)malloc(6 * strlen(bstr) + 1);
	if(nstr == NULL) return NULL; // make shure to raise Exception!
	char *bptr = bstr;
	char *nptr = nstr;
	while(*bptr) {
		if (*bptr == '&') { strcat(nptr, "&amp;"); nptr += 4; }
		else if (*bptr == '<') { strcat(nptr, "&lt;"); nptr += 3; }
		else if (*bptr == '>') { strcat(nptr, "&gt;"); nptr += 3; }
		else if (*bptr == '"') { strcat(nptr, "&quot;"); nptr += 5; }
		else if (*bptr == '\'') { strcat(nptr, "&#39;"); nptr += 4; }
		else *nptr = *bptr;
		bptr++;
		nptr++;
	}
	*nptr = '\0';
	return nstr;
}

/*
#include "stdio.h"
int main()
{
	char *tstring = "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\"  \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">"
	"<html xmlns=\"http://www.w3.org/1999/xhtml\">  <head>	<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />		"
	"<title>Profiling &mdash; Cython 0.16 documentation</title>		<link rel=\"stylesheet\" href=\"../../_static/default.css\" type=\"text/css\" />"
	"	<link rel=\"stylesheet\" href=\"../../_static/pygments.css\" type=\"text/css\" />		<script type=\"text/javascript\">	  var DOCUMENTATION_OPTIONS "
	"= {		URL_ROOT:	'../../',		VERSION:	 '0.16',		COLLAPSE_INDEX: false,		FILE_SUFFIX: '.html',		HAS_SOURCE:  true	  };  "
	"  </script>	<script type=\"text/javascript\" src=\"../../_static/jquery.js\"></script>	<script type=\"text/javascript\" src=\"../../_static/undersc"
	"ore.js\"></script>	<script type=\"text/javascript\" src=\"../../_static/doctools.js\"></script>	<link rel=\"shortcut icon\" href=\"../../_static/favic"
	"on.ico\"/>	<link rel=\"top\" title=\"Cython 0.16 documentation\" href=\"../../index.html\" />	<link rel=\"up\" title=\"Tutorials\" href=\"index.html\" /> "
	"   <link rel=\"next\" title=\"Unicode and passing strings\" href=\"strings.html\" />	<link rel=\"prev\" title=\"Caveats\" href=\"caveats.html\" />   </head"
	">  <body>	<div class=\"related\">	  <h3>Navigation</h3>	  <ul>		<li class=\"right\" style=\"margin-right: 10px\">	   "
	"   <a href=\"strings.html\" title=\"Unicode and passing strings\"			 accesskey=\"N\">next</a></li>		<li class=\"right\" >		"
	"  <a href=\"caveats.html\" title=\"Caveats\"			 accesskey=\"P\">previous</a> |</li>		<li><a href=\"../../index.html\">Cytho"
	"n 0.16 documentation</a> &raquo;</li>		  <li><a href=\"index.html\" accesskey=\"U\">Tutorials</a> &raquo;</li>	   </ul>	</di"
	"v>	  <div class=\"document\">	  <div class=\"documentwrapper\">		<div class=\"bodywrapper\">		  <div class=\"body\">	 "
	"		 <div class=\"section\" id=\"profiling\"><span id=\"id1\"></span><h1>Profiling<a class=\"headerlink\" href=\"#profiling\" title=\"Permalin"
	"k to this headline\">¶</a></h1><p>This part describes the profiling abilities of Cython. If you are familiarwith profiling pure Python code, you c"
	"an only read the first section(<a class=\"reference internal\" href=\"#profiling-basics\"><em>Cython Profiling Basics</em></a>\n";
	printf("%s", escape_html(tstring));
	return 0;
}
*/
