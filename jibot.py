#!/usr/bin/python2.2

#	jibot - #joiito's IRC bot 
#		(C) 2003 Víctor R. Ruiz <rvr@infoastro.com>
#
#	Contributors
#		Kevin Marks < http://epeus.blogspot.com/ >
#		Jens-Christian Fischer
#		Joi Ito  http://joi.ito.com/
#
#	This script is based in simpleclient.py
#		(C) 1999  Erno Kuusela <erno@iki.fi> 

__author__ = "Victor R. Ruiz <rvr@infoastro.com>"
__contributors__ = ['Kevin Marks', 'Jens-Christian Fischer', 'Joi Ito']
__copyright__ = "Copyright (c) 2003 Victor R. Ruiz"
__license__ = "GPL"
__version__ = "0.4"
__cvsversion__ = "$Revision: 1.66 $"[11:-2]
__date__ = "$Date: 2003/12/05 00:25:13 $"[7:-2]

import string, sys, os, re
import random, time, xmlrpclib
import cPickle as pickle
#from Crypto.Hash import MD5

import technorati, google, amazon
import irclib, rssparser

class jibot(irclib.irc):
	""" #joiito's bot class """

	def __init__(self):
		""" Constructor """
		irclib.irc.__init__(self)
		getenv = os.environ.get

		# Begin configurable bits.

		# Command prefix (for instance, '?' for '?def')
		self.cmdchars = getenv('CMDCHARS') or '?'

		# Announce people joining the channels.
		self.herald = 1
		# The owners of the bot.
		self.owners = getenv('JIBOTOWNERS') or ['imajes','JoiIto','rvr','KevinMarks']

		# IRC nickname
		self.nick = getenv('IRCNICK') or 'jibot'
		# IRC server
		server = getenv('IRCSERVER') or 'irc.freenode.net'
		# IRC full name (shown in /whois)
		ircname = getenv('IRCNAME') or 'http://sf.net/projects/jibot/?%s' % __version__
		# IRC username (____@host.com)
		username  = getenv('USER') or 'jibot'
		# IRC channels (space separated)
		inchannels = getenv('IRCCHANNEL') or '#joiito #mobilewhack'
		self.channels = inchannels.split()

		# The queen of the channel.
		self.queen = 'jeanniecool'

		# Debug mode
		# self.debug = 1

		# End configurable options.

		self.wannaquit = 0
		self.hasquit = 0
		self.heraldq = 0
		self.curchannel = None
		self.herald_stamp = time.time()
		# Connects to the IRC server and joins the channel
		self.connect(server)
		self.send(irclib.msg(
			command='USER',
			params = [ username, 'localhost', 'localhost', ircname ]))
		self.send(irclib.msg(command='NICK', params = [ self.nick ]))
		print "setting nick to %s" % (self.nick)
		for channel in self.channels:
			self.send(irclib.msg(command='JOIN', params=[ channel ]))
			print "joining channel %s" % (channel)
			self.curchannel = channel
		print 'done joining'
		
		
		# Load definitions from file
		self.def_file = 'jibot.def'
		try:
			f = open(self.def_file, 'r')
			self.definitions = pickle.load(f)
			f.close()
			for k, v in self.definitions.items():
				if (type(v) == type('string')):
					self.definitions[k] = v.split(" and ")
		except:
			self.definitions = dict()
		
		# Load karma from file
		self.karma_file = 'jibot.kar'
		try:
			f = open(self.karma_file, 'r')
			self.karma = pickle.load(f)
			f.close()
		except:
			self.karma = dict()
		
		# Load nick aliases from file
		self.NickAka_file = 'jibot.NickAka'
		try:
			f = open(self.NickAka_file, 'r')
			self.NickAka = pickle.load(f)
			f.close()
		except:
			self.NickAka = dict()
		# Load nick aliases from file
		self.masternick_file = 'jibot.masternicks'
		try:
			f = open(self.masternick_file, 'r')
			self.masternicks = pickle.load(f)
			f.close()
		except:
			self.masternicks = dict()		
		#NickAka keeps track of name changes by mapping from nick to master nick - a simple dictionary
		#masternicks has the info mapping from nick ID to list of related ones and master nick
		#dictionary containing a dictionary with entries masternick and nickList
		#nicks is the current users
		# NOTE nicks shooudl be per channel now; which it isn't.
		self.nicks = dict()

		self.favorites_file = 'jibot.favorites'
		try:
			f = open(self.favorites_file, 'r')
			self.favorites = pickle.load(f)
			f.close()
		except:
			self.favorites = []
		self.disfavorites_file = 'jibot.disfavorites'
		try:
			f = open(self.disfavorites_file, 'r')
			self.disfavorites = pickle.load(f)
			f.close()
		except:
			self.disfavorites = []
		
	def do_join(self, m):
		""" /join #m """
		self.send(irclib.msg(command = 'JOIN', params = [ self.curchannel ]))

	def do_ping(self, m):
		""" /ping """
		reply = irclib.msg(command = 'PONG', params = [m.params[0]])
		self.send(reply)

	def do_privmsg(self, m):
		""" Handles private message """
		recipient, text = m.params
		sender = m.prefix
		self.sendernick = string.split(sender, '!')[0]
		if (recipient == self.nick):
			#self.curchannel = self.sendernick #use msg
			self.msg = 1
		else:
			self.msg = 0
			self.curchannel = recipient
		if recipient[0] not in irclib.NICKCHARS:
			if (text.startswith(self.cmdchars)):
				self.channel_cmd(text)
				print '<%s:%s> %s\n' % (self.sendernick, recipient, text)
			elif (text[-2:] == '++' or text[-2:] == '--'):
				# Karma
				who = string.lower(text[:-2])
				if (len(who) > 16):
					#self.say('That\'s a lengthy nick, Dave. Ignoring.')
					pass
				elif (len(who) > 0):
					if (self.karma.has_key(who)):
						pass
					else:
						self.karma[who] = 0
					if (text[-2:] == '++'):
						self.karma[who] += 1
					if (text[-2:] == '--'):
						self.karma[who] -= 1
					if (self.karma[who] == 0):
						del self.karma[who]
					# Save definition in file
					try:
						f = open(self.karma_file, 'w')
						pickle.dump(self.karma, f)
						f.close()
						#self.say('%s has %d points now' % (who, self.karma[who]))
						# self.say('Quite honestly, I wouldn\'t worry myself about that.')
					except:
						print 'Unable to save karma for %s' % who
		else:
			print '[%s]' % self.sendernick, 'to (%s)' % recipient,
			print text
	def addnick(self, nick):
		lcNick = string.lower(nick)
		if (not self.NickAka.has_key(lcNick)):
			self.NickAka[lcNick] = lcNick
		if not self.masternicks.has_key(lcNick):
			self.masternicks[lcNick] = dict()
			(self.masternicks[lcNick])['nicklist'] = [nick]
		#print "nick aka:", self.NickAka
		#print "masternicks:", self.masternicks
		
	def addnickalias(self, nick, aliasnick):
		self.addnick(nick)
		self.addnick(aliasnick)
		lcNick = string.lower(nick)
		lcNickAka = string.lower(aliasnick)
		nickMaster = self.NickAka[lcNick]
		if (lcNick == lcNickAka):
			return
		if (self.NickAka.has_key(lcNickAka)):
			if (self.NickAka[lcNickAka] == self.NickAka[lcNick]):
				return #already linked
			else:
				try:
					oldnicklist = ((self.masternicks[self.NickAka[lcNickAka]])['nicklist'])[:]
					del self.masternicks[self.NickAka[lcNickAka]]
				except:
					oldnicklist = [aliasnick]

		else:
			oldnicklist = [aliasnick]
		for oldnick in oldnicklist:
			lcOldnick = string.lower(oldnick)
			self.NickAka[lcOldnick] = nickMaster
			try:
				i = (self.masternicks[nickMaster])['nicklist'].index(oldnick)
			except:
				if not self.masternicks.has_key(nickMaster):
					self.addnick(nickMaster)
				(self.masternicks[nickMaster])['nicklist'].append(oldnick)
		self.saveNicks()

	def saveNicks(self):
		try:
			f = open(self.NickAka_file, 'w')
			pickle.dump(self.NickAka, f)
			f.close()
			f = open(self.masternick_file, 'w')
			pickle.dump(self.masternicks, f)
			f.close()
		except:
			pass

	def saveFavors(self):
		try:
			f = open(self.favorites_file, 'w')
			pickle.dump(self.favorites, f)
			f.close()
			f = open(self.disfavorites_file, 'w')
			pickle.dump(self.disfavorites, f)
			f.close()
		except:
			pass

	def do_any(self, m):
		print "do_any",m
		if (m.command == '353'):
			list = m.params[-1].split()
			
			for nick in list:
				self.nicks[nick] = nick
				self.addnick(nick)
			print self.nicks
		elif (m.command == 'NICK'):
			nick = m.params[-1]
			self.nicks[nick] = nick
			oldnick = string.split(m.prefix, '!')[0]
			if (self.nicks.has_key(oldnick)):
				del self.nicks[oldnick]
			self.addnickalias(oldnick,nick)
			if (self.herald):
				if (self.definitions.has_key(string.lower(nick)) and (not self.definitions.has_key(string.lower(oldnick)))):
					self.cmd_def(nick)
		elif (m.command == 'JOIN'):
			self.curchannel =  m.params[0]
			nick = string.split(m.prefix, '!')[0]
			self.nicks[nick] = nick
			self.addnick(nick)
			if (self.herald):
				self.queue_herald(nick)
		elif (m.command == 'QUIT') or (m.command == 'PART'):
			oldnick = string.split(m.prefix, '!')[0]
			if (self.nicks.has_key(oldnick)):
				del self.nicks[oldnick]
		else:
			print "%s - %s " % (m.command, "/".join(m.params))
		
	def do_default(self, m):
		""" Default """
		if m.prefix:
			print '[%s]' % m.prefix,
		print '|', m.command, '|',
		print string.join(m.params, ' ! ')

	def loop(self):
		""" Main loop """
		import select
		while not self.wannaquit:
			r, w, e = select.select([self], [], [])
			if self in r:
				self.do_one_msg()
				
			if (self.hasquit == 1):
				break

			##if (int(time.time()) % 5 == 0):
			##	self.checklinks()
			#if sys.stdin in r:
			#	self.user_cmd(sys.stdin.readline())

	def checklinks():
		""" Check links 
		cosmos = technorati.cosmos('rvr.blogalia.com')
		try:
			hashlist = picke.load(open('hash'))
		except:
			haslist = []
		hash = ''
		changed = 0

		# Check each blog against list of hashes and jabber and email new ones
		for blog in cosmos.item:
			hash = str(MD5.new(blog.url + str(blog.linkcreated)).hexdigest())
			if hash not in hashlist:
				if changed == 0:
					changed = 1
					diff = mktime(gmtime()) - mktime(blog.linkcreated)
					self.say(blog,diff)
					print "looping"
					hashlist.append(hash)
				sleep(5) # try to prevent irc flooding
			# If there were any new ones, update the hashfile
			if changed == 1:
				hashfile = open(hashfilename, 'w')
				if len(hashlist) > 50:
				del hashlist[0:len(hashlist)-50]
				writestr = "\n".join(hashlist)
				hashfile.writelines(writestr)
				hashfile.close()
				irccon.disconnect()
			else:
				print "no new inbound links\n" """
		pass
		
	def say(self, line):
		""" Sends a message to a channel """
		if not self.curchannel:
			print '-- no current channel!'
			return
		line = string.rstrip(line)
		m = irclib.msg(command = 'PRIVMSG',
				params = [self.curchannel, line])
		self.send(m)
		time.sleep(1.0)

	def action(self, line):
		""" performs an action on the channel (eg, /me foo) """
		if not self.curchannel:
			print '-- no current channel!'
			return
		line = string.rstrip(line)
		line = '\001ACTION' + line + '\001'  
		m = irclib.msg(command = 'PRIVMSG',
			       params = [self.curchannel, line])
		self.send(m)
		time.sleep(1.5)

	def quit(self, line):
		""" quits the irc network """
		""" some irc networks have this problem with early quits, to prevent
		    bot attacks using the quit message, so we should probably check to see
		    if the bot quit early, and if so, just send a msg rather than the
		    quit line """
		line = string.rstrip(line)
		m = irclib.msg(command = 'QUIT',
			       params = [line])
		self.send(m)
		time.sleep(1.5)
		sys.exit()
		
	def get_next_word(self, s):
		""" Next word """
		foo = string.split(s, None, 1)
		if len(foo) == 1:
			rest = ''
		else:
			rest = foo[1]
		foo = foo[0]
		return foo, rest

	def user_cmd(self, line):
		""" Handler of user commands """
		if line[0] not in self.cmdchars:
			self.say(line)
			return
		line = string.rstrip(line[1:])
		cmd, rest = self.get_next_word(line)
		assert type(cmd) == type('')
		if not cmd:
			return
		attr = 'usercmd_' + cmd
		if hasattr(self, attr):
			cmdhandler = getattr(self, attr)
			cmdhandler(rest)
		else:
			print '-- command not found:', cmd

	def channel_cmd(self, line):
		""" Handler of channel commands """
		if (len(line) < 2):
			return
		if line[0] not in self.cmdchars:
			self.say(line)
			return
		line = string.rstrip(line[1:])
		cmd, rest = self.get_next_word(line)
		assert type(cmd) == type('')
		if not cmd:
			return
		attr = 'cmd_' + cmd
		if hasattr(self, attr):
			cmdhandler = getattr(self, attr)
			cmdhandler(rest)
		else:
			print '-- command not found:', cmd

	""" Private commands """
	def usercmd_echo(self, l):
		print '--', l

	def usercmd_msg(self, l):
		recipient, rest = self.get_next_word(l)
		self.send(irclib.msg(command = 'PRIVMSG',
				  params = [recipient, rest]))
		print '-->', recipient, ':', rest

	def queue_herald(self, m):
		""" Queue a herald, unless bucket is already full """
		if (time.time() - self.herald_stamp < 2):
			self.heraldq = self.heraldq + 1
		else:
			self.heraldq = 0
		if (self.heraldq < 2):
			self.cmd_def(m)
			self.herald_stamp = time.time()

	""" 'Channel' commands """
	def cmd_cool(self, m):
		coolphrases = ('Cool? we keep drinks in %s', '%s\'s undergarments are full of dry ice', 'ice forms on %s\'s upper slopes')
		cool = coolphrases[int(random.random() *len(coolphrases))] % (m)
		self.say(cool)

	def cmd_shirt(self, m):
		shirtphrases = ('%s would look supercilious in a blogging shirt http://cafeshops.com/jeanniecool', '%s is hot enough to carry off the \'too hot for friendster\' shirts http://cafeshops.com/frndster', 'I don\'t mean to get shirty, %s, but try http://cafeshops.com/mirandablog','Give up knitting, %s, try these on http://cafestores.com/beendoneblogged', 'Weblogs will fact-check %s\'s ... http://www.cafeshops.com/mirandablog.6314725')
		self.say(shirtphrases[int(random.random() *len(shirtphrases))] % (m))

	def cmd_knit(self, m):
		self.action('%s picks up the knitting' % (m))

	def cmd_aka(self, m):
		nick = string.lower(m)
		if (self.NickAka.has_key(nick)):
			if self.masternicks.has_key(self.NickAka[nick]):
				nicklist = ((self.masternicks[self.NickAka[nick]])['nicklist'])[:]
				for n in nicklist:
					if (nick == string.lower(n)):
						nicklist.remove(n)
				if (len(nicklist)>0):
					self.say ('%s is also known as %s' % (m," and ".join(nicklist)))
				else:
					self.say('%s has no other names I know about' % (m))
			else:
				#fix broken masternicks
				self.NickAka[nick] = nick
				self.addnick(m)
				self.say('%s had a broken AKA list - try again' % (m))
		else:
			self.say('%s is not a nick I know' % (m))

	def cmd_fight(self, m):
		self.say('%s and %s go at it like hammer and tongs' % (m,self.sendernick))
		self.say('%s pulls %s off %s' % (self.nick,m,self.sendernick))

	def cmd_lay(self, m):
		if (m == ""):
			self.say('You have to tell me whom to lay')
		else:
			self.say('JiBot and %s discreetly retreat to a secluded area in the #channel. Muffled noises suggest the things happening...' % (m))
		
	def cmd_help(self, m):
		""" Show commands """
		""" FIXME: this needs to understand potential other cmd chars. """
		
		self.say('JiBot - #JoiIto\'s bot - http://joi.ito.com/joiwiki/JiBot')
		self.say('Dictionary and user info: ?learn concept is definition || ?whois concept || ?whatis concept')
		self.say('Technorati: ?info blog.com || ?last blog.com || ?cosmos blog.com || ?search keywords')
		self.say('Amazon: ?amazon words || ?asin ASIN || ?isbn ISBN')
		self.say('Google: ?google words')
		self.say('Karma: nick++ || nick-- || ?karma nick || ?karma')
		self.say('Turn on or off heralding: ?herald')
	
	def cmd_herald(self, m):
		if (self.herald):
			self.herald = 0
			self.say('stopped heralding')
		else:
			self.herald = 1
			self.say('started heralding')
		

	def cmd_info(self, m):
		""" Display """
		if (m == ""):
			return
		try:
			info = technorati.bloginfo(m)
			lastupdate = "%02d-%02d-%02d %02d:%02d" % info.lastupdate[:5]
			self.say('%s - URL: %s - Last update: %s - Inbound links: %d - Inbound blogs: %d' % (info.name.encode('ISO-8859-1'), info.url.encode('ISO-8859-1'), lastupdate, info.inboundlinks, info.inboundblogs))
		except:
			self.say('Sorry %s is not in this universe' % (m))

	def cmd_last(self, m):
		""" Last post as in RSS feed """
		if (m == ""):
			return
		try:
			info = technorati.bloginfo(m)
			if (info.rssurl):
				rss = rssparser.parse(info.rssurl)
				if (len(rss['items']) > 0):
					# Remove html links
					desc = re.compile('(<p>|<br>)').sub(' ', rss['items'][0]['description'].encode('ISO-8859-1'))
					desc = re.compile('<(.*?)>').sub('', desc)
					lastupdate = "%02d-%02d-%02d %02d:%02d" % info.lastupdate[:5]
					self.say('%s\'s latest post at %s: %s' % (info.name.encode('ISO-8859-1'), lastupdate, desc[:200]))
				else:
					self.say('No posts in %s\'s RSS feed' % (info.name.encode('ISO-8859-1')))
			else:
				self.say('This blog doesn\'t have RSS feed')
		except:
			self.say('I cannot read %s\'s info. Look Dave, I can see you\'re really upset about this. I honestly think you ought to sit down calmly, take a stress pill and think things over.' % (m))

	def cmd_search(self, m):
		""" Search in technorati """
		if (m == ""):
			return
		try:
			search = technorati.search(m)
			if (len(search.item) == 0):
				# Any result
				self.say('Technorati does not know anything about %s. Are you sure you are making the right decision?' % (m))
				return
			elif (len(search.item) > 3):
				# More than three results, let's cut them
				results = search.item[:3]
			else:
				results = search.item
			self.say('Search for %s. Showing first %d of %d sites' % (m,  len(results), len(search.item)))
			i = 0
			while (i < len(results)) :
				# Remove html tags
				name = re.compile('(<p>|<br>)').sub(' ',results[i].name)
				name = re.compile('<(.*?)>').sub('', name)
				message = '%s - %s' % (name, results[i].url)
				self.say(message.encode('ISO-8859-1'))
				i += 1
		except:
			self.say('Technorati took exception to \'%s\' ' % (m))
			

	def cmd_cosmos(self, m):
		""" Technorati cosmos """
		if (m == ""):
			return
		try:
			search = technorati.cosmos(m)
			if (len(search.item) == 0):
				# Any result
				self.say('Technorati does not know anything about %s. Are you sure you are making the right decision?' % (m))
				return
			elif (len(search.item) > 3):
				# More than three results, let's cut them
				results = search.item[:3]
			else:
				results = search.item
			self.say('Search for %s. Showing first %d of %d sites' % (m,  len(results), len(search.item)))
			i = 0
			while (i < len(results)) :
				# Remove html tags
				name = re.compile('(<p>|<br>)').sub(' ',results[i].name)
				name = re.compile('<(.*?)>').sub('', name)
				message = '%s - %s' % (name, results[i].url)
				self.say(message.encode('ISO-8859-1'))
				i += 1
		except:
			self.say('Technorati took exception to \'%s\' ' % (m))
			

	def cmd_google(self, m):
		""" Query google """
		if (m == ""):
			return
		try:
			search = google.doGoogleSearch(m)
			if (len(search.results) == 0):
				# Any result
				self.say('Google does not know anything about %s. I\'m sorry Dave, I don\'t have enough information.' % (m))
				return
			elif (len(search.results) > 3):
				# More than three results, let's cut them
				results = search.results[:3]
			else:
				results = search.results
			self.say('Search for %s: %2.3f seconds. Showing first %d of %d sites' % (m, search.meta.searchTime, len(results), search.meta.estimatedTotalResultsCount))
			for result in results:
				# Remove html tags
				title = re.compile('(<p>|<br>)').sub(' ',result.title.encode('ISO-8859-1'))
				title = re.compile('<(.*?)>').sub('', title)
				message = '%s - %s' % (title, result.URL)
				self.say(message)
		except:
			self.say('I cannot search %s. Dr. Chandra, I\'m ready to stop the countdown if you want.' % (m))

	def cmd_blogrep(self, m):
		self.cmd_search(m)

	def cmd_whatis(self, m):
		self.cmd_def(m)

	def cmd_whois(self, m):
		self.cmd_def(m)

	def cmd_savedefs(self, m):
		f = open("defdump_%s.txt" % m, 'w')
		for k,v in self.definitions.items():
			for defn in v:
				f.write("%s is %s\n" % (k,defn))
		f.close()

	def cmd_amazon(self, m):
		""" Search keywords in Amazon """
		if (m == ""):
			return
		try:
			search = amazon.searchByKeyword(m)
			if (len(search) == 0):
				self.say('Amazon does not know anything about %s. Are you quite sure?' % (m))
			elif (len(search) > 3):
				# More than three results, let's cut them
				results = search[:3]
			else:
				results = search
			self.say('Search for %s. Showing first %d of %d products' % (m, len(results), len(search)))
			for result in results:
				# Remove html tags
				title = re.compile('(<p>|<br>)').sub(' ',result.ProductName.encode('ISO-8859-1'))
				title = re.compile('<(.*?)>').sub('', title)
				message = '%s %s' % (title, result.OurPrice.encode('ISO-8859-1'))
				self.say(message)
			
		except:
			self.say('I cannot search %s. There are some extremely odd things about this mission.' % (m))
			
	def cmd_asin(self, m):
		""" Search ASIN in Amazon """
		if (m == ""):
			return
		try:
			search = amazon.searchByASIN(m)
			if (len(search) == 0):
				self.say('Amazon does not know anything about %s. It is nothing serious.' % (m))
			elif (len(search) > 3):
				# More than three results, let's cut them
				results = search[:3]
			else:
				results = search
			self.say('Search for %s. Showing first %d of %d products' % (m, len(results), len(search)))
			for result in results:
				# Remove html tags
				title = re.compile('(<p>|<br>)').sub(' ',result.ProductName.encode('ISO-8859-1'))
				title = re.compile('<(.*?)>').sub('', title)
				message = '%s %s' % (title, result.OurPrice.encode('ISO-8859-1'))
				self.say(message)
			
		except:
			self.say('I cannot search %s. Sorry about this. I know it\'s a bit silly.' % (m))

	def cmd_isbn(self, m):
		self.cmd_asin(m)
	
	def cmd_learn(self, m):
		""" Learn a definition """
		if (m == ""):
			return
		words = m.split()
		if (len(words) < 3):
			self.say('I need at least 3 words with an \'is\' in the middle')
			return
		try:
			pos = words.index('is') 
		except:
			self.say('I need an \'is\' in the middle')
			return
		
		concept = string.lower(' '.join(words[:pos]))
		definition = ' '.join(words[pos+1:])
		if (not self.definitions.has_key(concept)):
			self.definitions[concept] = []
		try:
			i = self.definitions[concept].index(definition)
		except:
			self.definitions[concept].append(definition)

		try:
			f = open(self.def_file, 'w')
			pickle.dump(self.definitions, f)
			f.close()
			self.say('I understand now, Dr. Chandra; %s is %s' % (concept, " & ".join(self.definitions[concept])))
		except:
			pass

	def cmd_forgetnick(self, oldNicks):
		nickList = oldNicks.split()
		for oldNick in nickList:
			lcOldNick = string.lower(oldNick)
			lcNick = string.lower(self.sendernick)
			if (self.NickAka.has_key(lcOldNick)):
				if (self.NickAka[lcNick] == self.NickAka[lcOldNick]):
					nicklist = (self.masternicks[self.NickAka[lcNick]])['nicklist']
					for nick in nicklist:
						if (string.lower(nick) == lcOldNick):
							nicklist.remove(nick)
					del self.NickAka[lcOldNick] #remove mapping
					self.addnick(oldNick) #make clean mapping - ie fresh masternicks
					self.saveNicks()
				else:
					self.say("%s is not an alias for %s" % (oldNick,self.sendernick))
			else:
				self.say("%s is not an nick I know" % (oldNick))

	def cmd_forgetme(self,m):
		""" Forget my nick's definition """
		concept = string.lower(self.sendernick)
		if (not self.definitions.has_key(concept)):
			self.say('I don\'t know about \'%s\' ' % concept)
			return;
		del self.definitions[concept]
		self.say('I have expunged %s from my mind' % (concept))
		try:
			f = open(self.def_file, 'w')
			pickle.dump(self.definitions, f)
			f.close()
		except:
			pass

	def cmd_forget(self, m):
		""" Forget a definition """
		if (m == ""):
			return
		words = m.split()
		if (len(words) < 3):
			self.say('I need at least 3 words with an \'is\' in the middle')
			return
		try:
			pos = words.index('is') 
		except:
			self.say('I need an \'is\' in the middle')
			return
		
		concept = string.lower(' '.join(words[:pos]))
		definition = ' '.join(words[pos+1:])
		if (not self.definitions.has_key(concept)):
			self.say('I don\'t know about \'%s\' ' % concept)
			return;
		if(definition in self.definitions[concept]):
			self.definitions[concept].remove(definition)
		else:
			self.say('I didn\'t know %s was %s' % (concept, definition))
			return;
		if (len(self.definitions[concept]) == 0):
			del self.definitions[concept]
			self.say('I have expunged %s from my mind' % (concept))
		else:
			self.say('I now only know that %s is %s' % (concept, " & ".join(self.definitions[concept])))
		try:
			f = open(self.def_file, 'w')
			pickle.dump(self.definitions, f)
			f.close()
			#dumbphrases = ('I am now a dumber bot','Dave, my mind is going...')
			#self.say(dumbphrases[int(random.random() *len(dumbphrases))])
		except:
			pass
			
	def cmd_def(self, m):
		""" Display a stored definition """
		if (m == ""):
			self.say("Braindump is at http://jibot.joi.ito.com:8080/braindump.rpy")
			return
		words = m.split()
		try:
			pos = words.index('is') 
			self.cmd_learn(m) #ie do this if there is an 'is' involved
		except:
			concept = string.lower(m)
			if (self.definitions.has_key(concept)):
				self.say('%s is %s' % (m, " and ".join(self.definitions[concept])))
			else:
				try:
					nickList = ((self.masternicks[self.NickAka[concept]])['nicklist'])[:]
					for akaNick in nickList:
						concept = string.lower(akaNick)
						if (self.definitions.has_key(concept)):
							self.say('%s is aka %s, and %s is %s' % (m, akaNick,akaNick," and ".join(self.definitions[concept])))
				except:
					unknownphrases = ("It's puzzling, I don't think I've ever seen anything like %s before","No-one has dished the dirt on %s yet",
					"Perhaps if %s makes friends with jeannie I'll say something nice next time", "Are you new here, %s?","Is %s a pseudonym?")
					self.say(unknownphrases[int(random.random() *len(unknownphrases))] %(m))
				if m in self.favorites:
					self.say("%s is on %s's favorites list" % (m,self.queen))
				if m in self.disfavorites:
					self.say("%s is on %s's least favorites list" % (m,self.queen))

	def cmd_assert(self, m):
		""" Joi's first command """
		if (m == ""):
			pass
		else:
			if (m == "Joi is a fool"):
				self.say("Jibot does not agree.")
			elif (m == "Technobot is the ruler of all #joiito bots."):
				self.say("Technobot needs ego.")
				self.say("fussbot++")
			else:
				self.say("Jibot agrees with %s that %s" % (self.sendernick, m))
			
	def cmd_karma(self, m):
		if (m == ""):
			self.say("Chart is at http://jibot.joi.ito.com:8080/karmadump.rpy")
		else:
			words = m.split()
			nick = words[0]
			try:
				self.say('%s has %s points' % (nick, self.karma[nick.lower()]))
			except:
				self.say('%s has no karma points' % nick)
	def cmd_blog(self, m):
		if (m == ""):
			return
		message = '%s\n%s' % (self.sendernick, m)
		blog = xmlrpclib.Server('http://www.bloxus.com/RPC.php', verbose = 1)
		try:
			if (blog.blogger.newPost('APPKEY', '21', 'jibot', 'jibotblog', message, 1)):
				self.say('Posted.')
		except:
			self.say('I cannot blog.')

	def cmd_quit(self, m):
		if (m == ""):
			return
		if (self.sendernick in self.owners): 
			self.quit('%s told me to quit -- %s' % (self.sendernick, m))
			self.hasquit = 1
		else:
			self.say("%s: you can't make me quit!" % (self.sendernick))
	
	def cmd_favor(self, nick):
		if (not self.sendernick == self.queen):
			self.say("Only the Queen has favorites")
			return	
		if not nick in self.favorites:
			self.favorites = [nick] + self.favorites[:4]
			self.say("%s is now on %s's favorites list" % (nick,self.queen))
		if nick in self.disfavorites:
			self.disfavorites.remove(nick)
		self.saveFavors()

	def cmd_unfavor(self, nick):
		if (not self.sendernick == self.queen):
			self.say("Only the Queen has favorites")
			return	
		if nick in self.favorites:
			self.favorites.remove(nick)
			self.say("%s is no longer looked upon with favor" % (nick))
		self.saveFavors()

	def cmd_pardon(self, nick):
		if (not self.sendernick == self.queen):
			self.say("Only the Queen has favorites")
			return	
		if nick in self.disfavorites:
			self.disfavorites.remove(nick)
			self.say("%s is no longer looked upon with disfavor" % (nick))
		self.saveFavors()

	def cmd_disfavor(self, nick):
		if (not self.sendernick == self.queen):
			self.say("Only the Queen has favorites")
			return	
		if not nick in self.disfavorites:
			self.disfavorites = [nick] + self.disfavorites[:4]
			self.say("%s is now on %s's least favorites list" % (nick,self.queen))
		if nick in self.favorites:
			self.favorites.remove(nick)
		self.saveFavors()

			
	def cmd_favorites(self,m):
		if (not self.sendernick == self.queen):
			self.say("Only the Queen has favorites")
		else:
			if len (self.favorites) >0:
				self.say("On %s's favorites list: %s" % (self.sendernick, ",".join(self.favorites)))
			if len (self.disfavorites) >0:
				self.say("On %s's least favorites list: %s" % (self.sendernick, ",".join(self.disfavorites)))

if __name__ == '__main__':
	bot = jibot()
	while (1):
		try:
			bot.loop()
			bot = jibot()
			
		except irclib.IrcNetworkError, msg:
			print 'lost connection,', msg

		except (bot.hasquit == 1):
			print 'quit command used.'
			sys.exit()
