from twisted.web.woven import page
import string, sys, os, re
import cPickle as pickle

model = {'name': "Jibot's brain"} 
jibotFolder = os.path.dirname(__file__)
brainpath = os.path.join(jibotFolder,'jibot.def')
try:
	f = open(brainpath, 'r')
	defs= pickle.load(f)
	f.close()
except:
	defs = {"error":["Can't find jibot.def"]}
model['defs'] = ['%s is %s' % (k, " and ".join(v)) for k,v in defs.items()]
model['defs'].sort()

resource = page.Page(model, templateFile='braintemplate.html', templateDirectory=jibotFolder)

