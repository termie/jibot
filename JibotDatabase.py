#!/usr/bin/env python

import cPickle as pickle
import sqlite

class JibotDatabase:
    """ A very simple database interface for jibot, not PEP249 Compatible """
    def __init__(self,logger,name=None,buffer_capacity=1):
        self._name=name
        self._logger=logger
        self._dict={}
        self._queue=[]
        self._buffer_capacity=int(buffer_capacity) # How many commands to queue before execution
        
    def load(self):
        """ Load the data into the object memory from the DB"""
        pass
    
    def flush(self):
        self._queue=[]
        self._logger.info("Flushing queue for database '%s'"%(self._name))
    
    def _should_flush(self):
        if len(self._queue) > self._buffer_capacity:
            self._logger.debug("Ready to flush buffer for database '%s'"%(self._name))
            return True
        else: 
            return False
    
    def get(self,key,default=None):
        return self._dict.get(key.lower(),default)
    
    def put(self,key,value):
        key = key.lower()
        if key not in self._dict:
            self._dict[key]=value
            self._queue.append({"cmd":"put","args":(key,value)})
            if self._should_flush(): 
                self.flush()
 
    def set(self,key,value):
        key = key.lower()
        self._dict[key] = value
        self._queue.append({"cmd":"set","args":(key,value)})
        if self._should_flush(): 
            self.flush()
    
    def batch_put(self,entries):
        for k,v in entries.items():
            key = k.lower()
            value = v
            if k not in self._dict: self._dict[key]=value
            self._queue.append({"cmd":"put","args":(key,value)})
        if self._should_flush(): self.flush()
    
    def batch_set(self,entries):
        for key,value in entries.items():
            key = key.lower()
            self._dict[key]=value
            self._queue.append({"cmd":"set","args":(key,value)})
        if self._should_flush(): self.flush()    
        
    def remove(self,key):
        key = key.lower()
        if key in self._dict:
            del self._dict[key]
            self._queue.append({"cmd":"remove","args":(key)})
            if self._should_flush(): self.flush()
    
    def clear(self):
        self._dict.clear()
    
    def keys(self):
        return self._dict.keys()
    
    def has_key(self,key):
        return self._dict.has_key(key.lower())
    
    def values(self):
        return self._dict.values()
    
    def copy(self):
        return self._dict.copy()
    
    def items(self):
        return self._dict.items()
    
    def iteritems(self):
        return self._dict.iteritems()
    
    def get_name(self):
        return self._name
    
    def set_buffer_capacity(self,i):
        self._buffer_capacity=i


# Escape functions grabbed from Glen Starchman on the python mailing list
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


class PickleDB(JibotDatabase):
    def __init__(self,file,logger,name="PickleDB",buffer_capacity=1):
        JibotDatabase.__init__(self,name=name,logger=logger,buffer_capacity=buffer_capacity)
        self._file = file
        
    def load(self):
        try:
            f = open(self._file, 'r')
            data = pickle.load(f)
            f.close()
            self._logger.info("Loaded %d entries from %s" %(len(data), self._file))
        except:
            self._logger.exception("Could not load entries from %s"%(self._file), exc_info=1)
            data = {}
        self._dict = data
    
    def _dump(self):
        try:
            f = open(self._file, 'w')
            pickle.dump(self._dict, f)
            f.close()
            self._logger.info("Dumped %d entries to %s"%(len(self._dict), self._file))
        except:
            self._logger.exception("Could not dump to file %s" %(self._file))
    
    def flush(self):
        JibotDatabase.flush(self)
        self._dump()

