======================
听云 Python Agent
======================

    该安装包为北京基调网络股份有限公司提供用于应用性能管理的采集客户端，旨在对Python Web应用的全栈性能监测以及采样提供支持。更多资讯请移步听云 `官方网站 <http://www.tingyun.com>`_

安装
------------
使用python包常见安装方法:

    *pip install tingyun*


使用
-------------
    **注**：以下示例，为在linux shell终端下执行。 探针启动时需要的 **配置文件** 环境变量"TING_YUN_CONFIG_FILE"也可以直接设置到操作系统环境里，或者类似示例一样直接设置到当前应用启动的局部环境变量中。

    1、使用听云为用户分发的licenseKey生成配置文件
            *tingyun-admin  generate-config <ACCOUNT-LICENSE-KEY> $config-file-path.ini*

       例如：
            *tingyun-admin  generate-config 111-111-111 /tmp/ty-agent-config.ini*

    2、使用探针启动web应用
            *TING_YUN_CONFIG_FILE=$config-file-path tingyun-admin run-program <APPLICATION-START-COMMAND>*

        例如（启动django应用）：
            *TING_YUN_CONFIG_FILE=/tmp/ty-agent-config.ini tingyun-admin run-program python manage.py runserver 0.0.0.0:8800*