#!/usr/bin/env python
from ConfigParser import ConfigParser
class JibotConfig(ConfigParser):
    def __init__(self, defaults_override=None):
        defaults = {
            "cmd_chars":"?",
            "herald":"True",
            "owners":"imajes,JoiIto,rvr,KevinMarks,termie",
            "nick":"jibot",
            "server":"irc.freenode.net",
            "port":"6667",
            "ircname":"#JoiIto's Bot",
            "user":"jibot",
            "channels":"joiito",
            "bots":"xena,datum,shorten,workbench,surly,chomp",
            "bots_ignore":"True",
            "silent":"False",
            "identify":"False",
            "identify_key_file":"indentifykey.txt",
            "check_identification":"True",
            "queen":"jeanniecool",
            "speech":"PRIVMSG",
            "debug":"False",
            "db_type":"sqlite",
            "def_file":"jibot.def",
            "def_buffer":"5",
            "def_join_char_long":"&",
            "def_join_char_short":"and",
            "karma_file":"jibot.karma",
            "karma_buffer":"15",
            "alias_file":"jibot.alias",
            "alias_buffer":"20",
            "masternick_file":"jibot.masternick",
            "masternick_buffer":"20",
            "herald_file":"jibot.herald",
            "herald_buffer":"2",
            "favor_file":"jibot.favor",
            "favor_buffer":"1",
            "log_level":"WARNING", #OFF, CRITICAL, ERROR, WARNING, INFO, DEBUG
            "log_file":"jibot.log",
            "log_rotate":"False",
            "log_rotate_count":"7",
            "log_rotate_bytes":"102400", # 100kb
            "log_buffer":"False",
            "log_buffer_bytes":"2048", # 2kb
            "advanced_log_config":"False", # This won't work yet, but would use fileConfig
            "strip_unprintables":"True"
        }
        if None != defaults_override:
            for k, v in defaults_override:
                defaults[k] = v
        ConfigParser.__init__(self, defaults)
