#!/usr/bin/env python
from optparse import OptionParser, make_option
class JibotOptions(OptionParser):
    def __init__(self, *args, **kwargs):
        usage = "usage: %prog [options] action [message]"
        optConfig = make_option(
            "-c", "--config",
            dest="config", metavar="FILE",
            help="Specify a configuration file to load")
        
        # We'd want to add support for multiple log files
        optLog = make_option(
            "-l", "--log",
            dest="log", metavar="FILE",
            help="Specify location for the log")
        optVerbose = make_option(
            "-v", "--verbose",
            action="count", dest="verbosity",
            help="Verbose output. Use twice for greater effect")
        optDatabase = make_option(
            "-d", "--database",
            dest="database", metavar="DB",
            help="Source database location")
        optInteractive = make_option(
            "-i", "--interactive",
            dest="interactiveMode", action="store_true",
            default=False,
            help="Enter interactive mode")
        optNick = make_option(
            "--nick",
            dest="nick", metavar="IRCNICK",
            help="Nickname for IRC")
        optUsername = make_option(
            "--username",
            dest="username", metavar="USER",
            help="Username for IRC")
        
        
        
        optList = [optConfig, optLog, optVerbose, optDatabase, optInteractive, optNick, optUsername]
        OptionParser.__init__(self, usage, optList, *args, **kwargs)