# -*- coding: utf-8 -*-

from collections import namedtuple

_ExceptionNode = namedtuple('_ExceptionNode', ['exception_time', "class_name",  "message", 'stack_trace',
                                               "tracker_type"])


class ExceptionNode(_ExceptionNode):
    """
    """
    pass
