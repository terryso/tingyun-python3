# -*- coding: utf-8 -*-

import json
import logging

from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, ApdexMetric, TracedError, node_start_time, node_end_time
from tingyun.logistics.attribution import TracedExternalError, TracedException
from tingyun.config.settings import global_settings

console = logging.getLogger(__name__)
_TrackerNode = namedtuple('_TrackerNode', ['type', 'group', 'name', 'start_time', 'end_time', 'request_uri',
                                           'duration', 'http_status', 'exclusive', 'children', 'path', "errors",
                                           "apdex_t", "request_params", "custom_params", "thread_name", "trace_data",
                                           "referer", "slow_sql", "queque_time", "trace_guid", 'trace_id',
                                           "external_error", "trace_interval", "is_root", 'exception'])

try:
    from traceback import FrameSummary
except ImportError:
    class FrameSummary:
        pass


class TrackerNode(_TrackerNode):
    """hold the tracker trace data for collect
    """

    def time_metrics(self):
        """
        :return:
        """
        if self.is_root:
            yield TimeMetric(name=self.path, scope=self.path, duration=self.duration, exclusive=self.exclusive)

            queque_metric = 'GENERAL/WebFrontend/NULL/QueueTime'
            yield TimeMetric(name=queque_metric, scope=queque_metric, duration=self.queque_time,
                             exclusive=self.queque_time)

        for child in self.children:
            for metric in child.time_metrics(self, self):
                yield metric

    def quantile(self):
        """
        :return:
        """
        return self.path, self.duration

    def action_metrics(self):
        """
        :return: the full tracker metric of the top
        """
        if self.type != "WebAction":
            return

        if self.http_status > 401:
            console.debug("Abnormal status code %s with uri %s", self.http_status, self.request_uri)
            return

        if self.is_root:
            yield TimeMetric(name=self.path, scope="", duration=self.duration, exclusive=self.exclusive)
        else:
            for child in self.children:
                for metric in child.action_metrics(self, self):
                    yield metric

    def apdex_metrics(self):
        """
        :return:
        """
        if self.type != "WebAction":
            console.debug("get apdex with none webaction %s", self.type)
            return

        satisfying = 0
        tolerating = 0
        frustrating = 0

        # status code large than 400 but not 401, we think it frustrating
        if (self.http_status >= 400 and self.http_status != 401) or self.errors:
            frustrating = 1
        else:
            if self.duration <= self.apdex_t:
                satisfying = 1
            elif self.duration <= 4 * self.apdex_t:
                tolerating = 1
            else:
                frustrating = 1

        name = self.path.replace("WebAction", "Apdex")
        yield ApdexMetric(name=name, satisfying=satisfying, tolerating=tolerating, frustrating=frustrating,
                          apdex_t=self.apdex_t)

    def transform_stack_format(self, stacks):
        """compatible py2 & py3 stack trace format
        :param stacks:
        :return:
        """
        result = []
        stacks = stacks or []

        for s in stacks:

            if isinstance(s, FrameSummary):
                result.append((s.filename, s.lineno, s.name, s._line))
            else:
                result = stacks
                break

        return result

    def format_stack_trace(self, stack_trace):
        """
        :param stack_trace:  traceback.extract_tb 解析出来的trace数据
        :return:
        """
        stacks = self.transform_stack_format(stack_trace)
        return ["%s(%s:%s)" % (s[2], s[0], s[1]) for s in stacks if len(s) >= 4 and 'tingyun' not in s[0]]

    def parse_exception_detail(self, ex_node):
        """
        :param ex_node: ExceptionNode
        :return: []
        """
        detail = []
        exceptions = [ex_node] if not isinstance(ex_node, list) else ex_node

        for ex in exceptions:
            if not ex:
                continue

            detail.append({
                "message": ex.message, "class": ex.class_name,
                "stacktrace": self.format_stack_trace(ex.stack_trace)}
            )

        return detail

    def traced_error(self):
        """yield the traced errors according to protocol
        :return:
        """
        if not self.errors:
            return

        error = self.errors
        error_filter_key = "%s_|%s_|%s_|%s" % (self.path, error.http_status, error.error_class_name, error.message)
        error_item = [error.error_time, self.path, self.http_status, error.error_class_name, error.message,
                      1, self.request_uri]
        stack_detail = self.format_stack_trace(error.stack_trace)
        error_params = {"params": {"threadName": error.thread_name, "httpStatus": self.http_status,
                                   "referer": error.referer},
                        "requestParams": error.request_params,
                        "stacktrace": stack_detail
                        }

        error_item.append(json.dumps(error_params))
        error_item.append(self.trace_guid)

        yield TracedError(error_filter_key=error_filter_key, tracker_type=error.tracker_type, trace_data=error_item)

    def trace_node(self, root):
        """
        :param root: the root node of the tracker
        :return: traced node
        """
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        metric_name = self.path
        call_url = self.request_uri
        call_count = 1
        class_name = ""
        # 如果该节点未非根节点，强制使用常量名称
        method_name = self.name if root.is_root else "execute"
        params = {}
        children = []

        root.trace_node_count += 1
        for child in self.children:
            if root.trace_node_count > root.trace_node_limit:
                break

            children.append(child.trace_node(root))

        return [start_time, end_time, metric_name, call_url, call_count, class_name, method_name, params, children]

    def slow_action_trace(self, limit, threshold):
        """ the main interface to data engine
        :param limit: the maximum limitation of the nodes
        :param threshold: this value is dynamic from server. then pass from packager
        :return:
        """
        self.trace_node_limit = limit
        self.trace_node_count = 0
        start_time = int(self.start_time)
        duration = self.duration
        trace_id = self.trace_id
        trace_guid = self.trace_guid

        # 被调用方如果产生慢过程，调用方，需要强制触发该慢过程
        has_slow_action = True if duration >= threshold else False
        for td in self.trace_data.values():
            if td.get("tr", 0):
                has_slow_action = True
                break

        if not has_slow_action:
            return None

        trace_node = self.trace_node(self)
        custom_params = {"httpStatus": self.http_status, "threadName": self.thread_name, "referer": self.referer,
                         }
        custom_params.update(self.custom_params)
        slow_trace = [start_time, self.request_params, custom_params, trace_node]

        # 由异常引发错误时，异常和错误同时记录，此时最后一段数据只需要算异常个数即可
        return [start_time, duration, self.path, self.request_uri, json.dumps(slow_trace),
                trace_id, trace_guid, 0 if not self.errors else 1, len(self.exception)]

    def slow_sql_nodes(self):
        """
        :return:
        """
        for item in self.slow_sql:
            yield item.slow_sql_node(self)

    def traced_external_error(self):
        """
        :return:
        """
        # if has exception, drop the external error
        if self.exception:
            return

        for error in self.external_error:
            metric_name = 'External/%s/%s' % (error.url.replace("/", "%2F"), error.module_name)
            error_item = [error.error_time, metric_name, error.status_code,
                          error.error_class_name, 1, self.path]

            stack_detail = self.format_stack_trace(error.stack_trace)
            error_params = {"params": {"threadName": error.thread_name, "httpStatus": self.http_status},
                            "requestParams": error.request_params, "stacktrace": stack_detail}
            error_item.append(json.dumps(error_params))

            error_filter_key = "%s_|%s_|%s" % (metric_name, self.http_status, error.error_class_name)
            yield TracedExternalError(error_filter_key=error_filter_key, trace_data=error_item,
                                      tracker_type=error.tracker_type, status_code=self.http_status)

    def traced_exception(self):
        """处理捕获到的异常数据, 获取该数据必须在slowAction后面执行,因为slowAction最后一段数据需要统计exception和错误的总数
        :return:
        """
        # 如果异常引发错误，丢掉异常
        if self.errors:
            return

        http_status = 0
        settings = global_settings()
        max_msg = settings.exception.max_msg_character

        for ex in self.exception:
            filter_key = '%s_|%s_|%s' % (self.path.replace('%2F', '/'), ex.class_name, ex.message[:max_msg])
            stack_detail = self.format_stack_trace(ex.stack_trace)
            exception_item = [ex.exception_time, self.path, http_status, ex.class_name, ex.message,
                              1, self.request_uri, json.dumps({"stacktrace": stack_detail}), self.trace_guid]

            yield TracedException(filter_key=filter_key, trace_data=exception_item, tracker_type=ex.tracker_type)
