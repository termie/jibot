#!/usr/bin/env python
from JibotOptions import JibotOptions
from JibotConfig import JibotConfig
import JibotInterface, JibotDatabase
from ConfigParser import ConfigParser
import os, logging, logging.handlers, sys


# Roadmap:
#  Get command-line and config file parsing running
#  Get logging functionality up
#  Work on alternate database (SQLlite, for now)
#  Diagnosis/debug/test/benchmark functionality
#


def main ():
    cli = JibotOptions()
    options, args = cli.parse_args()

    config = JibotConfig()
    if None != options.config:
        config.read(options.config)
    else:
        config.read(['jibot.conf', os.path.expanduser('~/.jibot/jibot.conf')])
    
    # Configure Variables
    verbosity = options.verbosity

    # Configure Logging
    
#    log_level = config.get("logging", "log_level")
    log_level = "DEBUG"
    log_file = config.get("logging", "log_file")
#    log_format = config.get("logging", "log_format")
#    log_datefmt = config.get("logging", "log_datefmt")
    log_rotate = config.getboolean("logging", "log_rotate")
    log_rotate_count = config.get("logging", "log_rotate_count")
    log_rotate_bytes = config.getint("logging", "log_rotate_bytes")
    log_buffer = config.getboolean("logging", "log_buffer")
    log_buffer_bytes = config.getint("logging", "log_buffer_bytes")
    
    if 2 == options.verbosity: verbosity = logging.DEBUG
    elif 1 == options.verbosity: verbosity = logging.INFO
    else: verbosity = logging.ERROR
    
    logger=logging.getLogger("jibot")
    logger.setLevel(logging.DEBUG)
