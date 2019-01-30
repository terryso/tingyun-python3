# -*- coding: utf-8 -*-

"""
"""

import logging
from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, ExternalTimeMetric, node_start_time, node_end_time
from tingyun.logistics.workshop.packets import ExternalTimePackets, TimePackets

console = logging.getLogger(__name__)
_ExternalNode = namedtuple('_ExternalNode', ['library', 'url', 'children', 'start_time', 'end_time', 'protocol',
                                             'duration', 'exclusive', 'external_id', 'exception'])


class ExternalNode(_ExternalNode):
    """

    """

    def time_metrics(self, root, parent):
        """
        :param root: the top node of the tracker
        :param parent: parent node.
        :return:
        """
        url = self.url.replace("/", "%2F")

        # 产生跨应用时，统计信息需要变更，且单独在performance中产生一条ExternalTransaction数据
        trace_data = root.trace_data.get(self.external_id, None)
        if trace_data:
            packets = ExternalTimePackets
            app_time = trace_data.get("time", {}).get("duration", 0)
            queque_time = trace_data.get("time", {}).get("qu", 0)
            net_time = self.exclusive - app_time - queque_time
            console.debug("Get the across network time %s", net_time)

            callee_action = trace_data.get("action", "None").replace("%2F", "/")
            server_data = '%s%%2F%s' % (trace_data.get("id", "No-Id-Exist"), callee_action)
            backend_time = app_time + queque_time if net_time >= 0 else app_time
            name = 'ExternalTransaction/%s/%s' % (url, server_data)
            yield ExternalTimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=backend_time,
                                     packets=packets())

            name = 'GENERAL/ExternalTransaction/NULL/%s' % trace_data.get("id")
            yield TimeMetric(name=name, scope=root.path, duration=backend_time, exclusive=0)

            name = 'GENERAL/ExternalTransaction/%s/%s' % (self.protocol, trace_data.get("id"))
            yield TimeMetric(name=name, scope=root.path, duration=backend_time, exclusive=0)

            name = 'GENERAL/ExternalTransaction/%s:sync/%s' % (self.protocol, trace_data.get("id"))
            yield TimeMetric(name=name, scope=root.path, duration=backend_time, exclusive=0)

        name = 'GENERAL/External/NULL/All'
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=0)

        name = "GENERAL/External/NULL/AllWeb"
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=0)

        name = 'External/%s/%s' % (url, self.library)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.duration)

        name = 'GENERAL/External/%s/%s' % (url, self.library)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=0)

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return:
        """
        params = {}
        children = []
        call_count = 1
        class_name = ""
        method_name = self.library
        call_url = self.url
        root.trace_node_count += 1
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        metric_name = 'External/%s/%s' % (self.url.replace("/", "%2F"), self.library)

        # 当作为调用者时，该数据才会从上报，否则该id会跟着跨应用数据上报服务器
        if self.external_id:
            params['externalId'] = self.external_id

        if root.trace_id:
            params['txId'] = root.trace_id

        trace_data = root.trace_data.get(self.external_id, None)
        if trace_data:
            params['txData'] = trace_data

        # exception不存在，不能加入该key值
        if self.exception:
            params['exception'] = root.parse_exception_detail(self.exception)

        return [start_time, end_time, metric_name, call_url, call_count, class_name, method_name, params, children]
