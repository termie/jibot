#!/usr/bin/env python
import string, sys, os, re
import random, time, xmlrpclib
#from Crypto.Hash import MD5

import cgi
import technorati, rssparser, amazon, jargon, google
import irclib, socket, errno

class JibotInterface:
    def __init__(self,logger,config,**kwargs):
        self._socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_STREAM)
        self.logger = logger
        self._config = config
        self._handlers={}
        self._cur_channel=None
        self.server = self._config.get("global","server")
        self.port = self._config.getint("global","port")
        self._silent = self._config.getboolean("global","silent")
        self.cmd_chars = self._config.get("global","cmd_chars")
        self.server = self._config.get("global","server")
        self.nick = self._config.get("global","nick")
        self.ircname = self._config.get("global","ircname")
        self.user = self._config.get("global","user")
        self.speech = self._config.get("global","speech")
        self.channels = self._config.get("global","channels").split(",")
        self.bots = self._config.get("global","bots").split(",")
        self.bots_ignore = self._config.getboolean("global","bots_ignore")
        self.owners = self._config.get("global","owners").split(",")
        self.check_identification = config.getboolean("global","check_identification")
        self.identify = config.getboolean("global","identify")
        self.identify_key_file = config.get("global","identify_key_file")
        self._should_quit = False
        self._has_quit = False
        self.sanitizer = re.compile("[\x00-\x19\x7F-\xFF]") #done early as it
                                                            #will be used many
                                                            #times
        if self.identify:
            filename = os.path.join(os.getcwd(),self.identify_key_file)
            if os.path.exists(filename):
                f = open(filename)
                self._identify_password = f.read().strip()
                f.close()
                self.logger.info("Indentify password loaded successfully")
            else:
                self.logger.warn("Could not load identify password")
                self.identify = False
    
    def start(self):
        self.connect(self.server,self.port)
        self.send(JibotMessage(root=self,
                               command='USER',
                               params=[self.user,'localhost','localhost',self.ircname]))
        self.logger.info("Sending NICK %s"%(self.nick))
        self.send(JibotMessage(root=self,
                               command='NICK',
                               params=[self.nick]))
        if self.check_identification:
            self.logger.info("Sending QUOTE CAPAB IDENTIFY-MSG")
            self.send(JibotMessage(root=self,
                                   command='CAPAB',
                                   params=['IDENTIFY-MSG']))
        if self.identify:
            self.logger.info("Sending identify to NickServ")
            self.send(JibotMessage(root=self,
                                   command='PRIVMSG',
                                   params=['NickServ',"IDENTIFY %s"%(self._identify_password)]))
            
        for channel in self.channels:
            self.join("#"+channel)
        
    def connect(self,server=None,port=6667):
        if None == server:
            server = self.server
        self.server = server
        self.port = port
        try:
            self._socket.connect((server,port))
        except socket.error, why:
            if why[0] in (errno.EWOULDBLOCK, errno.EINPROGRESS):
                pass
            else:
                self.logger.exception("Could not connect to %s:%d"%(self.server,self.port))
                raise irclib.IrcNetworkError, why
        self._sockf = self._socket.makefile('r',0)
        self.server, self.port = server, port
        self.logger.info("Connected to %s:%d"%(self.server,self.port))

    def disconnect(self):
        self._socket.close()

    def fileno(self):
        return self._socket.fileno()

    def get_msg(self):
        # I want to make a self-targetting message object
        # so that it will hold with it all the information about
        # where it needs to go already, but until then, we'll
        # have to make due with the base object
        m = JibotMessage(root=self)
        line = self._sockf.readline()
        if not line:
            raise irclib.ConnectionClosed, 'Connection closed'
            return
        m.parse(line)
        return m

    def join(self,channel):
        self.send(JibotMessage(root=self,
                               command='JOIN',
                               params=[channel]))
        self.set_cur_channel(channel)
    
    def part(self,channel):
        self.send(JibotMessage(root=self,
                               command='PART',
                               params=[channel]))
        self.set_cur_channel(None)

    
    def send(self,m):
        try:
            self._socket.send(m.to_string())
        except socket.error, why:
            raise irclib.IrcNetworkError, why 
    
    def do_one_msg(self):
        try:
            m = self.get_msg()
        except irclib.ConnectionClosed,why:
            self.logger.exception("Connection was closed, exiting")
            self._should_quit=1
            return
        except:
            self.logger.exception("Could not read line from socket")
            return
        if self._handlers.has_key(m.command):
            self._handlers[m.command].handle(m)
        else:
            self.do_default(m)
                
        # recipient, text = m.params
        # text = text.strip()
        # sender = m.prefix
        # sendernick = string.split(sender, '!')[0]
        
    def do_default(self,m):
        pass
        
    def add_handler(self,hdlr):
        handles = hdlr.get_handles()
        for x in handles:
            self._handlers[x]=hdlr
            
    def set_cur_channel(self,chan):
        self._cur_channel=chan
    
    def set_silent(self,silent=None):
        if None == silent:
            if self._silent: self._silent=False
            else: self._silent=True
        else:
            if silent: self._silent=True
            else: self._silent=False
        if self._silent:
            self.say("Now being quiet")
        else:
            self.say("No longer being quiet")
   
    def say(self,s):
        if not self._cur_channel:
            return
        if self._silent:
            self.logger.info("%s in %s: %s"%(self.speech,self._cur_channel,s))
            return
        s = s.rstrip()
        self.send(JibotMessage(root=self,
                               command=self.speech,
                               params=[self._cur_channel,s]))
    
    def say_no_private(self,m):
        self.say("I can only do that in a channel")
    
    def say_only_owners(self,m):
        self.say("Only my owners can do that")

    def say_not_identified(self,m):
        self.say("Please identify yourself with NickServ")
    
    def action(self,s):
        if not self._cur_channel:
            return
        if self._silent:
            self.logger.info("ACTION in %s: %s"%(self._cur_channel,s))
            return
        s = s.rstrip()
        s = "\001ACTION "+s+"\001"
        self.send(JibotMessage(root=self,
                               command='PRIVMSG',
                               params=[self._cur_channel,s]))

    def quit(self,s):
        """ some irc networks have this problem with early quits, to prevent
		    bot attacks using the quit message, so we should probably check to see
		    if the bot quit early, and if so, just send a msg rather than the
		    quit line """
        # the quit message isn't showing up yet    
        s = s.rstrip()
        self.send(JibotMessage(root=self,
                               command="QUIT",
                               params=[s]))
        time.sleep(1.5)
        self._should_quit=True

    def pong(self,server):
        server = server.rstrip()
        self.send(JibotMessage(root=self,
                               command="PONG",
                               params=[server]))
                               
    def loop(self):
        import select
        while not self._should_quit:
            r, w, e = select.select([self],[],[])
            if self in r:
                self.do_one_msg()
            if self._has_quit:
                break

