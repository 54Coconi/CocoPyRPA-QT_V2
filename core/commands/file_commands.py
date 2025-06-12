"""
@author: 54Coconi
@date: 2024-11-10
@version: 1.0.0
@path: /core/commands/file_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    文件操作指令模块
"""


import shutil
import requests
from pathlib import Path
from pydantic import Field, HttpUrl
from datetime import datetime

from utils.debug import print_func_time
# 导入可重复指令基类和异常类
from .base_command import RetryCmd, CommandRunningException

_DEBUG = True


# @ <目录备份> 指令
class BackupDirCmd(RetryCmd):
    """
    BackupDirCmd 用于备份指定源目录下的所有文件到目标目录，目标目录不能为空，
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        source_dir:(Path): 源目录路径
        target_dir:(Path|str): 目标目录路径
    """
    name: str = Field("目录备份", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(1, description="指令重复执行次数")

    source_dir: Path = Field(..., description="源目录路径")
    target_dir: Path | str = Field(..., description="目标目录路径")

    @print_func_time(_DEBUG)
    def run_command(self, **kwargs):
        """ 备份源目录到目标目录的逻辑 """
        if not self.source_dir.exists() or not self.source_dir.is_dir():
            raise CommandRunningException(f"源目录 [{self.source_dir}] 不存在或不是一个目录")

        if self.target_dir == "" or self.target_dir is None:
            raise CommandRunningException(f"目标目录 [{self.target_dir}] 为空或不是一个目录")
        elif self.target_dir == "." or self.target_dir == "..":
            raise CommandRunningException(f"目标目录 [{self.target_dir}] 不能为当前目录或上级目录")
        else:
            # 将目标目录转换为 Path 对象
            self.target_dir = Path(self.target_dir)

        # 创建带时间戳的备份目录
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup_target_dir = self.target_dir / f"{self.source_dir.name}_bak_{timestamp}"

        # 判断目标目录是否存在
        if not backup_target_dir.exists():
            print(f"[INFO] - 创建带时间戳的备份目录: [{backup_target_dir}]")
            backup_target_dir.mkdir(parents=True, exist_ok=True)

        # 开始备份操作
        try:
            for item in self.source_dir.iterdir():
                s = self.source_dir / item.name
                t = backup_target_dir / item.name
                if s.is_dir():
                    # 递归复制目录
                    print(f"[INFO] - 正在备份目录 [{s}] 到 [{t}]")
                    shutil.copytree(s, t, dirs_exist_ok=True)
                else:
                    # 复制文件
                    print(f"[INFO] - 正在备份文件 [{s}] 到 [{t}]")
                    shutil.copy2(s, t)
            print(f"[INFO] - 备份完成，目标目录：[{backup_target_dir}]")
        except Exception as e:
            raise CommandRunningException(f"备份过程发生错误: {e}")


# @ <文件下载> 指令
class DownloadCmd(RetryCmd):
    """
    DownloadCmd 用于从指定 URL 下载文件到目标路径。
    Attributes:
        name:(str): 指令名称

        url:(HttpUrl): 下载文件的 URL
        destination:(Path): 下载文件的目标路径
    """
    name: str = Field("文件下载", description="指令名称")

    url: HttpUrl = Field(..., description="下载文件的 URL")
    destination: Path = Field(..., description="下载文件的目标路径")

    @print_func_time(_DEBUG)
    def run_command(self, **kwargs):
        """ 从 URL(HttpUrl) 下载文件到目标路径 """
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()  # 检查请求是否成功
            with open(self.destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[INFO] - 文件已成功下载到：{self.destination}")
        except Exception as e:
            raise CommandRunningException(f"下载失败: {e}")
