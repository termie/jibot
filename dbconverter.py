#!/usr/bin/python
# This is a very one-sided, poor database coverter to convert from the 
# old jibot pickle files to the sqlite files
# You will have to change the infiles for all the functions to make it work
# Escape functions grabbed from Glen Starchman on the python mailing list
import cPickle as pickle
import sqlite

mappings = {"'":"''",
           '"':'""',
           ' ':'+'
           }

def escape_list(l):
    arg_lst = []
    if len(l)==1:
        return escape(args[0])
    for x in l:
        arg_lst.append(escape(x))
    return tuple(arg_lst)
    
def escape(x):
    if type(x)==type(()) or type(x)==type([]):
        return escape_list(x)
    if type(x)==type(""):
        tmpstr=''
        for c in range(len(x)):
            if x[c] in mappings.keys():
                if x[c] in ("'", '"'):
                    if c+1<len(x):
                        if x[c+1]!=x[c]:
                            tmpstr+=mappings[x[c]]
                    else:
                        tmpstr+=mappings[x[c]]
                else:
                    tmpstr+=mappings[x[c]]
            else:
                tmpstr+=x[c]
    else:
        tmpstr=x
    return tmpstr

def unescape(val):
    if type(val)==type(""):
        tmpstr=''
        for key,item in mappings.items():
            val=val.replace(item,key)
        tmpstr = val
    else:
        tmpstr=val
    return tmpstr
    
def unescape_list(l):
    arg_lst = []
    for x in l:
        arg_lst.append(unescape(x))
    return arg_lst


def convert_def(infile="jibdb.def",outfile="jibot.def.sqlite"):
    f = open(infile, "r")
    defs = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE def (key VARCHAR, value VARCHAR)")
    for k,v in defs.items():
        key = escape(k)
        value = escape(" & ".join(v))
        cu.execute("INSERT INTO def (key, value) VALUES('%s', '%s')"%(key, value))
    cx.commit()
    
def convert_karma(infile="jibdb.karma",outfile="jibot.karma.sqlite"):
    f = open(infile, "r")
    karma = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE karma (key VARCHAR, value VARCHAR)")
    for k,v in karma.items():
        key = escape(k)
        value = v
        cu.execute("INSERT INTO karma (key, value) VALUES('%s', '%s')"%(key, value))
    cx.commit()

def convert_alias(infile="jibdb.alias",outfile="jibot.alias.sqlite"):
    f = open(infile, "r")
    alias = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE alias (key VARCHAR, value VARCHAR)")
    for k,v in alias.items():
        key = escape(k)
        value = escape(v)
        cu.execute("INSERT INTO alias (key, value) VALUES('%s', '%s')"%(key, value))
    cx.commit()

def convert_masternick(infile="jibdb.masternick",outfile="jibot.masternick.sqlite"):
    f = open(infile, "r")
    mn = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE masternick (key VARCHAR, value VARCHAR)")
    for k,v in mn.items():
        key = escape(k)
        value = escape(" & ".join(v['nicklist']))
        cu.execute("INSERT INTO masternick (key, value) VALUES('%s', '%s')"%(key, value))
    cx.commit()

def convert_favor(fav_file="jibdb.favor",dis_file="jibdb.disfavor",outfile="jibot.favor.sqlite"):
    f = open(fav_file, "r")
    fv = pickle.load(f)
    f.close()
    f = open(dis_file,"r")
    df = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE favor (key VARCHAR, value VARCHAR)")
    for k in fv:
        key = escape(k)
        value = '1'
        cu.execute("INSERT INTO favor (key, value) VALUES('%s', '%s')"%(key, value))
    for k in df:
        key = escape(k)
        value = '-1'
        cu.execute("INSERT INTO favor (key, value) VALUES('%s', '%s')"%(key, value)) 
    cx.commit()

def convert_herald(infile="jibdb.herald",outfile="jibot.herald.sqlite"):
    f = open(infile, "r")
    he = pickle.load(f)
    f.close()
    cx = sqlite.connect(outfile)
    cu = cx.cursor()
    cu.execute("CREATE TABLE herald (key VARCHAR, value VARCHAR)")
    for k,v in he.items():
        key = escape(k)
        value = '1'
        cu.execute("INSERT INTO herald (key, value) VALUES('%s', '%s')"%(key, value))
    cx.commit()

def main():
    convert_def()
    convert_karma()
    convert_alias()
    convert_masternick()
    convert_favor()
    convert_herald()

if __name__ == "__main__":
    main()