class SQLite(JibotDatabase):
    """ Strings are not yet escaped, but they need to be """
    def __init__(self,file,table,logger,name="SQLite",buffer_capacity=1):
        JibotDatabase.__init__(self,name=name,logger=logger,buffer_capacity=buffer_capacity)
        self._file = file
        self._table = table

    
    def load(self):
        try:
            db = sqlite.connect(self._file)
            cu = db.cursor()
            cu.execute("SELECT key, value FROM %s"%(escape(self._table)))
            rows = cu.fetchall()
            data = {}
            for k,v in rows:
                data[unescape(k)]=unescape(v)
            self._logger.info("Loaded %d entries from %s"%(len(data),self._table))
            db.close()
        except sqlite.DatabaseError, msg:
            if "no such table" == msg[0][:13]:
                self._logger.warning("Table '%s' not found, creating."%(self._table))
                cu.execute("CREATE TABLE %s (key VARCHAR, value VARCHAR)"%(escape(self._table)))
                db.commit()
            else:
                self._logger.exception("Could not load entries from %s"%(self._table))
            data = {}
            db.close()
        except:
            self._logger.exception("Could not load entries from %s"%(self._table))
            data = {}
        self._dict = data

    def flush(self):
        try:
            db = sqlite.connect(self._file)
            cu = db.cursor()
            for item in self._queue:
                cmd = item['cmd']
                args = escape(item['args'])
                table = escape(self._table)
                if "set" == cmd:
                    cu.execute("UPDATE %s SET value='%s' WHERE key='%s'"%(table,args[1],args[0]))
                elif "put" == cmd:
                    cu.execute("INSERT INTO %s (key, value) VALUES ('%s', '%s')"%(table,args[0],args[1]))
                elif "remove" == cmd:
                    cu.execute("DELETE FROM %s WHERE key='%s'"%(table,args[0]))
                else:
                    self._logger.warn("Invalid queue item in database object '%s'"%(self._name))
            db.commit()
            self._logger.info("Wrote %d changes to the database '%s'"%(len(self._queue),self._name))
            db.close()
            JibotDatabase.flush(self)
        except:
            self._logger.exception("Failed to write to the database '%s'"%(self._name))
        
class DatabaseWrapper:
    def __init__(self,database):
        self._database=database
    
    def load(self):
        self._database.load()
    
    def flush(self):
        self._database.flush()
    
    def get(self,key,default=None):
        return self._database.get(key,default)
    
    def put(self,key,value):
        self._database.put(key,value)
 
    def set(self,key,value):
        self._database.set(key,value)
    
    def batch_put(self,entries):
        self._database.batch_put(entries)
    
    def batch_set(self,entries):
        self._database.batch_set(entries)   
        
    def remove(self,key):
        self._database.remove(key)
    
    def clear(self):
        self._database.clear()
    
    def keys(self):
        return self._database.keys()
    
    def has_key(self,key):
        return self._database.has_key(key)
    
    def values(self):
        return self._database.values()
    
    def copy(self):
        return self._database.copy()
    
    def items(self):
        return self._database.items()
    
    def iteritems(self):
        return self._database.iteritems()
    
    def get_name(self):
        return self._database.get_name()
    
    def set_buffer_capacity(self,i):
        self._database.set_buffer_capacity(i)

class MasterNickWrapper(DatabaseWrapper):
    def __init__(self,database):
        DatabaseWrapper.__init__(self,database)
        self._db_join="&"
    
    def get(self,key,default=''):
        return self._database.get(key,default).split(" %s "%(self._db_join))
    
    def set(self,key,value):
        self._database.set(key,(" %s "%(self._db_join)).join(value))

    def put(self,key,value):
        self._database.put(key,(" %s "%(self._db_join)).join(value))