#    formatter=logging.Formatter(log_format, log_datefmt)
    formatter=logging.Formatter('%(levelname)s %(asctime)s %(message)s')
    # The runtime output
    outputHandler=logging.StreamHandler(sys.stdout)
    outputHandler.setFormatter(formatter)
    outputHandler.setLevel(verbosity)
    logger.addHandler(outputHandler)
    # File output, if turned on
    if "OFF" != log_level:
        if log_rotate:
            fileHandler=logging.handlers.RotatingFileHandler(log_file,'a',
                                                    log_rotate_bytes,
                                                    log_rotate_count)
        else: fileHandler=logging.FileHandler(log_file, 'a')
        fileHandler.setFormatter(formatter)
        fileHandler.setLevel(eval("logging.%s"%log_level))
        if log_buffer:
            bufferHandler=logging.handlers.MemoryHandler(log_buffer_bytes, logging.ERROR, fileHandler)
            logger.addHandler(bufferHandler)
        else:
            logger.addHandler(fileHandler)
    
    logger.debug("JibotLogger started")

    # Configure Database
    # For now just use what is already there, grabbing flat file names from
    # the config settings
    db_type = config.get("database", "db_type")
    def_join_char_short = config.get("database", "def_join_char_short")
    def_join_char_long = config.get("database","def_join_char_long")
    def_buffer = config.get("database", "def_buffer")
    karma_buffer = config.get("database", "karma_buffer")
    alias_buffer = config.get("database", "alias_buffer")
    masternick_buffer = config.get("database", "masternick_buffer")
    herald_buffer = config.get("database", "herald_buffer")
    favor_buffer = config.get("database", "favor_buffer")
    
    if "sqlite" == db_type:
        def_file = config.get("database", "def_file")+".sqlite"
        karma_file = config.get("database", "karma_file")+".sqlite"
        alias_file = config.get("database", "alias_file")+".sqlite"
        masternick_file = config.get("database", "masternick_file")+".sqlite"
        herald_file = config.get("database", "herald_file")+".sqlite"
        favor_file = config.get("database", "favor_file")+".sqlite"
        defDB=JibotDatabase.DefWrapper(
            JibotDatabase.SQLite(file=def_file,
                                 table='def',
                                 logger=logger,
                                 name="defDB",
                                 buffer_capacity=def_buffer),
                                       join_char_short=def_join_char_short,
                                       join_char_long=def_join_char_long)
        karmaDB=JibotDatabase.KarmaWrapper(
            JibotDatabase.SQLite(file=karma_file,
                                 table='karma',
                                 logger=logger,
                                 name="karmaDB",
                                 buffer_capacity=karma_buffer))
        aliasDB=JibotDatabase.SQLite(file=alias_file,
                                     table='alias',
                                     logger=logger,
                                     name="aliasDB",
                                     buffer_capacity=alias_buffer)
        masternickDB=JibotDatabase.MasterNickWrapper(
            JibotDatabase.SQLite(file=masternick_file,
                                 table='masternick',
                                 logger=logger,
                                 name="masternickDB",
                                 buffer_capacity=masternick_buffer))
        heraldDB=JibotDatabase.HeraldWrapper(
            JibotDatabase.SQLite(file=herald_file,
                                   table='herald',
                                   logger=logger,
                                   name="heraldDB",
                                   buffer_capacity=herald_buffer))
        favorDB=JibotDatabase.FavorWrapper(
            JibotDatabase.SQLite(file=favor_file,
                                 table='favor',
                                 logger=logger,
                                 name="favorDB",
                                 buffer_capacity=favor_buffer)) 
    elif "pickle" == db_type:
        def_file = config.get("database", "def_file")+".pickle"
        karma_file = config.get("database", "karma_file")+".pickle"
        alias_file = config.get("database", "alias_file")+".pickle"
        masternick_file = config.get("database", "masternick_file")+".pickle"
        herald_file = config.get("database", "herald_file")+".pickle"
        favor_file = config.get("database", "favor_file")+".pickle"
        defDB=JibotDatabase.DefWrapper(
            JibotDatabase.PickleDB(file=def_file,
                                   logger=logger,
                                   name="defDB",
                                   buffer_capacity=def_buffer),
                                       join_char_short=def_join_char_short,
                                       join_char_long=def_join_char_long)
        karmaDB=JibotDatabase.KarmaWrapper(
            JibotDatabase.PickleDB(file=karma_file,
                                     logger=logger,
                                     name="karmaDB",
                                     buffer_capacity=karma_buffer))
        aliasDB=JibotDatabase.PickleDB(file=alias_file,
                                     logger=logger,
                                     name="aliasDB",
                                     buffer_capacity=alias_buffer)
        masternickDB=JibotDatabase.MasterNickWrapper(
            JibotDatabase.PickleDB(file=masternick_file,
                                     logger=logger,
                                     name="masternickDB",
                                     buffer_capacity=masternick_buffer))
        heraldDB=JibotDatabase.HeraldWrapper(
            JibotDatabase.PickleDB(file=herald_file,
                                     logger=logger,
                                     name="heraldDB",
                                     buffer_capacity=herald_buffer))
        favorDB=JibotDatabase.FavorWrapper(
            JibotDatabase.PickleDB(file=favor_file,
                                     logger=logger,
                                     name="favorDB",
                                     buffer_capacity=favor_buffer))
    
    # Configure Definitions
    defDB.load()
    
    # Configure Karma
    karmaDB.load()    
    
    # Configure Nicks
    aliasDB.load()
    masternickDB.load()
    
    # Configure Heralding
    heraldDB.load()
    
    # Configure Queen
    favorDB.load()
    
    # Configure Blogging
    
    # Configure Channels            
        
    # Load the JibotInterface
    jibot = JibotInterface.JibotInterface(config=config,
                                          logger=logger)
    
    # Initialize the Handlers
    cmdHandler = JibotInterface.CmdHandler(root=jibot)
    pingHandler = JibotInterface.PingHandler(root=jibot)
    technoratiHandler = JibotInterface.TechnoratiHandler(root=jibot)
    amazonHandler = JibotInterface.AmazonHandler(root=jibot)
    googleHandler = JibotInterface.GoogleHandler(root=jibot)
    jargonHandler = JibotInterface.JargonHandler(root=jibot)
    systemHandler = JibotInterface.SystemHandler(root=jibot)
    blogHandler = JibotInterface.BlogHandler(root=jibot)
    funHandler = JibotInterface.FunHandler(root=jibot)
    defHandler = JibotInterface.DefHandler(defDB,jibot)
    karmaHandler = JibotInterface.KarmaHandler(karmaDB,jibot)
    favorHandler = JibotInterface.FavorHandler(favorDB,jibot,queen=config.get("global","queen"))
    heraldHandler = JibotInterface.HeraldHandler(heraldDB,defDB,aliasDB,\
                                                 favorHandler,root=jibot,\
                                                 herald=config.get("global","herald"))
    # Must initialize the heraldHandler before the nickHandler
    nickHandler = JibotInterface.NickHandler(aliasDB,masternickDB,defDB,heraldHandler,root=jibot)
        

    
    # Add the handlers to jibot
    jibot.add_handler(nickHandler)
    jibot.add_handler(pingHandler)
    jibot.add_handler(cmdHandler)
    cmdHandler.add_handler(nickHandler)
    cmdHandler.add_handler(defHandler)
    cmdHandler.add_handler(karmaHandler)
    cmdHandler.add_handler(favorHandler)
    cmdHandler.add_handler(heraldHandler)
    cmdHandler.add_handler(systemHandler)
    cmdHandler.add_handler(technoratiHandler)
    cmdHandler.add_handler(amazonHandler)
    cmdHandler.add_handler(googleHandler)
    cmdHandler.add_handler(jargonHandler)
    cmdHandler.add_handler(blogHandler)
    cmdHandler.add_handler(funHandler)
    
    jibot.start()
    try:
        jibot.loop()
    except KeyboardInterrupt:
        logger.error("Caught a KeyboardInterrupt, flushing databases")
    except:
        logger.exception("Something tossed an error, attempting to flush the databases")
    defDB.flush()
    karmaDB.flush()
    favorDB.flush()
    aliasDB.flush()
    masternickDB.flush()
    heraldDB.flush()   
     

if __name__ == "__main__":
    main()
