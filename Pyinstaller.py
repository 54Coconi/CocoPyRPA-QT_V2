"""
打包程序
"""
import os

# 获取 paddleocr 的安装路径
paddleocr_path = os.path.dirname(__import__("paddleocr").__file__)
tools_path = os.path.join(paddleocr_path, "tools")
ppocr_path = os.path.join(paddleocr_path, "ppocr")
print(f"paddleocr 的 tools 路径: {tools_path}")
print(f"paddleocr 的 ppocr 路径: {ppocr_path}")

if __name__ == '__main__':
    from PyInstaller.__main__ import run

    x = input("是否继续打包程序[y/N]?")
    if x.lower() == "y":
        opts = [
            'run.py',
            '-D',  # 生成目录而非单文件
            '-w',  # 不显示控制台窗口（适用于 GUI 程序）
            '--hidden-import=queue',  # 显式包含 queue
            '--hidden-import=numpy',  # 显式包含 NumPy
            '--hidden-import=numpy.core._multiarray_umath',  # 显式包含 numpy.core._multiarray_umath
            '--exclude-module=PySide2',  # 排除 PySide2
            '--exclude-module=PySide6',  # 排除 PySide6
            '--icon=./logo.ico',  # 设置图标

            # 添加 paddleocr 的数据文件
            '--add-data', f'{tools_path}{os.pathsep}tools',  # 包含 tools 目录
            '--add-data', f'{ppocr_path}{os.pathsep}ppocr',  # 包含 ppocr 目录

            '--clean',  # 强制清理缓存
            '-y'   # 覆盖已存在的输出文件
        ]
        run(opts)
    else:
        exit()
