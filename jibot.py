#!/usr/bin/python2.2

#	jibot - #joiito's IRC bot 
#		(C) 2003 V�ctor R. Ruiz <rvr@infoastro.com>
#
#	Contributors
#		Kevin Marks < http://epeus.blogspot.com/ >
#		Jens-Christian Fischer
#
#	This script is based in simpleclient.py
#		(C) 1999  Erno Kuusela <erno@iki.fi> 

__author__ = "Victor R. Ruiz <rvr@infoastro.com>"
__contributors__ = ['Kevin Marks', 'Jens-Christian Fischer']
__copyright__ = "Copyright (c) 2003 Victor R. Ruiz"
__license__ = "GPL"
__version__ = "0.4"
__cvsversion__ = "$Revision: 1.8 $"[11:-2]
__date__ = "$Date: 2003/06/11 19:14:08 $"[7:-2]

import string, sys, os, re
import random, time
import cPickle as pickle
#from Crypto.Hash import MD5

import technorati, google, amazon
import irclib, rssparser

class jibot(irclib.irc):
	""" #joiito's bot class """

	def __init__(self):
		""" Constructor """
		self.cmdchars = '?'
		self.curchannel = None
		self.wannaquit = 0
		irclib.irc.__init__(self)
		
		# Variable declarations
		getenv = os.environ.get
		ircname = getenv('IRCNAME') or 'Python #joiito\'s bot'
		self.nick = getenv('IRCNICK') or 'jibot'
		username  = getenv('USER') or 'jibot'
		server = getenv('IRSERVER') or 'irc.freenode.net'
		channel = getenv('IRCCHANNEL') or '#joiito'
		
		# Connects to the IRC server and joins the channel
		self.connect(server)
		self.send(irclib.msg(
			command='USER',
			params = [ username, 'localhost', 'localhost', ircname ]))
		self.send(irclib.msg(command='NICK', params = [ self.nick ]))
		self.send(irclib.msg(command='JOIN', params=[ channel ]))
		self.curchannel = channel
		
		# Load definitions from file
		self.def_file = 'jibot.def'
		try:
			f = open(self.def_file, 'r')
			self.definitions = pickle.load(f)
			f.close()
		except:
			self.definitions = dict()
		
	def do_join(self, m):
		""" /join #m """
		self.send(irclib.msg(command='JOIN', params=[ self.curchannel ]))

	def do_ping(self, m):
		""" /ping """
		reply = irclib.msg(command = 'PONG', params=[m.params[0]])
		self.send(reply)

	def do_privmsg(self, m):
		""" Sends private message """
		recipient, text = m.params
		sender = m.prefix
		self.sendernick = string.split(sender, '!')[0]
		if recipient[0] not in irclib.NICKCHARS:
			if (text[0] == '?'):
				self.channel_cmd(text)
				print '<%s:%s> %s\n' % (self.sendernick, recipient, text)
		else:
			print '[%s]' % self.sendernick,
			print text

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
		m = irclib.msg(command='PRIVMSG',
				params = [self.curchannel, line])
		self.send(m)

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
		self.send(irclib.msg(command='PRIVMSG',
				  params = [recipient, rest]))
		print '-->', recipient, ':', rest

	""" 'Channel' commands """
	def cmd_cool(self, m):
		coolphrases = ('Cool? we keep drinks in %s', '%s\'s undergarments are full of dry ice', 'ice forms on %s\'s upper slopes')
		cool = coolphrases[int(random.random() *len(coolphrases))] % (m)
		self.say(cool)

	def cmd_shirt(self, m):
		shirtphrases = ('%s would look supercilious in a blogging shirt http://cafeshops.com/jeanniecool', '%s is hot enough to carry off the \'too hot for friendster\' shirts http://cafeshops.com/frndster', 'I don\'t mean to get shirty, %s, but try http://cafeshops.com/mirandablog','Give up knitting, %s, try these on http://cafestores.com/beendoneblogged', 'Weblogs will fact-check %s\'s ... http://www.cafeshops.com/mirandablog.6314725')
		self.say(shirtphrases[int(random.random() *len(shirtphrases))] % (m))

	def cmd_knit(self, m):
		self.say('%s picks up the knitting' % (m))

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
		self.say('JiBot - #JoiIto\'s bot - http://joi.ito.com/joiwiki/JiBot')
		self.say('Dictionary: ?learn concept is definition || ?def concept')
		self.say('Technorati: ?info blog.com || ?last blog.com')
		self.say('Amazon: ?amazon words || ?isbn ISBN')
		self.say('Google: ?search words')
	
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
			self.say('I cannot read %s\'s info' % (m))

	def cmd_search(self, m):
		""" Search in technorati """
		if (m == ""):
			return
		try:
			search = technorati.search(m)
			if (len(search.item) == 0):
				# Any result
				self.say('Google does not know anything about %s' % (m))
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
				self.say('Google does not know anything about %s' % (m))
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
			self.say('I cannot search %s' % (m))

	def cmd_blogrep(self, m):
		self.cmd_search(m)

	def cmd_amazon(self, m):
		""" Search keywords in Amazon """
		if (m == ""):
			return
		try:
			search = amazon.searchByKeyword(m)
			if (len(search) == 0):
				self.say('Amazon does not know anything about %s' % (m))
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
			self.say('I cannot search %s' % (m))
			
	def cmd_isbn(self, m):
		""" Search ISBN in Amazon """
		if (m == ""):
			return
		try:
			search = amazon.searchByASIN(m)
			if (len(search) == 0):
				self.say('Amazon does not know anything about %s' % (m))
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
			self.say('I cannot search %s' % (m))
	
	def cmd_learn(self, m):
		""" Learn a definition """
		if (m == ""):
			return
		words = m.split()
		if (len(words) < 3):
			self.say('?learn some-concept is Not-very-long-definition ;)')
			return
		try:
			pos = words.index('is') 
		except:
			self.say('I need an \'is\' in the middle')
			return
		
		concept = string.lower(' '.join(words[:pos]))
		definition = ' '.join(words[pos+1:])
		if (self.definitions.has_key(concept)):
			definition = '%s and %s' % (self.definitions[concept],definition)
		self.definitions[concept] = definition
		
		# Save definition in file
		try:
			f = open(self.def_file, 'w')
			pickle.dump(self.definitions, f)
			f.close()
			self.say('I am a smarter bot.')
		except:
			pass
			
	def cmd_def(self, m):
		""" Display a stored definition """
		if (m == ""):
			[self.say("%s is %s" % (k, v)) for k, v in self.definitions.items()] 
			return
		concept = string.lower(m)
		if (self.definitions.has_key(concept)):
			self.say('%s is %s' % (m, self.definitions[concept]))
		else:
			self.say('I don\'t know anything about %s' % (m))

	def cmd_introduce(self, m):
		""" Introductions """
		self.say('Excuse me, Joi Ito has ordered me (yes, really!) to say this:')
		self.say('dsifry, who doesn\'t seem to be at his computer is the Technorati guy')
		self.say('Kevin Burton, the newsmonster guy')
		self.say('Pete is the flash guy. ;-)')
		self.say('<femtoid> Flash guy?')
		self.say('Pete is captain flash.')
		self.say('rvr is Victor Ruiz')
		self.say('Kevin Marks is away, but he\'s the limericks guy.')
		self.say('And datum is a stupid bot. I\'m better. Of course.')

if __name__ == '__main__':
	while (1):
		try:
			bot = jibot()
			bot.loop()
			
		except irclib.IrcNetworkError, msg:
			print 'lost connection,', msg
