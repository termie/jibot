"""Python interface for doing jargon file lookups."""

import re, urllib, time, cgi

glossary_timestamp = 0
glossary_data = ''
glossary = 'http://www.catb.org/~esr/jargon/html/go01.html'
prefix = 'http://www.catb.org/~esr/jargon/html/'

href = re.compile(r'href=".*?"')

def get_glossary():
    """Returns the glossary, fetches it if necessary."""
    global glossary_timestamp, glossary_data
    if glossary_timestamp > time.time() - 86400:
        return glossary_data
    else:
        glossary_data = urllib.urlopen(glossary).read()
        glossary_timestamp = time.time()
        return glossary_data

def find(message):
	"""Does a search for entry in the jargon file."""
        entry = re.compile('<a href=".*?/.*?">%s</a>' % cgi.escape(message), re.I)
        start = 0
        result = None
        data = get_glossary()
        # Searching for dt tags is done manually, because
        # python barfs with a RuntimeError on regular expression
        # searches..
        while 1:
            next =  data.find('<dt>', start)
            if next > -1:
                end = data.find('</dt>', next)
                result = entry.search(data[next:end])
		if result:
	            link = href.search(result.group()).group()[6:-1]
                    return prefix + link
                start = end
            else:
                return "Nothing found in the jargon file for %s" % message
                

if __name__ == '__main__':
	x = find("linux")
 	print x
