#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Logging support for the entire package."""

import logging
import pkg_resources

root_logger_name = "gmusicapi"
log_filename = "gmusicapi.log"

#Logging code adapted from: 
# http://docs.python.org/howto/logging-cookbook.html#logging-cookbook

class LogController(object):
    """Creates the root logger, and distributes loggers."""

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
    logger.info("version: " + pkg_resources.get_distribution("gmusicapi").version)


    #Map {Logger name: number distributed} for all distributed Loggers.
    distrib_names = {}
    distrib_names[root_logger_name] = 1

    @classmethod
    def get_logger(cls, name, unique=False):
        """Returns a logger for the given name. The root name is prepended.
        
        :param name: the base name desired.
        :param unique: if True, return a unique version of the base name."""

        name_to_give = "{0}.{1}".format(root_logger_name, name)

        already_distributed = name in cls.distrib_names

        if not already_distributed:
            cls.distrib_names[name] = 1
        else:
            if unique:
                cls.distrib_names[name] += 1
                name_to_give = "{0}.{1}_{2}".format(root_logger_name, name, cls.distrib_names[name])

        return logging.getLogger(name_to_give)

class UsesLog(object):
    """A mixin to provide the ability to get a unique logger."""
    
    #Sometimes we want a logger for the class, other times for the instance.
    #Leave it up to the derived class to pick the correct one.
    #TODO: there's probably a way to just use one exposed method here.

    @classmethod
    def init_class_logger(cls):
        cls.log = LogController().get_logger(cls.__name__, unique=True)

    def init_logger(self):
        self.log = LogController().get_logger(self.__class__.__name__, unique=True)
