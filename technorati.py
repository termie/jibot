"""Python wrapper for Technorati web APIs

This module allows you to access Technorati's web APIs,
to search Technorati and get the results programmatically.
Described here:
  http://www.sifry.com/alerts/archives/000288.html

You need a Technorati-provided license key to use these services,
available here:
  http://www.technorati.com/members/apikey.html

The functions in this module will look in several places (in this order)
for the license key:
- the "license_key" argument of each function
- the module-level LICENSE_KEY variable (call setLicense once to set it)
- an environment variable called TECHNORATI_LICENSE_KEY
- a file called ".technoratikey" in the current directory
- a file called "technoratikey.txt" in the current directory
- a file called ".technoratikey" in your home directory
- a file called "technoratikey.txt" in your home directory
- a file called ".technoratikey" in the same directory as technorati.py
- a file called "technoratikey.txt" in the same directory as technorati.py

Sample usage:
>>> import technorati
>>> technorati.setLicense('...') # must get your own key!
>>> cosmos = technorati.cosmos('http://diveintomark.org/')
>>> cosmos.name
u'Dive Into Mark'
>>> cosmos.url
u'http://diveintomark.org'
>>> cosmos.rssurl
u'http://diveintomark.org/xml/rss.xml'
>>> cosmos.inboundlinks
1379
>>> cosmos.inboundblogs
819
>>> cosmos.lastupdate
(2003, 5, 12, 5, 48, 51, 0, 0, 0)
>>> for blogThatLinksToMine in cosmos.item:
...     print blogThatLinksToMine.name
...     print blogThatLinksToMine.url
...     print blogThatLinksToMine.rssurl
...     print blogThatLinksToMine.inboundlinks
...     print blogThatLinksToMine.inboundblogs
...     print blogThatLinksToMine.lastupdate
...     print blogThatLinksToMine.nearestpermalink
...     print blogThatLinksToMine.excerpt
...     print blogThatLinksToMine.linkcreated

Other functions:
>>> outboundlinks = technorati.outbound('http://diveintomark.org/')
>>> info = technorati.bloginfo('http://diveintomark.org/')

Other usage notes:
- Most functions can take product_line as well, see source for possible values
- All functions can take page=N to get second, third, fourth page of results
- All functions can take license_key="XYZ", instead of setting it globally
- All functions can take http_proxy="http://x/y/z" which overrides your system setting
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__version__ = "0.1"
__cvsversion__ = "$Revision: 2.0 $"[11:-2]
__date__ = "$Date: 2004/04/22 18:32:24 $"[7:-2]
__copyright__ = "Copyright (c) 2003 Mark Pilgrim"
__license__ = "Python"

from xml.dom import minidom
import os, sys, urllib, re
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass

LICENSE_KEY = None
HTTP_PROXY = None
DEBUG = 0

# don't touch the rest of these constants
class TechnoratiError(Exception): pass
class NoLicenseKey(Exception): pass
_keyfile1 = ".technoratikey"
_keyfile2 = "technoratikey.txt"
_licenseLocations = (
    (lambda key: key, 'passed to the function in license_key variable'),
    (lambda key: LICENSE_KEY, 'module-level LICENSE_KEY variable (call setLicense to set it)'),
    (lambda key: os.environ.get('TECHNORATI_LICENSE_KEY', None), 'an environment variable called TECHNORATI_LICENSE_KEY'),
    (lambda key: _contentsOf(os.getcwd(), _keyfile1), '%s in the current directory' % _keyfile1),
    (lambda key: _contentsOf(os.getcwd(), _keyfile2), '%s in the current directory' % _keyfile2),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _keyfile1), '%s in your home directory' % _keyfile1),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _keyfile2), '%s in your home directory' % _keyfile2),
    (lambda key: _contentsOf(_getScriptDir(), _keyfile1), '%s in the technorati.py directory' % _keyfile1),
    (lambda key: _contentsOf(_getScriptDir(), _keyfile2), '%s in the technorati.py directory' % _keyfile2)
    )

## administrative functions
def version():
    print """PyTechnorati %(__version__)s
