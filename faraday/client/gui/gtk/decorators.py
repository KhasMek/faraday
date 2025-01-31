# Faraday Penetration Test IDE
# Copyright (C) 2016  Infobyte LLC (http://www.infobytesec.com/)
# See the file 'doc/LICENSE' for the license information
import requests
from gi.repository import Gtk
from faraday.server.utils.logger import get_logger
from functools import wraps
from compatibility import CompatibleScrolledWindow as GtkScrolledWindow
from faraday.client.persistence.server.server_io_exceptions import ServerRequestException

def safe_io_with_server(response_in_emergency):
    """A function that takes a response_in_emergency. It will return
    a safe_decorator, which will try to execture a funcion and in case
    anything happens, it will return the response in emergency.
    """
    def safe_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except ServerRequestException as e:
                res = response_in_emergency
                get_logger("Server-GTK IO").warning(e)
            except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema):
                res = response_in_emergency
                get_logger("Server-GTK IO").error("It looks like the Faraday Server "
                        "URL is not correctly formated. Please change it and "
                        "remember to set it with a valid protocol, like http.\n"
                        "For example: http://faradayserver:port/")
            except Exception:
                res = response_in_emergency
                get_logger("Server-GTK IO").error("It looks like the Faraday Server is not running\n")

            return res
        return wrapper
    return safe_decorator

def scrollable(width=-1, height=-1, overlay_scrolling=False):
    """A function that takes optinal width and height and returns
    the scrollable decorator. -1 is the default GTK option for both
    width and height."""
    def scrollable_decorator(func):
        """Takes a function and returns the scroll_object_wrapper."""
        @wraps(func)
        def scroll_object_wrapper(*args, **kwargs):
            """Takes arguments and obtains the original object from
            func(*args, **kwargs). Creates a box and puts the original
            inside that box. Creates a scrolled window and puts the
            box inside it.
            """

            original = func(*args, **kwargs)
            scrolled_box = GtkScrolledWindow(None, None)
            scrolled_box.set_min_content_width(width)
            scrolled_box.set_min_content_height(height)
            scrolled_box.set_overlay_scrolling(overlay_scrolling)
            scrolled_box.add(original)
            return scrolled_box

        return scroll_object_wrapper

    return scrollable_decorator
