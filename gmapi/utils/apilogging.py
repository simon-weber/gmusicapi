"""Logging support for the entire package."""

import logging

root_logger_name = "gmapi"
log_filename = "gmapi.log"

#Logging code adapted from: 
# http://docs.python.org/howto/logging-cookbook.html#logging-cookbook

class LogController():

    #Set up the logger for the entire application:
    logger = logging.getLogger(root_logger_name)
    logger.setLevel(logging.DEBUG)

    # create file handler to log debug info
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("!-- Starting log --!")

    
    def get_logger(self, name):
        return logging.getLogger(name)
