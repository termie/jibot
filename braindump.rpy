from twisted.web.woven import page
import string, sys, os, re
import cPickle as pickle

model = {'name': "Jibot's brain"} 
brainpath = os.path.join(os.path.dirname(__file__),'jibot.def')
try:
	f = open(brainpath, 'r')
	defs= pickle.load(f)
	f.close()
except:
	defs = {"error":["Can't find jibot.def"]}
model['defs'] = ['%s is %s' % (k, " and ".join(v)) for k,v in defs.items()]
model['defs'].sort()
template = """<html><head>
 <title  model="name" view="Text" /></head>
  <body>
      <h3 model="name" view="Text" />
       <div model="defs" view="List">
         <p pattern="listItem" view="Text" />
      </div>
   </body>
  </html>
"""   

resource = page.Page(model, template=template)

