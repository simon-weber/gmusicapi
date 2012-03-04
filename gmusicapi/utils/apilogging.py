"""Logging support for the entire package."""

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmusicapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmusicapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmusicapi.  If not, see <http://www.gnu.org/licenses/>.

import logging

root_logger_name = "gmusicapi"
log_filename = "gmusicapi.log"

#Logging code adapted from: 
# http://docs.python.org/howto/logging-cookbook.html#logging-cookbook

class LogController():
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

class UsesLog():
    """A mixin to provide the ability to get a unique logger."""
    
    #Sometimes we want a logger for the class, other times for the instance.
    #Leave it up to the derived class to pick the correct one.
    #TODO: there's probably a way to just use one exposed method here.

    @classmethod
    def init_class_logger(cls):
        cls.log = LogController().get_logger(
            "{0}.{1}".format(root_logger_name, cls.__name__), unique=True)

    def init_logger(self):
        self.log = LogController().get_logger(
            "{0}.{1}".format(root_logger_name, self.__class__.__name__), unique=True)
