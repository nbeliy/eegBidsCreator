import logging

Logger = logging.getLogger(__name__)



def ChannelsEP(record, argv = None, params = None):
    Logger.info('Running ChannelsEP')
    if argv != None:
        Logger.info("CLI options: "+str(argv))
    if params != None:
        Logger.info("Conf options: "+str(params))

    return 0
