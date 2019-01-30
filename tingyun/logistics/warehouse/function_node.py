# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

from tingyun.logistics.attribution import TimeMetric, node_start_time, node_end_time


_FunctionNode = namedtuple('_FunctionNode', ['group', 'name', 'children', 'start_time', 'end_time', 'duration',
                                             'exclusive', 'params', 'stack_trace', 'exception'])
console = logging.getLogger(__name__)


class FunctionNode(_FunctionNode):
    """
    """
    def time_metrics(self, root, parent):
        """
        :param root:
        :param parent:
        :return:
        """
        name = 'Python/%s/%s' % (self.group, self.name)

        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        for child in self.children:
            for metric in child.time_metrics(root, self):
                yield metric

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return: traced node
        """
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        metric_name = 'Python/%s/%s' % (self.group, self.name)
        call_url = root.request_uri
        call_count = 1
        class_name = ""
        method_name = self.name
        params = {
            "sql": "", "stacktrace": root.format_stack_trace(self.stack_trace or []),
        }

        # exception不存在，不能加入该key值
        for ex in self.exception:
            params['exception'] = root.parse_exception_detail(ex)

        children = []

        root.trace_node_count += 1
        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break

            children.append(child.trace_node(root))

        return [start_time, end_time, metric_name, call_url, call_count, class_name, method_name, params, children]
