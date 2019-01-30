# -*- coding: utf-8 -*-

"""

"""

import logging
from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, node_start_time, node_end_time


console = logging.getLogger(__name__)
_MemcacheNode = namedtuple('_MemcacheNode', ['command', 'children', 'start_time', 'end_time', 'duration', 'exclusive',
                                             'host', 'port', 'exception'])


class MemcacheNode(_MemcacheNode):
    """
    """
    def time_metrics(self, root, parent):
        """
        :param root: the root node of the tracker
        :param parent: the parent node object
        :return:
        """
        command = str(self.command).upper()

        name = 'GENERAL/Memcached/%s:%s/All' % (self.host, self.port)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'GENERAL/Memcached/NULL/All'
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebAction':
            name = "GENERAL/Memcached/NULL/AllWeb"
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)
        else:
            name = "GENERAL/Memcached/NULL/AllBackgound"
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'Memcached/%s:%s/%s' % (self.host, self.port, command)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'GENERAL/Memcached/%s:%s/%s' % (self.host, self.port, command)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return: traced node
        """
        command = "Memcached:%s" % self.command
        params = {}
        children = []
        call_count = 1
        class_name = ""
        root.trace_node_count += 1
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        metric_name = 'Memcached/%s:%s/%s' % (self.host, self.port, command)

        # exception不存在，不能加入该key值
        if self.exception:
            params['exception'] = root.parse_exception_detail(self.exception)

        return [start_time, end_time, metric_name, "", call_count, class_name, command, params, children]
