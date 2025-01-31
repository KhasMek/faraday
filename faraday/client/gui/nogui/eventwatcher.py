'''
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

'''

from faraday.server.utils.logger import get_logger
from faraday.client.gui.customevents import CHANGEFROMINSTANCE


class EventWatcher(object):
    def __init__(self):
        self.logger = get_logger(self)

    def update(self, event):
        if event.type() == CHANGEFROMINSTANCE:
            get_logger(self).info(
                "[Update Received] " + event.change.getMessage())