%(__copyright__)s
released %(__date__)s
""" % globals()

## utility functions
def setLicense(license_key):
    """set license key"""
    global LICENSE_KEY
    LICENSE_KEY = license_key

def getLicense(license_key = None):
    """get license key

    license key can come from any number of locations;
    see module docs for search order"""
    for get, location in _licenseLocations:
        rc = get(license_key)
        if rc: return rc
    raise NoLicenseKey, 'get a license key at http://www.technorati.com/members/apikey.html'

def setProxy(http_proxy):
    """set HTTP proxy"""
    global HTTP_PROXY
    HTTP_PROXY = http_proxy

def getProxy(http_proxy = None):
    """get HTTP proxy"""
    return http_proxy or HTTP_PROXY

def getProxies(http_proxy = None):
    http_proxy = getProxy(http_proxy)
    if http_proxy:
        proxies = {"http": http_proxy}
    else:
        proxies = None
    return proxies

def _contentsOf(dirname, filename):
    filename = os.path.join(dirname, filename)
    if not os.path.exists(filename): return None
    fsock = open(filename)
    contents = fsock.read()
    fsock.close()
    return contents

def _getScriptDir():
    if __name__ == '__main__':
        return os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        return os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))

class Bag: pass

_intFields = ('inboundblogs', 'inboundlinks', 'rankingstart')
_dateFields = ('lastupdate', 'linkcreated')
_listFields = ('item', )
def unmarshal(element):
    rc = Bag()
    childElements = [e for e in element.childNodes if isinstance(e, minidom.Element)]
    if childElements:
        for child in childElements:
            key = child.tagName
            if DEBUG: print key
            if hasattr(rc, key):
                if key in _listFields:
                    setattr(rc, key, getattr(rc, key) + [unmarshal(child)])
            elif isinstance(child, minidom.Element) and (child.tagName in ('result', 'weblog')):
                rc = unmarshal(child)
            elif key in _listFields:
                setattr(rc, key, [unmarshal(child)])
            else:
                setattr(rc, key, unmarshal(child))
    else:
        rc = "".join([e.data for e in element.childNodes if isinstance(e, minidom.Text)])
        if str(element.tagName) in _intFields:
            rc = int(rc)
        elif str(element.tagName) in _dateFields:
            year, month, day, hour, minute, second = re.search(r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})', rc).groups()
            rc = (int(year), int(month), int(day), int(hour), int(minute), int(second), 0, 0, 0)
    return rc

def _buildCosmosURL(url, search_type, start, format, version, license_key):
    cosmosURL = "http://api.technorati.com/cosmos?type=%(search_type)s&start=%(start)s&format=%(format)s&version=%(version)s&key=%(license_key)s" % vars()
    cosmosURL += "&url=%s" % urllib.quote(url)
    return cosmosURL

def _buildOtherURL(func_type, url, license_key):
    otherURL = "http://api.technorati.com/%(func_type)s?key=%(license_key)s" % vars()
    otherURL += "&url=%s" % urllib.quote(url)
    return otherURL

def _buildSearch(query, start, format, license_key):
    searchUrl = "http://api.technorati.com/search?query=%(query)s&start=%(start)s&format=%(format)s&key=%(license_key)s" % vars()
    return searchUrl

## main functions

def cosmos(url, start=0, search_type='link', format='xml', version='0.9', license_key=None, http_proxy=None):
    """search Technorati

    You need a license key to call this function; see
    http://www.technorati.com/members/apikey.html
    to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.
    """
    license_key = getLicense(license_key)
    url = _buildCosmosURL(url, search_type, start, format, version, license_key)
    proxies = getProxies(http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    rawdata = usock.read()
    if DEBUG: print rawdata
    xmldoc = minidom.parseString(rawdata)
    usock.close()
    data = unmarshal(xmldoc).tapi.document
#    if hasattr(data, 'ErrorMsg'):
    if 0:
        raise TechnoratiError, data
    else:
        return data

def _do(func_type, url, license_key, http_proxy):
    license_key = getLicense(license_key)
    url = _buildOtherURL(func_type, url, license_key)
    proxies = getProxies(http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    rawdata = usock.read()
    if DEBUG: print rawdata
    xmldoc = minidom.parseString(rawdata)
    usock.close()
    data = unmarshal(xmldoc).tapi.document
#    if hasattr(data, 'ErrorMsg'):
    if 0:
        raise TechnoratiError, data
    else:
        return data
    
def outbound(url, license_key=None, http_proxy=None):
    return _do('outbound', url, license_key, http_proxy)

def bloginfo(url, license_key=None, http_proxy=None):
    return _do('bloginfo', url, license_key, http_proxy)

def search(query, start=0, format='xml', license_key=None, http_proxy=None):
    """search Technorati

    You need a license key to call this function; see
    http://www.technorati.com/members/apikey.html
    to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.
    """
    license_key = getLicense(license_key)
    encodedQuery = urllib.quote(query)
    url = _buildSearch(encodedQuery, start, format, license_key)
    print url
    proxies = getProxies(http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    rawdata = usock.read()
    if DEBUG: print rawdata
    xmldoc = minidom.parseString(rawdata)
    usock.close()
    data = unmarshal(xmldoc).tapi.document
#    if hasattr(data, 'ErrorMsg'):
    if 0:
        raise TechnoratiError, data
    else:
        return data
