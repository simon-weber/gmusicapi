#!/usr/bin/env python


# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Logging support for the entire package."""

import logging

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
