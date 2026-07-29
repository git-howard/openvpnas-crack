本 Python 程序（update_egg.py）是一个用于自动化修改和更新 OpenVPN Access Server (OpenVPN AS) 授权并发连接数的工具。

主要功能与工作流程：
路径确定与解压： 支持自定义 .egg 文件路径，默认自动读取 /usr/local/openvpn_as/lib/python/pyovpn-2.0-py3.12.egg，并将其解压至临时工作目录。如Docker部署，则可将相应的egg文件复制出来进行操作。

核心模块自动备份： 检查解压后的 pyovpn/lic 目录：

若不存在 uprop2.pyc，自动将原始授权模块 uprop.pyc 复制并备份重命名为 uprop2.pyc；
若已存在 uprop2.pyc（表示此前已修改过），则跳过备份，直接使用现有备份。
并发许可动态编译与注入： 交互式提示用户输入期望的授权并发连接数（如 100 或 1024），程序会在内存中生成 Hook 补丁代码，修改 concurrent_connections 的返回数值，并将其编译为 Python 3.12 字节码（uprop.pyc）直接写入 pyovpn/lic 目录。

重新打包覆盖： 将更新后的完整文件结构重新打包压缩为 .egg 格式，覆盖原有的系统库文件，并自动清理临时目录。

服务自动重启： 在打包完成后，自动调用系统命令 sudo systemctl restart openvpnas 重启 OpenVPN AS 服务，使新的并发许可设置立即生效。


理论上支持2.x和3.x和未来版本，仅用于学习和研究，请勿适用于生产环境。