class JibotMessage(irclib.IrcMessage):
    def __init__(self,root,prefix=None,command=None,params=()):
        irclib.IrcMessage.__init__(self,prefix,command,params)
        self._root = root
        self.private = False
        self.ignore = False
        self.cmd = None
        self.identified = False

    def parse(self,line):
        self.from_string(line)
        self._root.logger.debug("Parsing: %s"%(line))
        if "JOIN" == self.command:
            self.channel = self.params[0]
        if "PRIVMSG" == self.command:
            self.recipient = self.params[0]
            self.text = self.params[1].strip()
            self.text = self.sanitize(self.text)
            self.sender_nick = self.sender_nick()
            if self.sender_nick in self._root.bots and self._root.bots_ignore:
                self.ignore = True
                return
            if self.recipient == self._root.nick:
                self.channel = self.sender_nick
                self.private = True
            else:
                self.channel = self.recipient
                self.private = False
            if self._root.check_identification:
                if self.text[0] == '+': self.identified=True
                self.text = self.text[1:]
            self.cmd, self.rest = self.get_cmd(self.text)
            self._root.set_cur_channel(self.channel)
       
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

    def sanitize(self,s):
        return self._root.sanitizer.sub("-",s)

    def from_string(self, buf):
#        print 'from_string: %s' % repr(buf)
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

    def get_cmd(self, line=None):
        if None == line:
            line = self.text
        if None != self._root.cmd_chars:
            if line[0] not in self._root.cmd_chars:
                return None, None
            if 1 == len(line):
                return None, None
            line = string.rstrip(line[1:])
            cmd, rest = self.get_next_word(line)
            assert type(cmd) == type('')
            return cmd, rest
        else:
            return None, None
        
    def get_next_word(self, s):
        # REFACTOR ME
        """ Next word """
        foo = string.split(s, None, 1)
        if len(foo) == 1:
            rest = ''
        else:
            rest = foo[1]
        foo = foo[0]
        return foo, rest

    def pl(self, word, n, s='s'):
        suffix = s
        if not n == 1:
            return word + suffix
        else:
            return word


class MessageHandler:
    def __init__(self,root,name="Handler"):
        self._name = name
        self._root = root
        self._handles=()
    
    def get_handles(self):
        return self._handles
        
    def handle(self,m):
        """ Override me """
#        self._root.logger.debug("Message handled by '%s'"%(self._name))
        return
    
    def get_name(self):
        return self._name

