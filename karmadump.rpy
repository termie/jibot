from twisted.web.woven import page
import string, sys, os, re
import cPickle as pickle

model = {'name': "Jibot's karma"} 
jibotFolder = os.path.dirname(__file__)
brainpath = os.path.join(jibotFolder,'jibot.kar')
try:
	f = open(brainpath, 'r')
	defs= pickle.load(f)
	f.close()
	ranks = [(v,k) for k,v in defs.items()]
	ranks.sort()
	ranks.reverse()
	model['defs'] = ['%d: %s' % l for l in ranks]
except:
	defs = ["error:Can't find jibot.kar"]

resource = page.Page(model, templateFile='karmatemplate.html', templateDirectory=jibotFolder)