class DefWrapper(DatabaseWrapper):
    def __init__(self,database,join_char_long="&",join_char_short="and"):
        DatabaseWrapper.__init__(self,database)
        self._join_char_short=join_char_short
        self._join_char_long=join_char_long
        self._db_join="&"
    
    def has_def(self,key):
        return self._database.has_key(key)
    
    def get_def(self,key,start=0,end=None,step=1,join=False):
        # I know, the full functionality will never be used...    
        out = self._database.get(key)
        # We may be able to get rid of this once all old defs have been re-parsed...    
        if None != out:
            out = out.replace(" and ", " %s "%(self._db_join)).split(" %s "%(self._db_join))
            out = filter(lambda x: len(x) > 3, out)
            # Some auto correction for the database: removes the entry if
            # there are no good defs...
            if 1 > len(out):
                self._database.remove(key)
        if None == out:
            out = []
        if None == end:
            out = out[start::step]
        else:
            out = out[start:end:step]
        if join:
            if 5 > len(out):
                join_char = self._join_char_short
            else:
                join_char = self._join_char_long
            out = (" %s "%(join_char)).join(out)
        return out
    
    def get_def_first(self,key):
        """ Shortcut """
        return self.get_def(key,join=False)[0]
    
    def get_def_all(self,key):
        """ Shortcut, sort of """
        return self.get_def(key,join=True)
    
    def add_def(self,key,s):
        if type(s) == type([]) or type(s) == type(()):
            s = (" %s "%(self._db_join)).join(s)
        if self.has_def(key):
            def_list = self.get_def(key)
            s_list = s.split(" and ")
            for s in s_list:
                def_list.append(s)
            self._database.set(key,(" %s "%(self._db_join)).join(def_list))
            
        else:
            self._database.put(key,s)
        
    def set_def(self,key,s):
        if type(s) == type([]) or type(s) == type(()):
            s = (" %s "%(self._db_join)).join(s)
        self._database.set(key,s)
    
    def remove_def(self,key,s):
        try:
            def_list = self.get_def(key)
            i = def_list.index(s)
            del def_list[i]
            if 1 > len(def_list):
                self._database.remove(key)
            else:
                self._database.set(key,(" %s "%(self._db_join)).join(def_list))
            return True
        except:
            return False
    
class HeraldWrapper(DatabaseWrapper):
    def __init__(self,database):
        DatabaseWrapper.__init__(self,database)
    
    def set_herald_nick(self,nick,herald=True):
        """ These _herald_nick functions are a bit misnamed, should be heraldfirst or something """
        if self._database.has_key(nick):
            self._database.set(nick,herald)
        else:
            self._database.put(nick,herald)
        return bool(herald)

    def toggle_herald_nick(self,nick):
        if self.get_herald_nick(nick): return self.set_herald_nick(nick,False)
        else: return self.set_herald_nick(nick,True)
        
    def get_herald_nick(self,nick):
        return bool(self._database.get(nick,False))
    
class KarmaWrapper(DatabaseWrapper):
    def __init__(self,database):
        DatabaseWrapper.__init__(self,database)
        
    def add_karma(self,key):
        if self._database.has_key(key):
            self._database.set(key,int(self._database.get(key))+1)
        else:
            self._database.put(key,1)
    
    def sub_karma(self,key):
        if self._database.has_key(key):
            self._database.set(key,int(self._database.get(key))-1)
        else:
            self._database.put(key,-1)
    
    def get_karma(self,key):
        return int(self._database.get(key,0))
    
class FavorWrapper(DatabaseWrapper):
    def __init__(self,database):
        DatabaseWrapper.__init__(self,database)
        
    def get_favor(self,nick,default=0):
        return int(self._database.get(nick,default))
    
    def set_favor(self,nick,favor=1):
        if self._database.has_key(nick):
            self._database.set(nick,favor)
        else:
            self._database.put(nick,favor)
    
    def get_favorites(self):
        favs = []
        for k,v in self._database.iteritems():
            if int(v) > 0: favs.append(k)
        return favs

    def get_disfavorites(self):
        disfavs = []
        for k,v in self._database.iteritems():
            if int(v) < 0: disfavs.append(k)
        return disfavs
    
    def pardon(self,nick):
        """ Shortcut """
        self.set_favor(nick,favor=0)
    
    def unfavor(self,nick):
        """ Shortcut """
        self.set_favor(nick,favor=0)
    
    def favor(self,nick):
        """ Shortcut """
        self.set_favor(nick,favor=1)
    
    def disfavor(self,nick):
        """ Shortcut """
        self.set_favor(nick,favor=-1)
        