class PingHandler(MessageHandler):
    def __init__(self,root,name="PingHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("PING",)

    def handle(self,m):
        if "PING" == m.command:
            self._root.pong(m.params[0]) # I am guessing this means
                                         # the server that originated
                                         # the ping form other code

class CmdHandler(MessageHandler):
    def __init__(self,root,name="CmdHandler"):
        MessageHandler.__init__(self,name=name,root=root)
        self._handlers={}
        self._handles=("PRIVMSG",)
    
    def handle(self,m):
        MessageHandler.handle(self,m)
        if self._handlers.has_key(m.cmd):
            self._handlers[m.cmd].handle(m)
        else:
            if self._handlers.has_key("karma"):
                self._handlers['karma'].handle(m)
        
    def add_handler(self,hdlr):
        handles = hdlr.get_handles()
        for x in handles:
            self._handlers[x]=hdlr
        
class NickHandler(MessageHandler):
    # Requires heraldHandler to be initialized first
    # This class is a big'un
    def __init__(self,aliasDB,masternickDB,defDB,heraldHandler,root,name="NickHandler"):
        MessageHandler.__init__(self, name=name, root=root)
        self._cur_nicks={}
        self._aliasDB=aliasDB
        self._masternickDB=masternickDB
        self._defDB=defDB
        self._heraldHandler=heraldHandler
        self._handles = ("353", "NICK", "JOIN", "QUIT", "PART","forgetnick","aka","savenicks")
    
    def handle(self,m):
        """ Returns True if no other handlers should handle the message """
        MessageHandler.handle(self,m)
        if (m.command == '353'): # 353 is the response that is giving us a
                                 # a list of who is on the channel
            list = m.params[-1].split()
            for nick in list:
                self._cur_nicks[nick.lower()]=nick
                self._heraldHandler.set_last_herald(nick)
                self.add_nick(nick)
            return True
        elif (m.command == 'NICK'):
            nick=m.params[-1]
            self._cur_nicks[nick]=nick
            old_nick=m.sender_nick()
            if self._cur_nicks.has_key(old_nick.lower()):
                del self._cur_nicks[old_nick.lower()]
            self.add_alias(old_nick,nick)
            if not self._defDB.has_def(old_nick) \
                    and not self._cur_nicks.has_key(nick.lower()):
                self._heraldHandler.say_herald(nick)
            return True
        elif (m.command == 'JOIN'):
            self._root.set_cur_channel(m.params[0])
            nick=m.sender_nick()
            if self._cur_nicks.has_key(nick.lower()):
                return True
            self._cur_nicks[nick.lower()]=nick
            if not self._aliasDB.has_key(nick):
                self.add_nick(nick.lower())
                self._heraldHandler.say_herald_unknown(nick)
            else:
                self._heraldHandler.say_herald(nick)
            return True
        elif (m.command == 'QUIT') or (m.command == 'PART'):
            old_nick = m.sender_nick()
            self._heraldHandler.set_last_herald(old_nick)
            if self._cur_nicks.has_key(old_nick.lower()):
                del self._cur_nicks[old_nick.lower()]
            return True
        else:
            if "forgetnick" == m.cmd:
                if m.private and \
                        ((self._root.check_identification and \
                        not m.identified) or \
                        not self._root.check_identification):
                    self._root.say_no_private(m)
                else:
                    self.cmd_forgetnick(m)
                return True
            elif "aka" == m.cmd:
                self.cmd_aka(m)
                return True
            elif "savenicks" == m.cmd:
                self.cmd_savenicks(m)
                return True
            else:               
                return False
                
    def cmd_forgetnick(self,m):
        to_remove = m.rest.split()
        for old_nick in to_remove:
            lc_old_nick = old_nick.lower()
            lc_nick = m.sender_nick.lower()
            if not self._aliasDB.has_key(lc_old_nick):
                self._root.say("%s is not a nick I know" % (old_nick))
                continue
            if self._aliasDB.get(lc_nick) != self._aliasDB.get(lc_old_nick):
                self._root.say("%s is not an alias for %s" % (old_nick,m.sender_nick))
                continue
            nick_list = self._masternickDB.get(self._aliasDB.get(lc_nick))
            removed = 0
            for nick in nick_list:
                if nick.lower() == lc_old_nick:
                    nick_list.remove(nick)
                    removed += 1
            self._aliasDB.remove(lc_old_nick)
            self.add_nick(old_nick)
            if 0 < removed:
                self._root.say("Forgot %s %s for %s" % \
                    (removed,m.pl('alias',removed,'es'),m.sender_nick))
            else:
                self._root.say("%s not found for %s" % \
                    (m.pl('Alias', len(nick_list), 'es'), m.sender_nick))
                    
    def cmd_aka(self,m):
        nick = m.rest.strip()
        lc_nick = nick.lower()
        if not self._aliasDB.has_key(lc_nick):
            self._root.say('%s is not a nick I know' % (nick))
            return
        if not self._masternickDB.has_key(self._aliasDB.get(lc_nick)):
            self._aliasDB.set(lc_nick, lc_nick)
            self.add_nick(nick)
            self._root.say('%s had a broken AKA list - try again' % (nick))
            return
        nick_list = self._masternickDB.get(self._aliasDB.get(lc_nick))
        for x in nick_list:
            if lc_nick == x.lower():
                nick_list.remove(x)
        if 0 < len(nick_list):
            if len(nick_list)>10:
		nick_list=nick_list[:10]
		nick_list.append("too many more to list.")
            self._root.say ('%s is also known as %s' % (nick," and ".join(nick_list)))
        else:
    		self._root.say('%s has no other names I know about' % (nick))
            
    def cmd_savenicks(self,m):
        if m.sender_nick in self._root.owners:
            if self._root.check_identification and not m.identified:
                self._root.say_only_owners(m)
                return False
            else:
                self._aliasDB.flush()
                self._masternickDB.flush()
                self._root.say("Nicks saved")
                return True
        else:
            self._root.say_only_owners(m)
            return False
    
    def add_nick(self, nick):
        lc_nick = nick.lower()
        if not self._aliasDB.has_key(lc_nick):
            self._aliasDB.put(lc_nick, lc_nick)
        if not self._masternickDB.has_key(lc_nick):
            # We may be able to remove this, if nicklist is the only key
            self._masternickDB.put(lc_nick,[nick])
        #if self.debug:
        #    print "nick aka:", self.NickAka
        #    print "masternicks:", self.masternicks
    
    def add_alias(self,base_nick,target_nick):
        # Keep in mind that the conditions for adding aliases
        # tend to result in massive sets due to one person
        # changing their nick to another person's nick at some point
        # causing the sets of each to combine into one large set
        self.add_nick(base_nick)
        self.add_nick(target_nick)
        base_nick = base_nick.lower() # The nick to have an alias added to it
        target_nick = target_nick.lower() # The alias to be added to the nick
        base_alias = self._aliasDB.get(base_nick).lower()
                                              # The nick that base_nick is
                                              # currently aliased to
        target_alias = self._aliasDB.get(target_nick).lower()
                                              # The nick that target_nick is
                                              # currently aliased to
        
        # This code was really confusing, so I am trying to make it readable
        if base_nick == target_nick:
            return # They are the same, ignore
        if base_alias == target_alias:
            return # They both are aliased to the same name, ignore

        # They are aliased to different names, so we are going
        # to combine the nicklists of both by taking every nick
        # that belonged to target_alias and adding it to base_alias's list
        # then removing target_alias from the masternickDB, because it
        # is now just a link to base_alias
        try:
            target_alias_nicklist = self._masternickDB.get(target_alias)
            self._masternickDB.remove(target_alias)
            base_alias_nicklist = self._masternickDB.get(base_alias)
        except:
            target_alias_nicklist = [target_nick]
            base_alias_nicklist = [base_nick]
          
        batch_aliasDB_set = {}
        for target_alias_nick in target_alias_nicklist:
            target_alias_nick = target_alias_nick.lower()
            batch_aliasDB_set[target_alias_nick] = base_alias
            try:
                i = base_alias_nicklist.index(target_alias_nick)
            except:
                base_alias_nicklist.append(target_alias_nick)
        self._aliasDB.batch_set(batch_aliasDB_set)
        self._masternickDB.set(base_alias, base_alias_nicklist)

class FavorHandler(MessageHandler):
    def __init__(self,favorDB,aliasDB,root,name="FavorHandler",queen="The Queen"):
        MessageHandler.__init__(self,name=name,root=root)
        self._favorDB=favorDB
        self._aliasDB=aliasDB
        self.queen=queen
        self._handles = ("favor", "disfavor", "unfavor","favorites","pardon","savefavors")
    
    def handle(self,m):
        MessageHandler.handle(self,m)
        if self.queen.lower() != m.sender_nick.lower():
            self.say_queen_only(m)
            return True
        if self._root.check_identification and not m.identified:
            self._root.say_not_identified(m)
            return True
        if m.private and not self._root.check_identification:
            self._root.say_no_private(m)
            return True
        nick = m.rest
        if "favorites" == m.cmd:
            self.cmd_favorites(m)
            return True
        elif "savefavors" == m.cmd:
            if m.sender_nick in self._root.owners:
                if self._root.check_identification and not m.identified:
                    self._root.say_not_identified(m)
                    return False
                else:
                    self.cmd_savefavors(m)
                    return True
            else:
                self._root.say_only_owners(m)
        elif not self._aliasDB.has_key(nick):
            self.say_not_nick(m)
            return True
        elif "favor" == m.cmd:
            self.cmd_favor(m,nick)
            return True
        elif "disfavor" == m.cmd:
            self.cmd_disfavor(m,nick)
            return True
        elif "unfavor" == m.cmd:
            self.cmd_unfavor(m,nick)
            return True
        elif "pardon" == m.cmd:
            self.cmd_pardon(m,nick)
            return True
        else:
            return False
    
    def say_favor(self,nick):
        if self._favorDB.has_key(nick):
            favor=self._favorDB.get(nick)
            if "1" == favor:
                self._root.say("%s is on %s's favorites list"%(nick,self.queen))
            elif "-1" == favor:
                self._root.say("%s is on %s's least favorites list"%(nick,self.queen))
        else:
            pass

    def say_queen_only(self,m):
        self._root.say("Only the Queen has favorites")

    def say_not_nick(self,m):
        self._root.say("That is not a nick I have heard of")

    def cmd_favor(self,m,nick):
        self._favorDB.favor(nick)
        self._root.say("%s is now on %s's favorites list" % (nick, self.queen))
    
    def cmd_unfavor(self,m,nick):
        self._favorDB.unfavor(nick)
        self._root.say("%s is no longer looked upon with favor" % (nick))
    
    def cmd_pardon(self,m,nick):
        self._favorDB.pardon(nick)
        self._root.say("%s is no longer looked upon with disfavor" % (nick))
    
    def cmd_disfavor(self,m,nick):
        self._favorDB.disfavor(nick)
        self._root.say("%s is now on %s's least favorites list" % (nick, self.queen))

    def cmd_favorites(self,m):
        favs = self._favorDB.get_favorites()
        disfavs = self._favorDB.get_disfavorites()
        if not 0 == len(favs):
            self._root.say("On %s's favorites list: %s"\
                %(self.queen, ", ".join(favs)))
        if not 0 == len(disfavs):
            self._root.say("On %s's least favorites list: %s"\
                %(self.queen, ", ".join(disfavs)))
        return True

    def cmd_savefavors(self,m):
        if m.sender_nick in self._root.owners:
            if self._root.check_identification and not m.identified:
                self._root.say_only_owners(m)
                return False
            else:
                self._favorDB.flush()
                self._root.say("Favors saved")
                return True
        else:
            self._root.say_only_owners(m)
            return False
        

class HeraldHandler(MessageHandler):
    # Requires favorHandler to be initialized first
    def __init__(self,heraldDB,defDB,aliasDB,favorHandler,root,name="HeraldHandler",herald=True):
        MessageHandler.__init__(self,name=name,root=root)
        self._heraldDB=heraldDB
        self._defDB=defDB
        self._aliasDB=aliasDB
        self._favorHandler=favorHandler
        self._herald=herald
        self._herald_queue=0
        self._herald_timestamp=0
        self._last_herald={}
        self._handles=("heraldme","herald")
           
    def handle(self,m):
        MessageHandler.handle(self,m)
        if "heraldme" == m.cmd:
            if m.private and \
                    ((self._root.check_identification and \
                    not m.identified) or \
                    not self._root.check_identification):
                self._root.say_no_private(m)
            else:
                if self._heraldDB.get_herald_nick(m.sender_nick):
                    self._heraldDB.set_herald_nick(m.sender_nick, False)
                    self._root.say("Now heralding your full definition")
                else:
                    self._heraldDB.set_herald_nick(m.sender_nick, True)
                    self._root.say("Now heralding only your first definition")
        elif "herald" == m.cmd:
            if self._herald: 
                self.set_herald(False)
            else: 
                self.set_herald(True)
            return True
        
    def set_herald(self,herald=True):
        self._herald=herald
        if herald:
            self._root.say("Started heralding") 
        else:
            self._root.say("Stopped heralding")
    
    def say_herald(self,nick):
        """ Queue a herald, unless bucket is already full """
        if not self._herald:
            return
        if time.time() - self._herald_timestamp < 2:
            self._herald_queue += 1
        else:
            self._herald_queue = 0
        if self._herald_queue < 2:
            try:
                last_time = self.get_last_herald(nick)
                if time.time() - last_time < 600:
                    # replace with log: print "didn't herald %s" % m
                    return
            except:
                # replace with log: print "no lasttime for %s" % m
                pass

            if not self._defDB.has_def(nick) and self._defDB.has_def(self._aliasDB.get(nick)):
                master_nick = self._aliasDB.get(nick)
                if self._heraldDB.get_herald_nick(master_nick):
                    self._root.say("%s is aka %s; %s is %s"%(nick,master_nick,master_nick,self._defDB.get_def(master_nick,end=1,join=True)))
                else:
                    self._root.say("%s is aka %s; %s is %s"%(nick,master_nick,master_nick,self._defDB.get_def(master_nick,join=True)))
                self._favorHandler.say_favor(nick)              
            elif self._defDB.has_def(nick):
                if self._heraldDB.get_herald_nick(nick):
                    self._root.say("%s is %s"%(nick,self._defDB.get_def(nick,end=1,join=True)))
                else:
                    self._root.say("%s is %s"%(nick,self._defDB.get_def(nick,join=True)))
                self._favorHandler.say_favor(nick)
            self.set_last_herald(nick)
    
    def say_herald_unknown(self,nick):
        unknownphrases = ( \
                    "Welcome, %s; is this your first time here?", \
                    "Willkommen, bienvenue, welcome %s, im Cabaret, au Cabaret, to Cabaret", \
                    "Milords, Ladies and Gentlemen, please welcome %s")
        self._root.say(unknownphrases[int(random.random() *len(unknownphrases))] %(nick))
    
    def get_last_herald(self,nick):
        # This is changed from the previous way of handling last herald
        # in that it just holds the last herald list in memory, as there
        # is no good reason to store it. If the bot crashes we aren't
        # going to have a flood of people re-joining who just left minutes
        # before the bot crash, so it isn't worth writing it to the db
        # The only reason to hold that data would be for reference as to
        # a ".seen" sort of functionality, and that can be added somewher else
        master_nick = self._aliasDB.get(nick,nick.lower())
        try:
            return self._last_herald[master_nick]
        except:
            return None
        
    def set_last_herald(self,nick):
        cur_time = time.time()
        master_nick = self._aliasDB.get(nick,nick.lower())
        self._last_herald[master_nick]=cur_time
        self._herald_timestamp=cur_time


class DefHandler(MessageHandler):
    def __init__(self,defDB,root,name="DefHandler"):
        MessageHandler.__init__(self,name=name,root=root)
        self._defDB=defDB
        self._handles = ("def",
                         "whois",
                         "forget",
                         "forgetme",
                         "learn",
                         "learn_first",
                         "whatis",
                         "savedefs")
    def handle(self,m):
        MessageHandler.handle(self,m)
        if "def" == m.cmd:
            self.cmd_def(m)
            pass
        elif "whois" == m.cmd:
            self.cmd_def(m,concept=m.rest)
            return True
        elif "whatis" == m.cmd:
            self.cmd_def(m,concept=m.rest)
            return True
        elif "savedefs" == m.cmd:
            self.cmd_savedefs(m)
            return True
        else:
            if not m.private:
                if "forgetme" == m.cmd:
                    self.cmd_forgetme(m,m.sender_nick)
                else:    
                    words = m.rest.split()
                    if 3 > len(words):
                        self.say_bad_def()
                        return True
                    try:
                        pos =  words.index("is")
                        if 1 > pos or pos+1 == len(words):
                            self.say_bad_def()
                            return True
                    except:
                        self.say_bad_def()
                        return True
                    concept = ' '.join(words[:pos])
                    definition = ' '.join(words[pos+1:])
                    if "learn" == m.cmd:
                        self.cmd_learn(m,concept,definition)
                        return True
                    elif "forget" == m.cmd:
                        self.cmd_forget(m,concept,definition)
                        return True
                    elif "learn_first" == m.cmd:
                        self.cmd_learn_first(m,concept,definition)
                        return True
                    else:
                        return False
            else:
                self._root.say_no_private(m)
                return True
    
    def cmd_savedefs(self,m):
        if m.sender_nick in self._root.owners:
            if self._root.check_identification and not m.identified:
                self._root.say_only_owners(m)
                return False
            else:
                self._defDB.flush()
                self._root.say("Definitions saved")
                return True
        else:
            self._root.say_only_owners(m)
            return False
    
    def cmd_def(self,m,concept=None,definition=None):
        if "" == m.rest:
            self.say_def_dump()
            return True
        if None == concept and None == definition:
            words = m.rest.split()
            try:
                pos = words.index("is")
                if m.private:
                    self._root.say_no_private(m)
                    return True
                if 1 > pos or pos+1 == len(words):
                    self.say_bad_def()
                    return True
                concept = ' '.join(words[:pos])
                definition = ' '.join(words[pos+1:])
            except:
                pos = None
                concept = ' '.join(words)
        if None != concept:
            if None == definition:
                self.say_def(concept)
                return True
            else:
                self._defDB.add_def(concept,definition)
                self.say_def(concept)
        return False
    
    def say_bad_def(self):
        self._root.say("I need at least 3 words with an 'is' in the middle")
    
    def say_def_dump(self):
        self._root.say("Braindump available at: %s"%("nowhere, yet"))
    
    def cmd_learn(self,m,concept,definition):
        self.cmd_def(m,concept,definition)
        return True

    def cmd_forget(self,m,concept,definition):
        def_change = self._defDB.remove_def(concept,definition)
        if def_change['some_removed']:
            if self._defDB.has_def(concept):
                self._root.say("I now only know that %s is %s" \
                    % (concept, self._defDB.get_def_all(concept)))   
            else:
                self._root.say("I no longer know anything about %s"%(concept))
        if 0 < len(def_change['bad_list']):
            self._root.say("I did not know %s was %s" \
                %(concept," and ".join(def_change['bad_list'])))
        return True

    def cmd_forgetme(self,m,nick):
        self._defDB.remove(nick)
        self._root.say("I have expunged %s from my mind"%(nick))
        return True

    def cmd_learn_first(self,m,concept,definition):
        if not self._defDB.has_def(concept):
            self._defDB.add_def(concept,definition)
        else:
            def_list = self._defDB.get_def(concept,join=False)
            def_list = [definition] + def_list
            self._defDB.set_def(concept,def_list)
        self.say_def(concept)

    def say_def(self,concept):
        if not self._defDB.has_key(concept):
            self._root.say("Nobody has defined %s yet"%(concept))
        else:
            self._root.say("%s is %s"%(concept,self._defDB.get_def_all(concept)))

class KarmaHandler(MessageHandler):
    def __init__(self,karmaDB,root,name="KarmaHandler"):
        MessageHandler.__init__(self,name=name,root=root)
        self._karmaDB=karmaDB
        self._handles = ("karma","savekarmas")
        
    def handle(self,m):
        MessageHandler.handle(self,m)
        if "karma" == m.cmd:
            self.cmd_karma(m,m.rest)
            return True
        elif "savekarmas" == m.cmd:
            self.cmd_savekarmas(m)
            return True
        elif not m.private:
            for word in m.text.split():
                if 2 < len(word) and word[-2:] == "++":
                    self._karmaDB.add_karma(word[:-2])
                elif 2 < len(word) and word[-2:] == "--":
                    self._karmaDB.sub_karma(word[:-2])
            return True
        else:
            return True
                    
    def cmd_karma(self,m,word=None):
        if None == word: word = m.rest
        if 0 == len(word):
            self.say_karma_dump()
            return
        karma = self._karmaDB.get_karma(word)
        self._root.say("%s has %d %s"%(word,karma,m.pl("point",karma)))
        return True
    
    def cmd_savekarmas(self,m):
        if m.sender_nick in self._root.owners:
            if self._root.check_identification and not m.identified:
                self._root.say_only_owners(m)
                return False
            else:
                self._karmaDB.flush()
                self._root.say("Karmas saved")
                return True
        else:
            self._root.say_only_owners(m)
            return False
        
    def say_karma_dump(self):
        self._root.say("Karma Dump available at: %s"%("nowhere, yet"))

class SystemHandler(MessageHandler):
    def __init__(self,root,name="SystemHandler"):
        MessageHandler.__init__(self,name=name,root=root)
        self._handles = ("quit","log_level","help","join","part","silence","quiet","unquiet")
        
    def handle(self,m):
        MessageHandler.handle(self,m)
        if "help" == m.cmd:
            self.cmd_help(m,m.rest)
            return True
        elif m.sender_nick not in self._root.owners:
            self._root.say_only_owners(m)
            return True
        elif self._root.check_identification and not m.identified:
            self._root.say_not_identified(m)
            return False
        elif "quit" == m.cmd:
            self.cmd_quit(m,m.rest)
            return True
        elif "join" == m.cmd:
            self.cmd_join(m,m.rest)
            return True
        elif "part" == m.cmd:
            self.cmd_part(m,m.rest)
            return True
        elif "silence" == m.cmd:
            self.cmd_silence(m)
            return True
        elif "quiet" == m.cmd:
            self.cmd_silence(m,True)
            return True
        elif "unquiet" == m.cmd:
            self.cmd_silence(m,False)
            return True
        elif "log_level" == m.cmd:
            self.cmd_log_level(m)
            return True
        else:
            return False

    def cmd_quit(self,m,s):
        if 0 == len(s):
            s = "Planned Shutdown"
        self._root.logger.info("Quit called for by %s"%(m.sender_nick))
        self._root.quit(s)
        return True
        
    def cmd_help(self,m,nick):
        # I would like to make this targettable and only responding 
        # in private messages, a la: ?help termie
        # which would send the help message to termie, or the sender if
        # no target is specified
        """ Show commands """
        """ FIXME: this needs to understand potential other cmd chars. """
        if 0 < len(nick) and '#' != nick[0]:
            self._root.set_cur_channel(nick)
        else:
            self._root.set_cur_channel(m.sender_nick)
        self._root.say('JiBot - #JoiIto\'s bot - http://joi.ito.com/joiwiki/JiBot')
        self._root.say('Dictionary and user info: ?learn concept is definition || ?whois concept || ?whatis concept ||?forget concept is definition || ?forgetme')
        self._root.say('Technorati: ?info blog.com || ?last blog.com || ?cosmos blog.com || ?blogrep keywords')
        self._root.say('Amazon: ?amazon words || ?asin ASIN || ?isbn ISBN')
        self._root.say('Google: ?google words')
        self._root.say('Karma: nick++ || nick-- || ?karma nick || ?karma')
        self._root.say('Turn on or off heralding: ?herald')
	
    def cmd_log_level(self,m):
        pass

    def cmd_join(self,m,channel):
        if "" == channel:
            self._root.say("Which channel shall I join?")
            return
        self._root.logger.info("Told to join %s by %s"%(channel,m.sender_nick))
        self._root.join(channel)
        return True

    def cmd_part(self,m,channel):
        if "" == channel:
            self._root.say("Which channel shall I part?")
            return
        self._root.logger.info("Told to part %s by %s"%(channel,m.sender_nick))
        self._root.part(channel)
        return True

    def cmd_silence(self,m,silent=None):
        if None == silent:
            self._root.set_silent()
        else:
            self._root.set_silent(silent)
        return True

class TechnoratiHandler(MessageHandler):
    def __init__(self,root,name="TechnoratiHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("info","last","search","cosmos","blogrep","rss")

    def handle(self,m):
        MessageHandler.handle(self,m)
        query = m.rest
        if "" == query:
            return True
        if "info" == m.cmd:
            self.cmd_info(m,query)
            return True
        elif "last" == m.cmd:
            self.cmd_last(m,query)
            return True
        elif "search" == m.cmd or "blogrep" == m.cmd:
            self.cmd_search(m,query)
            return True
        elif "cosmos" == m.cmd:
            self.cmd_cosmos(m,query)
            return True
        elif "blogrep" == m.cmd:
            self.cmd_blogrep(m,query)
            return True
        elif "rss" == m.cmd:
            self.cmd_rss(m,query)
        else:
            return False
            
    def fetch_rss(self, url):
        try:
            rss = rssparser.parse(url)
            if (len(rss['items']) > 0):
                # Remove html links
                desc = re.compile('(<p>|<br>)').sub(' ', rss['items'][0]['description'].encode('ISO-8859-1'))
                desc = re.compile('<(.*?)>').sub('', desc)
            return desc
        except:
            self._root.logger.warn('Unable to fetch RSS for %s' % url)
        return None

    def cmd_info(self,m,query):
        try:
            info = technorati.bloginfo(query)
            lastupdate = "%02d-%02d-%02d %02d:%02d" % info.lastupdate[:5]
            self._root.say('%s - URL: %s - Last update: %s - Inbound links: %d - Inbound blogs: %d' % (info.name.encode('ISO-8859-1'), info.url.encode('ISO-8859-1'), lastupdate, info.inboundlinks, info.inboundblogs))
        except:
            self._root.say('Sorry %s is not in this universe' % (query))
    
    def cmd_last(self,m,query):
        """ Last post from a given blog (using Technorati for the RSS) """
        try:
            info = technorati.bloginfo(query)
            if info.rssurl:
                desc = self.fetch_rss(info.rssurl)
                if  0 < len(desc):
                    lastupdate = "%02d-%02d-%02d %02d:%02d" % info.lastupdate[:5]
                    self._root.say('%s\'s latest post at %s: %s' % (info.name.encode('ISO-8859-1'), lastupdate, desc[:200]))
                else:
                    self._root.say('No posts in %s\'s RSS feed' % (info.name.encode('ISO-8859-1')))
            else:
                self._root.say('I cannot find an RSS feed for %s' %(query))
        except:
            self._root.say('I cannot get info about %s\'s from Technorati. I honestly think you ought to sit down calmly, take a stress pill and think things over.' % (query))

    def cmd_search(self,m,query):
        """ Search in technorati """
        try:
            search = technorati.search(query)
            if 0 == len(search.item):
                # Any result
                self._root.say('Technorati does not know anything about %s. Are you sure you are making the right decision?' % (query))
                return
            elif 3 < len(search.item):
                # More than three results, let's cut them
                results = search.item[:3]
            else:
                results = search.item
            self._root.say('Search for %s. Showing first %d of %d sites' % (query,  len(results), len(search.item)))
            i = 0
            while i < len(results):
                # Remove html tags
                name = re.compile('(<p>|<br>)').sub(' ',results[i].name)
                name = re.compile('<(.*?)>').sub('', name)
                message = '%s - %s' % (name, results[i].url)
                self._root.say(message.encode('ISO-8859-1'))
                i += 1
        except:
            self._root.say('Technorati took exception to \'%s\' ' % (query))
			

    def cmd_cosmos(self,m,query):
        """ Technorati cosmos """
        try:
            search = technorati.cosmos(query)
            if 0 == len(search.item):
                # Any result
                self._root.say('Technorati does not know anything about %s. Are you sure you are making the right decision?' % (query))
                return
            elif 3 < len(search.item):
                # More than three results, let's cut them
                results = search.item[:3]
            else:
                results = search.item
            self._root.say('Search for %s. Showing first %d of %d sites' % (query,len(results),len(search.item)))
            i = 0
            while i < len(results):
                # Remove html tags
                name = re.compile('(<p>|<br>)').sub(' ',results[i].name)
                name = re.compile('<(.*?)>').sub('', name)
                message = '%s - %s' % (name, results[i].url)
                self._root.say(message.encode('ISO-8859-1'))
                i += 1
        except:
            self._root.say('Technorati took exception to \'%s\' ' % (query))

    def cmd_rss(self,m,url):
        try:
            desc = self.fetch_rss(url)
            if 0 < len(desc):
                self._root.say('%s: %s [...]' % (m.sender_nick, desc[:250]))
            else:
                self._root.say('%s: That RSS feed has no posts.'%(m.sender_nick))
        except:
            self._root.say('Unable to fetch RSS for %s'%(url))
        return

class AmazonHandler(MessageHandler):
    def __init__(self,root,name="AmazonHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("amazon","asin","isbn")

    def handle(self,m):
        MessageHandler.handle(self,m)
        query = m.rest
        if "" == query:
            return True
        if "amazon" == m.cmd:
            self.cmd_amazon(m,query)
            return True
        elif "asin" == m.cmd or "isbn" == m.cmd:
            self.cmd_asin(m,query)
            return True
        else:
            return False
    
    def cmd_amazon(self,m,query):
        """ Search keywords in Amazon """
        try:
            search = amazon.searchByKeyword(query)
            if 0 == len(search):
                self._root.say('Amazon does not know anything about %s. Are you quite sure?' % (query))
            elif 3 < len(search):
                # More than three results, let's cut them
                results = search[:3]
            else:
                results = search
            self._root.say('Search for %s. Showing first %d of %d products' % (query,len(results),len(search)))
            for result in results:
                try:
                    # Remove html tags
                    title = re.compile('(<p>|<br>)').sub(' ',result.ProductName.encode('ISO-8859-1'))
                    title = re.compile('<(.*?)>').sub('', title)
                    message = '%s %s' % (title, result.OurPrice.encode('ISO-8859-1'))
                    self._root.say(message)
                except AttributeError:
                    self._root.logger.warn("Amazon Query for '%s' returned a bad result"%(query))
        except:
                self._root.say('I cannot search %s. There are some extremely odd things about this mission.' % (query))

    def cmd_asin(self,m,query):
        """ Search ASIN in Amazon """
    	try:
            search = amazon.searchByASIN(query)
            if 0 == len(search):
                self._root.say('Amazon does not know anything about %s. It is nothing serious.' % (query))
            elif 3 < len(search):
                # More than three results, let's cut them
                results = search[:3]
            else:
                results = search
            self._root.say('Search for %s. Showing first %d of %d products' % (query, len(results), len(search)))
            for result in results:
                # Remove html tags
                title = re.compile('(<p>|<br>)').sub(' ',result.ProductName.encode('ISO-8859-1'))
                title = re.compile('<(.*?)>').sub('', title)
                message = '%s %s' % (title, result.OurPrice.encode('ISO-8859-1'))
                self._root.say(message)
        except:
            self._root.say('I cannot search %s. Sorry about this. I know it\'s a bit silly.' % (query))

class GoogleHandler(MessageHandler):
    def __init__(self,root,name="GoogleHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("google",)

    def handle(self,m):
        MessageHandler.handle(self,m)
        query = m.rest
        if "" == query:
            return True
        if "google" == m.cmd:
            self.cmd_google(m,query)
            return True
        else:
            return False

    def cmd_google(self,m,query):
        """ Query google """
        try:
            search = google.doGoogleSearch(query)
            if 0 == len(search.results):
                # Any result
                self._root.say('Google does not know anything about %s. I\'m sorry Dave, I don\'t have enough information.' % (query))
                return
            elif 3 < len(search.results):
                # More than three results, let's cut them
                results = search.results[:3]
            else:
                results = search.results
            self._root.say('Search for %s: %2.3f seconds. Showing first %d of %d sites' % (query, search.meta.searchTime, len(results), search.meta.estimatedTotalResultsCount))
            for result in results:
                # Remove html tags
                title = re.compile('(<p>|<br>)').sub(' ',result.title.encode('ISO-8859-1'))
                title = re.compile('<(.*?)>').sub('', title)
                message = '%s - %s' % (title, result.URL)
                self._root.say(message)
        except:
            self._root.say('I cannot search %s. Dr. Chandra, I\'m ready to stop the countdown if you want.' % (query))

class JargonHandler(MessageHandler): 
    def __init__(self,root,name="JargonHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("jargon",)

    def handle(self,m):
        MessageHandler.handle(self,m)
        query = m.rest
        if "" == query:
            return True
        if "jargon" == m.cmd:
            self.cmd_jargon(m,query)
            return True
        else:
            return False

    def cmd_jargon(self,m,query):
        """ Query jargon dictionary """
        self._root.say(jargon.find(query))            


class BlogHandler(MessageHandler): 
    def __init__(self,root,name="BlogHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("blog",)

    def handle(self,m):
        MessageHandler.handle(self,m)
        if m.private:
            self._root.say_no_private(m)
            return True
        if "" == m.rest:
            self.say_blog_location(m)
            return True
        if "blog" == m.cmd:
            self.cmd_blog(m,m.rest)
            return True
        else:
            return False

    def say_blog_location(self,m):
        self._root.say('My blog is located at: http://hashjoiito.bloxus.com')
        return True

    def cmd_blog(self,m,text):
        """ Add a blog entry """
        message = "%s\n%s"%(m.sender_nick,text)
        message = cgi.escape(message)
        blog = xmlrpclib.Server('http://www.bloxus.com/RPC.php',verbose=1)
        try:
            if (blog.blogger.newPost('APPKEY', '21', 'jibot', 'jibotblog', message, 1)):
                self._root.say('Posted.')
        except:
            self._root.say('I cannot blog.')


class FunHandler(MessageHandler): 
    def __init__(self,root,name="FunHandler"):
        MessageHandler.__init__(self,root=root,name=name)
        self._handles=("cool","shirt","knit","fight","lay","assert")

    def handle(self,m):
        MessageHandler.handle(self,m)
        if m.private:
            self._root.say_no_private(m)
            return True
        if "lay" == m.cmd:
            self.cmd_lay(m)
        elif "" == m.rest:
            return True
        elif "cool" == m.cmd:
            self.cmd_cool(m,m.rest)
            return True
        elif "shirt" == m.cmd:
            self.cmd_shirt(m,m.rest)
            return True
        elif "knit" == m.cmd:
            self.cmd_knit(m,m.rest)
            return True
        elif "fight" == m.cmd:
            self.cmd_fight(m,m.rest)
            return True
        else:
            return False        

    def cmd_cool(self,m,nick):
        coolphrases = ('Cool? we keep drinks in %s', '%s\'s undergarments are full of dry ice', 'ice forms on %s\'s upper slopes')
        cool = coolphrases[int(random.random() *len(coolphrases))] % (nick)
        self._root.say(cool)

    def cmd_shirt(self,m,nick):
        shirtphrases = ('%s would look supercilious in a blogging shirt http://cafeshops.com/jeanniecool', '%s is hot enough to carry off the \'too hot for friendster\' shirts http://cafeshops.com/frndster', 'I don\'t mean to get shirty, %s, but try http://cafeshops.com/mirandablog','Give up knitting, %s, try these on http://cafestores.com/beendoneblogged', 'Weblogs will fact-check %s\'s ... http://www.cafeshops.com/mirandablog.6314725')
        self._root.say(shirtphrases[int(random.random() *len(shirtphrases))] % (nick))

    def cmd_knit(self,m,item):
        self._root.action('picks up the knitting and begins to knit a %s for %s' % (item,m.sender_nick))

    def cmd_fight(self,m,nick):
        self._root.say('%s and %s go at it like hammer and tongs' % (nick,m.sender_nick))
        self._root.action('pulls %s off %s' % (nick,m.sender_nick))

    def cmd_lay(self,m):
        if "" == m.rest:
	        self._root.say('You have to tell me whom to lay')
        else:
            self._root.action('and %s discreetly retreat to a secluded area in the #channel. Muffled noises suggest the things happening...' % (m.rest))
		           
