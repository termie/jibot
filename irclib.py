#!/usr/bin/env python

# Copyright (C) 1999  Erno Kuusela <erno@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# $Id: irclib.py,v 1.2 2003/10/08 23:35:17 kevinmarks Exp $


'''
there are two ways to use this module.

a) use the IrcMessage class just to get/send messages

use get_msg()/send() to receive/send messages and select()
to take care of nonblocking io (the irc class provides a
fileno method so you can just pass it to the select function).
then you get to implement your own main loop. it is good
if you need to integrate irclib into a bigger app.
this mode of operation has not been tested much.

b) use the do_ callbacks

The simpleclient class demonstrates how to use this.
(see simpleclient.py) It works a bit like sgmllib/htmllib.
Subclass the irc class and define methods for commands that you
want to handle. When a command is received
a suitably named method (do_commandname) is looked up and if found, called.
An instance of msg is passed to it, representing the message.
If no suitable method is found, the do_default method is called.

'''

import string, os, sys, errno, socket, re

class IrcError(Exception):
    pass

class IrcNetworkError(IrcError):
    pass

class AllYourBaseAreBelongToUs(IrcError):
    pass

class ConnectionClosed(IrcNetworkError):
    pass

ALPHACHARS = 'abcdefghijklmnopqrstuvwxyz'
SPECIALCHARS = '-[]\\`^{}'
NICKCHARS = ALPHACHARS + string.upper(ALPHACHARS) + string.digits + \
        SPECIALCHARS

_lowertrans = string.maketrans(string.upper(ALPHACHARS) + '[]\\',
                   ALPHACHARS + '{}|')

def lowernick(n):
    return string.translate(n, _lowertrans)

def samenick(a, b):
    return string.translate(a, _lowertrans) == \
           string.translate(b, _lowertrans)


class IrcConnection:
    do_any = None
    def __init__(self):
        self.debug = 0
        self.socket = socket.socket(socket.AF_INET,
                                    socket.SOCK_STREAM)

    def connect(self, server, port = 6667):
        
        if self.debug: print 'connecting'
        try:
            self.socket.connect((server, port))
        except socket.error, why:
            if why[0] in (errno.EWOULDBLOCK, errno.EINPROGRESS):
                pass
            else:
                raise IrcNetworkError, why
        self.sockf = self.socket.makefile('r', 0)
        self.server, self.port = server, port


    def fileno(self):
        return self.socket.fileno()

    def loop(self):
        while 1:
            if self.debug: print 'loop'
            self.do_one_msg()

    def do_one_msg(self):
        m = self.get_msg()
        if self.debug: print 'got msg', m
        attr = 'do_' + string.lower(m.command)
        if self.do_any:
            self.do_any(m)
        if hasattr(self, attr):
            handlermethod = getattr(self, attr)
            handlermethod(m)
        else:
            self.do_default(m)

    def get_msg(self):
        m = IrcMessage()
        l = self.sockf.readline()
        if not l:
            raise ConnectionClosed, 'connection closed'
        m.from_string(l)
        if self.debug: print 'got msg:', m
        return m

    def do_default(self, m):
        "override me!"
        print 'default handler:', m

    def send(self, m):
        if self.debug: print 'send', m
        try:
            self.socket.send(m.to_string())
        except socket.error, why:
            raise IrcNetworkError, why

    def disconnect(self):
        self.socket.close()

irc = IrcConnection # for backwards compatibility

## <message>  ::= [':' <prefix> <SPACE> ] <command> <params> <crlf>
## <prefix>   ::= <servername> | <nick> [ '!' <user> ] [ '@' <host> ]
## <command>  ::= <letter> { <letter> } | <number> <number> <number>
## <SPACE>    ::= ' ' { ' ' }
## <params>   ::= <SPACE> [ ':' <trailing> | <middle> <params> ]

## <middle>   ::= <Any *non-empty* sequence of octets not including SPACE
##        or NUL or CR or LF, the first of which may not be ':'>
## <trailing> ::= <Any, possibly *empty*, sequence of octets not including
##          NUL or CR or LF>

## <crlf>     ::= CR LF

class MalformedMessageError(IrcError):
    pass

class UninitialisedMessageError(IrcError):
    pass

class IrcMessage:
    """
    has 3 public attributes: prefix, command and params.
    read the irc rfc to find out what they mean.
    prefix can be None if there is no prefix.

    you can construct one either by providing the attributes
    in arguments to the __init__ function, or by calling the
    from_string method. the latter parses a irc message
    (like the ones sent by irc servers). to_string does the
    reverse.
    """

    def __init__(self, prefix=None, command=None, params=()):
        if prefix is not None and ':' in prefix:
            raise MalformedMessageError, '":" in prefix'
        if type(params) == type(()):
            params = list(params)
        self.params = params
        self.command = command
        self.prefix = prefix


    def to_string(self):
        if self.command is None:
            raise UninitialisedMessageError, \
                  'attempt to use uninitialised message object'
        if self.prefix is not None:
            s = ':' + self.prefix + ' '
        else:
            s = ''
        s = s + self.command
        params = self.params[:]
        while len(params) > 1:
            s = s + ' ' + params[0]
            del params[0]
        if params:
            s = s + ' :' + params[0]
        return s + '\r\n'


    # XXX does not handle : characters embeddedin parmeters other than
    # "trailing". this happens a lot with ipv6 addresses.
    msgexp = re.compile(r'''
    ^                 # beginning of string
    (?P<prefix>       # this group matches the optional prefix part
      :               #    (leading ":
      [^\ \r\n]*      #     followed by any number of sensible letters)
                      #    OR
      |               #    (nothing)
    )

    (?:\ +)?          # optionally one or more spaces (non-grouping)

    (?P<middle>       # middle part of the message
     [^:\r\n]*        # just contains anything up to a ":"
    )
    
    (?P<trailing>     # optional last part of the message
      :[^\r\n]*       # (":" followed by anything)
                      # OR
      |               # (nothing)
    )

    \r?               # optional \r
    \n                # \n
    $                 # end of string
    ''', re.VERBOSE | re.MULTILINE | re.DOTALL)

    def from_string(self, buf):
        print 'from_string: %s' % repr(buf)
        mo = self.msgexp.match(buf)
        if mo is None:
            raise MalformedMessageError, \
                  'bad mesage: %s' % repr(buf)
        prefix, middle, last = mo.groups()
        #print (prefix, middle, last)
        self.prefix = prefix[1:] or None   # lose the leading ":"
        cmd_and_params = string.split(middle)
        cmd_and_params.append(last[1:])
        self.command = cmd_and_params[0]
        self.params = cmd_and_params[1:]
        
    def sender_nick(self):
        return self._sender_uh(0)

    def sender_userhost(self):
        return self._sender_uh(1)

    def _sender_uh(self, i):
        if self.prefix and '!' in self.prefix:
            return string.split(self.prefix, '!', 1)[i]
        else:
            return None
        
    def __repr__(self):
        return 'msg(prefix=%s, command=%s, params=%s)' % \
               (repr(self.prefix), repr(self.command),
            repr(self.params))

msg = IrcMessage # for backwards compatibility
