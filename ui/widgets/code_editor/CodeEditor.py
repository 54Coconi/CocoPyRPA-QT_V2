"""
@author: 54Coconi
@date: 2024-12-12
@version: 1.0.0
@path: ui/widgets/CodeEditor.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    Python 代码编辑器，支持语法高亮、自动补全、标准输出重定向等功能.采用 QScintilla 构建
    API 参考: https://www.riverbankcomputing.com/static/Docs/QScintilla/index.html
"""

import contextlib
import re
import sys
from typing import List

import jedi
from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QEvent
from PyQt5.QtGui import QFont, QColor, QTextCursor, QPixmap, QCursor, QPainter, QPen, QIcon
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget,
                             QFileDialog, QMessageBox, QPushButton, QTextEdit)

from core.commands.image_commands import *
from core.commands.keyboard_commands import *
from core.commands.mouse_commands import *
from core.commands.script_commands import ExecuteDosCmd
from core.my_apis import CUSTOM_APIS
from core.safe_globals import safe_globals_manager  # 安全全局变量管理器
from ui.widgets.CocoTitleBar import TitleBar, set_button_color, set_button_hover_color
from ui.widgets.code_editor.code_editor_ui import Ui_CodeEditorUI
from utils.debug import print_command
from utils.image_process.opencv_funcs import drawRectangle

BUTTON_STYLE = """
QPushButton {
    font-family: "Minecraft YaHei";
    font: 15px;
    color: rgb(255, 255, 255);
    background-color: rgba(70,95,72, 200);
    border: 1px outset rgba(255, 255, 255, 80);
    border-radius: 5px;
    padding: 0px 10px;
    text-align: center center;
}
QPushButton:hover {
    background-color: rgba(80,118,80,255);
    border:2px outset rgba(36, 36, 36, 0);
}
QPushButton:pressed {
    background-color: rgba(33,62,33,255);
    border:4px outset rgba(36, 36, 36, 0);
}
"""

EDGE_HIGHLIGHT_COLOR = QColor(200, 200, 0, 180)  # 边缘高亮颜色
EDGE_HIGHLIGHT_WIDTH = 2  # 高亮线宽


class PythonLexer(QsciLexerPython):
    """Python 语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_styles()

    def _setup_styles(self):
        """ 设置样式 """
        # 设置默认字体
        default_font = QFont('Consolas', 12)
        # 创建粗体字体
        bold_font = QFont('Consolas', 12)
        bold_font.setBold(True)
        # 创建斜体字体
        italic_font = QFont('Consolas', 12)
        italic_font.setItalic(True)

        # 设置各种语法元素的样式
        # 默认样式
        self.setDefaultColor(QColor("#FFFFFF"))  # 设置默认前景
        self.setDefaultPaper(QColor("#272427"))  # 设置默认背景
        self.setDefaultFont(default_font)

        # ---- 注释 ----
        self.setColor(QColor("#008000"), self.Comment)
        self.setColor(QColor("#008000"), self.CommentBlock)
        # 设置注释的字体斜体
        self.setFont(italic_font, self.Comment)
        self.setFont(italic_font, self.CommentBlock)

        # ---- 字符串 ----
        self.setColor(QColor("#808000"), self.DoubleQuotedString)  # 双引号
        self.setColor(QColor("#B7DF88"), self.DoubleQuotedFString)  # 双引号 f 字符串
        self.setColor(QColor("#808000"), self.SingleQuotedString)  # 单引号
        self.setColor(QColor("#B7DF88"), self.SingleQuotedFString)  # 单引号 f 字符串
        self.setColor(QColor("#808000"), self.TripleSingleQuotedString)  # 三个单引号
        self.setColor(QColor("#B7DF88"), self.TripleSingleQuotedFString)  # 三个单引号 f 字符串
        self.setColor(QColor("#808000"), self.TripleDoubleQuotedString)  # 三个双引号
        self.setColor(QColor("#B7DF88"), self.TripleDoubleQuotedFString)  # 三个双引号 f 字符串
        # 设置字符串的字体
        self.setFont(default_font, self.DoubleQuotedString)  # 双引号
        self.setFont(default_font, self.DoubleQuotedFString)  # 双引号 f 字符串
        self.setFont(default_font, self.SingleQuotedString)  # 单引号
        self.setFont(default_font, self.SingleQuotedFString)  # 单引号 f 字符串
        self.setFont(default_font, self.TripleSingleQuotedString)  # 三个单引号
        self.setFont(default_font, self.TripleSingleQuotedFString)  # 三个单引号 f 字符串
        self.setFont(default_font, self.TripleDoubleQuotedString)  # 三个双引号
        self.setFont(default_font, self.TripleDoubleQuotedFString)  # 三个双引号 f 字符串

        # ---- 未闭合的字符串 ----
        self.setColor(QColor("#FF0000"), self.UnclosedString)

        # ---- 数字 ----
        self.setColor(QColor("#8A8AF2"), self.Number)

        # ---- 关键字 ----
        self.setColor(QColor("#ED4A45"), self.Keyword)
        self.setFont(bold_font, self.Keyword)

        # ---- 类名 ----
        self.setColor(QColor("#ED4A45"), self.ClassName)
        self.setFont(bold_font, self.ClassName)

        # ---- 函数名 ----
        self.setColor(QColor("#1a86fd"), self.FunctionMethodName)

        # ---- 操作符 ----
        self.setColor(QColor("#89DDFF"), self.Operator)

        # ---- 标识符 ----
        self.setColor(QColor("#FFFFFF"), self.Identifier)

        # ---- 高亮显示的标识符 ----
        self.setColor(QColor("#FFE567"), self.HighlightedIdentifier)

        # ---- 装饰器 ----
        self.setColor(QColor("#1a86fd"), self.Decorator)

        # ---- 不一致的 ----
        # self.setColor(QColor("#FF0000"), self.Inconsistent)


class PythonEditor(QsciScintilla):
    """Python 代码编辑器（QScintilla），包含语法高亮与自动补全。"""

    code_executed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.lexer = PythonLexer()  # 语法高亮器
        self.api = QsciAPIs(self.lexer)  # 自动补全
        self.custom_apis = CUSTOM_APIS  # 自定义补全 API
        self.api_cache = {}  # 用于缓存自定义 API（避免依赖 QsciAPIs 内部）
        self._setup_editor()
        self._setup_autocomplete()

        # 当用户选择补全项时触发
        self.userListActivated.connect(self._handle_user_list_selection)
        self.completion_start_position = 0

    # ---------------- 内部配置 ----------------
    def _setup_editor(self):
        """配置编辑器外观和行为。"""
        self.setUtf8(True)  # 使用 UTF-8 编码
        font = QFont("Consolas", 12)  # 字体
        self.setFont(font)  # 设置编辑器的字体
        self.setMarginsFont(font)  # 设置行号边栏字体

        # 缩进与自动缩进
        self.setIndentationsUseTabs(False)  # 设置是否使用制表符进行缩进
        self.setTabWidth(4)  # 设置制表符的宽度
        self.setIndentationGuides(True)  # 设置缩进指示
        self.setTabIndents(True)  # 设置制表符缩进
        self.setAutoIndent(True)  # 设置自动缩进
        self.setBackspaceUnindents(True)  # 设置退格键缩进

        # 设置自动换行
        self.setWrapMode(QsciScintilla.WrapWord)

        # 设置光标
        self.setCaretWidth(2)  # 设置光标的宽度
        self.setCaretForegroundColor(QColor("#FFFFFF"))  # 设置光标的颜色
        self.setCaretLineVisible(True)  # 设置光标所在行是否可见

        # 设置选中文本的颜色
        self.setSelectionBackgroundColor(QColor("#ADD6FF"))  # 设置选中文本的背景
        self.setSelectionForegroundColor(QColor("#000000"))  # 设置选中文本的前景

        # 设置括号匹配
        self.setBraceMatching(QsciScintilla.StrictBraceMatch)  # 设置括号匹配模式
        self.setMatchedBraceForegroundColor(QColor("#D5D860"))  # 设置匹配括号的前景
        self.setMatchedBraceBackgroundColor(QColor("#4B4B4B"))  # 设置匹配括号的背景

        # 设置Python语法高亮
        self.setLexer(self.lexer)

        # 设置当前行高亮
        self.setCaretLineVisible(True)  # 显示当前行高亮
        self.setCaretLineBackgroundColor(QColor("#3B3539"))  # 设置当前行高亮的颜色

        # 设置行号区域
        self.setMarginType(0, QsciScintilla.NumberMargin)  # 设置行号区域
        self.setMarginWidth(0, "000")  # 设置行号区域的宽度
        self.setMarginsForegroundColor(QColor("#777777"))  # 设置行号区域的前景
        self.setMarginsBackgroundColor(QColor("#2D2A2E"))  # 设置行号区域的背景

    def _setup_autocomplete(self) -> None:
        """配置自动补全参数。"""
        self.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.setAutoCompletionThreshold(1)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)
        self.setAutoCompletionUseSingle(QsciScintilla.AcusNever)

        # 自动隐藏/选择策略
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETAUTOHIDE, False)
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETCHOOSESINGLE, True)

        # 初始化自定义 API 补全
        self._init_custom_apis()

        # 用自定义的 keyPressEvent 触发智能补全
        self.keyPressEvent = self._custom_key_press_event  # type: ignore

    # ---------------- 自动补全 ----------------
    def _init_custom_apis(self):
        """初始化自定义 API 补全"""
        self.api_cache = {}  # {class_name: {"methods": [...], "attributes": [...]}}

        for class_name, meta in self.custom_apis.items():
            self.api.add(class_name)  # 只添加类名到 QsciAPIs
            self.api_cache[class_name] = {
                "methods": meta.get("methods", []),
                "attributes": meta.get("attributes", [])
            }

        self.api.prepare()

    @staticmethod
    def _compute_word_start(text: str, caret_col: int) -> int:
        """计算“当前词”的起始列，仅将 [A-Za-z0-9_] 视为词的一部分。

        Args:
            text: 当前行文本。
            caret_col: 光标所在列（0-based）。

        Returns:
            词起始列（0-based）。若光标前不是单词字符，则返回 caret_col（表示空前缀）。
        """
        i = max(0, min(caret_col, len(text)))
        j = i - 1
        while j >= 0 and (text[j].isalnum() or text[j] == "_"):
            j -= 1
        return j + 1  # 跳回到第一位非词字符的后一个位置

    def _custom_key_press_event(self, event) -> None:
        """自定义键盘事件：在输入时实时触发补全。"""
        if self.isListActive():
            # 关键：列表激活时拦截 Enter/Return/Tab，避免基类插入换行而破坏选择处理
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                # 让 QsciScintilla 处理这个事件，以便完成补全
                QsciScintilla.keyPressEvent(self, event)
                return  # 交由 QScintilla 的用户列表自身处理 -> 触发 userListActivated
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self.SendScintilla(
                    QsciScintilla.SCI_LINEUP
                    if event.key() == Qt.Key_Up
                    else QsciScintilla.SCI_LINEDOWN
                )
                return

        # 先让编辑器处理（确保文本已更新，再基于最新上下文做推断）
        QsciScintilla.keyPressEvent(self, event)

        # 触发条件：字母/数字/下划线/点号（属性补全）
        ch = event.text()
        if not ch:
            return
        trigger = (ch.isalnum() or ch in "_.")
        if not trigger:
            return

        # 获取最新光标位置与行文本
        line, pos = self.getCursorPosition()
        line_text = self.text(line)

        # 仅替换“当前词”的前缀，避免清空整行：
        #   - 若是普通单词字符：向左回溯到词首
        #   - 若是点号触发（属性补全），通常词前缀为空 => 起始列为当前位置
        if ch == ".":
            print("按下点号，触发属性补全")
            self.completion_start_position = pos
        else:
            self.completion_start_position = self._compute_word_start(line_text, pos)

        # 计算并展示补全
        comps = self._get_completions(line_text, pos)
        if comps:
            self.showUserList(1, comps)

    def _get_completions(self, line_text: str, position: int):
        """获取 Jedi + 自定义 API 的补全结果"""
        completions = set()

        # ===== 1) Jedi 补全 =====
        try:
            text = self.text()
            line_number = self.getCursorPosition()[0] + 1
            script = jedi.Script(text)
            jedi_completions = script.complete(line_number, position)
            for comp in jedi_completions:
                completions.add(f"{comp.name}()" if comp.type == "function" else comp.name)
        except Exception:
            pass

        # ===== 2) 自定义 API 补全 =====
        prefix = line_text[:position].split()[-1] if line_text.strip() else ""
        print("before prefix:", prefix)
        # 情况1：如果是 类名. / 类名(). → 返回该类的方法和属性
        if "." in prefix:
            for part in prefix.split(".")[::-1]:
                if not part:
                    continue
                prefix = part
                break
            print("after prefix:", prefix)
            if prefix in self.api_cache:
                for method in self.api_cache[prefix]["methods"]:
                    completions.add(method)  # 只返回 execute() 而不是 MouseClickCmd.execute()
                for attr in self.api_cache[prefix]["attributes"]:
                    completions.add(attr)
            elif prefix[:-2] in self.api_cache:
                prefix = prefix[:-2]  # 去掉最后的 "()"
                for method in self.api_cache[prefix]["methods"]:
                    completions.add(method)
                for attr in self.api_cache[prefix]["attributes"]:
                    completions.add(attr)
        else:
            # 否则 → 返回类名列表
            for class_name in self.api_cache:
                if class_name.startswith(prefix):
                    completions.add(class_name)

        # 情况2：如果是 类名(key1, key2). → 返回该类的方法和属性
        class_name = self.extract_class_name(line_text)
        last_part = [part for part in line_text.strip().split(".") if part][-1]
        print("class_name:", class_name)
        print("last_part:", last_part)
        if class_name and class_name in last_part and class_name in self.api_cache:
            for method in self.api_cache[class_name]["methods"]:
                completions.add(method)
            for attr in self.api_cache[class_name]["attributes"]:
                completions.add(attr)

        return sorted(completions)

    def get_completions(self, line_text: str, position: int) -> List[str]:
        """使用 Jedi 获取智能补全列表。

        Args:
            line_text: 当前行文本（用于上下文分析，可不强依赖）
            position: 光标在当前行的位置（1-based 在 Script 中会换算）

        Returns:
            去重排序后的补全候选列表。
        """
        try:
            # 获取当前文档内容和光标位置
            text = self.text()
            line_number = self.getCursorPosition()[0] + 1

            # 使用jedi获取补全
            script = jedi.Script(text)
            completions = script.complete(line_number, position)
            # 处理函数补全
            completion_list: List[str] = []
            for comp in completions:
                if comp.type == 'function':
                    completion_list.append(f"{comp.name}()")
                else:
                    completion_list.append(comp.name)

            # 获取当前对象名称
            obj_name = self.extract_class_name(line_text)
            # 添加自定义API补全
            custom_completions = []
            if obj_name in self.custom_apis:
                custom_completions.extend([obj_name])
                custom_class = self.custom_apis[obj_name]
                custom_completions.extend(custom_class['methods'])
                custom_completions.extend(custom_class['attributes'])

            # 合并补全结果
            completion_list.extend(custom_completions)

            return sorted(set(completion_list))
        except Exception:
            return []

    @staticmethod
    def extract_class_name(code_line: str):
        """
        从代码行中提取类名
        适配变量赋值和直接实例化类的方式

        :param code_line: 包含类实例化的代码行
        :return: 提取到的类名，或者 None 如果没有匹配到
        """
        code_line = code_line.strip()  # 去除空格

        # 匹配类名及其后的开括号 "("
        match = re.search(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', code_line)
        if not match:
            return None  # 如果未匹配到，返回 None

        class_name = match.group(1)  # 提取类名
        start_idx = match.start(1)  # 类名的起始索引
        open_paren_idx = match.end()  # 开括号 "(" 的索引

        # 检查括号平衡
        stack = []
        for i in range(open_paren_idx, len(code_line)):
            char = code_line[i]

            if char == '(':
                stack.append('(')
            elif char == ')':
                if stack:
                    stack.pop()
                else:
                    # 如果找到没有匹配的右括号，结束解析
                    break

            # 如果括号平衡栈为空，说明解析完成
            if not stack:
                return class_name

        return None

    def _handle_user_list_selection(self, list_id: int, selection: str) -> None:
        """处理用户选择的补全项：仅替换当前词前缀，不影响其余文本。"""
        if list_id != 1:
            return
        # 当前光标列
        line, current_pos = self.getCursorPosition()

        # 仅删除“当前词前缀”，不再从列 0 开始删除
        start_col = max(0, min(self.completion_start_position, current_pos))
        if current_pos > start_col:
            self.setSelection(line, start_col, line, current_pos)
            self.removeSelectedText()

        # 插入所选补全项，并将光标放到末尾
        self.insert(selection)
        self.setCursorPosition(line, start_col + len(selection))


class Stream(QObject):
    """标准输出流，重定向 print 输出到文本框。"""

    newText = pyqtSignal(str)

    def write(self, text: str) -> None:
        """写入并发信号"""
        self.newText.emit(str(text))


class CodeEditor(QWidget, Ui_CodeEditorUI):
    """代码编辑器窗口，支持无边框拖动、缩放和边缘高亮提示。"""

    MARGIN = 6  # 边缘检测阈值（像素）
    MIN_WIDTH = 600  # 设置窗口最小宽度
    MIN_HEIGHT = 400  # 设置窗口最小高度

    def __init__(self, parent=None) -> None:
        # 强制顶级窗口，确保不受父窗口约束
        super().__init__(None)  # 不接收外部 parent，避免被限制在父窗口区域
        self.setupUi(self)
        set_button_color()
        set_button_hover_color()

        self.titleBar = TitleBar(self)
        self.current_file: Optional[str] = None
        self.stdout = Stream()
        self.editor = PythonEditor(self)

        # 拖拽与缩放状态
        self.resizing = False
        self.drag_pos = None
        self.resize_direction: Optional[str] = None
        self.hover_resize_direction: Optional[str] = None  # 当前悬停边缘方向

        self._setup_ui()
        self._setup_connections()
        self._setup_stdout_redirect()

    # ---------------- UI ----------------
    def _setup_ui(self) -> None:
        """配置窗口 UI"""
        self.setWindowTitle("Python 代码编辑器")
        self.setWindowIcon(QIcon(":/icons/logo2"))

        # 无边框 + 标准窗口按钮（支持最小化/最大化）
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
        )

        # 允许悬停事件（HoverMove）
        self.setAttribute(Qt.WA_Hover, True)

        # 追踪鼠标（无需按键按下即可触发 mouseMove）
        self.setMouseTracking(True)

        # 子组件也开启追踪，确保产生 MouseMove 事件
        self.editor.setMouseTracking(True)
        self.textEdit_log.setMouseTracking(True)

        # 应用级事件过滤器，捕获所有组件的鼠标事件
        QApplication.instance().installEventFilter(self)

        # 布局：把自定义标题栏塞到顶部
        self.mainVerticalLayout.insertWidget(0, self.titleBar)
        self.titleBar.SetIcon(QPixmap(":/icons/logo2"))
        self.titleBar.SetTitle("代码编辑器")

        # 代码编辑器放入占位面板
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.widget_codeEdit.setLayout(layout)

        # 日志窗口配置
        self.textEdit_log.setReadOnly(True)
        self.textEdit_log.ensureCursorVisible()
        self.textEdit_log.setLineWrapMode(QTextEdit.WidgetWidth)
        self.splitter.setSizes([500, 120])

        # 初始尺寸与居中
        self.resize(1000, 700)
        screen_geo = QApplication.desktop().availableGeometry(self)
        self.move(
            screen_geo.center().x() - self.width() // 2,
            screen_geo.center().y() - self.height() // 2,
        )

    def _setup_connections(self) -> None:
        """绑定工具按钮事件。"""
        self.toolButton_new.clicked.connect(self._new_file)
        self.toolButton_open.clicked.connect(self._open_file)
        self.toolButton_save.clicked.connect(self._save_file)
        self.toolButton_saveAs.clicked.connect(self._save_file_as)
        self.toolButton_run.clicked.connect(self._run_code)

    def _setup_stdout_redirect(self) -> None:
        """重定向标准输出到日志窗口。"""
        self.stdout.newText.connect(self._append_log)
        sys.stdout = self.stdout  # 可根据需要改为上下文管理器

    # ---------------- 文件操作 ----------------
    # 按钮 - 【新建】
    def _new_file(self) -> None:
        """新建文件"""
        if self.maybe_save():
            self.editor.clear()
            self.current_file = None
            self.setWindowTitle("Python Editor - 新文件")

    # 按钮 - 【打开】
    def _open_file(self) -> None:
        """打开文件"""
        if self.maybe_save():
            fname, _ = QFileDialog.getOpenFileName(
                self, '打开文件', '', 'Python files (*.py);;All files (*.*)')
            if fname:
                try:
                    with open(fname, 'r', encoding='utf-8') as f:
                        text = f.read()
                    self.editor.setText(text)
                    self.current_file = fname
                    self.setWindowTitle(f"Python Editor - {os.path.basename(fname)}")
                except Exception as e:
                    QMessageBox.warning(self, "打开文件错误", str(e))

    # 按钮 - 【保存】
    def _save_file(self) -> None:
        """保存文件"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._save_file_as()

    def _save_to_file(self, fname):
        """保存到指定文件"""
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.editor.text())
            self.current_file = fname
            self.setWindowTitle(f"Python Editor - {os.path.basename(fname)}")
            self.editor.setModified(False)  # 设置编辑器未修改
            QMessageBox.information(self, "保存文件", "文件已保存成功")
        except Exception as e:
            QMessageBox.warning(self, "保存文件错误", str(e))

    # 按钮 - 【另存为】
    def _save_file_as(self) -> None:
        """另存为"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Python File", "", "Python Files (*.py);;All Files (*)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.text())
        self.current_file = path

    # 按钮 - 【运行】
    def _run_code(self) -> None:
        """运行当前代码（示例：简单重定向到日志）。"""
        code = self.editor.text()
        # 清空日志窗口
        self.textEdit_log.clear()
        # 设置运行按钮不可用
        self.toolButton_run.setDisabled(True)
        # 创建执行代码的线程
        self.executor_thread = CodeExecutorThread(code, self.stdout)
        self.executor_thread.execution_output.connect(self._append_log)
        self.executor_thread.execution_error.connect(self._append_log)
        self.executor_thread.finished.connect(lambda: self.toolButton_run.setDisabled(False))
        self.executor_thread.start()

    def maybe_save(self):
        """如果有未保存的修改，提示保存"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("提示")
        msg_box.setText("当前文件已修改，是否保存当前文件？")
        # 创建按钮
        save_button = QPushButton("保存")
        no_save_button = QPushButton("不保存")
        cancel_button = QPushButton("取消")
        # 设置按钮样式
        save_button.setStyleSheet(BUTTON_STYLE)
        save_button.setMinimumHeight(30)
        no_save_button.setStyleSheet(BUTTON_STYLE)
        no_save_button.setMinimumHeight(30)
        no_save_button.setMinimumWidth(80)
        cancel_button.setStyleSheet(BUTTON_STYLE)
        cancel_button.setMinimumHeight(30)
        # 添加按钮到消息框
        msg_box.addButton(save_button, QMessageBox.YesRole)
        msg_box.addButton(no_save_button, QMessageBox.NoRole)
        msg_box.addButton(cancel_button, QMessageBox.RejectRole)
        msg_box.setDefaultButton(save_button)
        if self.editor.isModified() and self.editor.text() != '':
            msg_box.exec_()
            if msg_box.clickedButton().text() == "保存":
                self._save_file()  # 保存文件
                return True  # 返回 True 表示可以关闭窗口
            elif msg_box.clickedButton().text() == "取消":
                return False  # 返回 False 表示不关闭窗口
        return True

    def _append_log(self, log: str) -> None:
        """输出日志到日志窗口。"""
        cursor = self.textEdit_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        if re.search(r"<[^>]+>", log):
            cursor.insertHtml(log)
        else:
            cursor.insertText(log)
        self.textEdit_log.setTextCursor(cursor)
        self.textEdit_log.ensureCursorVisible()
        self.textEdit_log.verticalScrollBar().setValue(
            self.textEdit_log.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """ 关闭窗口时的事件 """
        if self.maybe_save():
            self.editor.clear()  # 清空编辑器
            self.textEdit_log.clear()  # 清空日志窗口
            self.editor.setModified(False)  # 设置编辑器未修改
            # 恢复标准输出
            sys.stdout = sys.__stdout__
            event.accept()
        else:
            event.ignore()

    def showEvent(self, event):
        """ 窗口显示时的事件 """
        self.editor.setFocus()

    # =========================================================
    # 无边框拖动与缩放（含边缘高亮）
    # =========================================================
    def mousePressEvent(self, event):
        """鼠标按下：记录拖拽起点并判定是否进入缩放模式。"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos()
            self.resize_direction = self._get_resize_direction(event.pos())
            self.resizing = self.resize_direction is not None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动：若在缩放则调整几何；否则仅更新光标与高亮"""
        if self.resizing and self.drag_pos:
            # 正在缩放：根据方向调整窗口矩形
            diff = event.globalPos() - self.drag_pos
            rect = self.geometry()

            if "left" in self.resize_direction:
                rect.setLeft(rect.left() + diff.x())
            if "right" in self.resize_direction:
                rect.setRight(rect.right() + diff.x())
            if "top" in self.resize_direction:
                rect.setTop(rect.top() + diff.y())
            if "bottom" in self.resize_direction:
                rect.setBottom(rect.bottom() + diff.y())

            # 最小尺寸限制
            limited = False
            if rect.width() < self.MIN_WIDTH:
                if "left" in self.resize_direction:
                    # 固定右边
                    rect.setLeft(rect.right() - self.MIN_WIDTH)
                elif "right" in self.resize_direction:
                    # 固定左边
                    rect.setRight(rect.left() + self.MIN_WIDTH)
                else:
                    rect.setWidth(self.MIN_WIDTH)
                limited = True
            if rect.height() < self.MIN_HEIGHT:
                if "top" in self.resize_direction:
                    # 固定下边
                    rect.setTop(rect.bottom() - self.MIN_HEIGHT)
                elif "bottom" in self.resize_direction:
                    # 固定上边
                    rect.setBottom(rect.top() + self.MIN_HEIGHT)
                else:
                    rect.setHeight(self.MIN_HEIGHT)
                limited = True

            # 如果达到最小尺寸 → 停止缩放
            if limited:
                self.resizing = False

            self.setGeometry(rect)
            self.drag_pos = event.globalPos()
        else:
            # 非缩放：基于当前局部坐标判定高亮
            direction = self._get_resize_direction(event.pos())
            if direction != self.hover_resize_direction:
                self.hover_resize_direction = direction
                self.update()

            # 设置指针形状
            self._apply_cursor_by_direction(direction)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：结束缩放并根据位置清理高亮"""
        self.resizing = False
        # 释放后若不在边缘，清除高亮
        direction = self._get_resize_direction(event.pos())
        if direction is None and self.hover_resize_direction is not None:
            self.hover_resize_direction = None
            self.update()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """鼠标离开窗口区域：清除高亮（兜底）"""
        if self.hover_resize_direction is not None:
            self.hover_resize_direction = None
            self.update()
        super().leaveEvent(event)

    # ---------------- 应用级事件过滤器 ----------------
    def eventFilter(self, obj, event) -> bool:
        """应用级事件过滤：确保在子组件上移动时也能刷新/清除高亮。

        关键点：
        - 当鼠标在 `editor` 或 `textEdit_log` 上移动时，父窗口不会自动收到 mouseMove。
        - 这里统一捕获全应用 MouseMove / HoverMove / Leave，并用**全局光标**计算位置。
        """
        et = event.type()
        if et in (QEvent.MouseMove, QEvent.HoverMove):
            self._update_hover_from_global()  # 基于全局光标刷新边缘高亮
        elif et == QEvent.Leave:
            # 某些子控件的 Leave 不会引发父组件的 leaveEvent，这里兜底清理
            # 但只在鼠标不在窗口内部时才清理，避免误闪烁
            self._update_hover_from_global()
        return super().eventFilter(obj, event)

    def _update_hover_from_global(self):
        """从**全局光标位置**更新边缘高亮状态。

        逻辑：
        1) 将 QCursor 全局坐标映射到当前窗口坐标。
        2) 若不在窗口矩形内 => 清除高亮；
        3) 若在窗口内 => 计算边缘方向并根据变化触发重绘。
        """
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        if not self.rect().contains(local_pos):
            if self.hover_resize_direction is not None:
                self.hover_resize_direction = None
                self.update()
            return

        direction = self._get_resize_direction(local_pos)
        if direction != self.hover_resize_direction:
            self.hover_resize_direction = direction
            self.update()

        # 根据方向设置光标形状（一致性）
        self._apply_cursor_by_direction(direction)

    def _apply_cursor_by_direction(self, direction: Optional[str]) -> None:
        """按方向设置鼠标指针形状。"""
        if direction in ("left", "right"):
            self.setCursor(Qt.SizeHorCursor)
        elif direction in ("top", "bottom"):
            self.setCursor(Qt.SizeVerCursor)
        elif direction in ("top-left", "bottom-right"):
            self.setCursor(Qt.SizeFDiagCursor)
        elif direction in ("top-right", "bottom-left"):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _get_resize_direction(self, pos) -> Optional[str]:
        """根据局部坐标判断是否靠近窗口边缘并返回方向。"""
        r = self.rect()
        margin = self.MARGIN

        left = pos.x() <= r.left() + margin
        right = pos.x() >= r.right() - margin
        top = pos.y() <= r.top() + margin
        bottom = pos.y() >= r.bottom() - margin

        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    def paintEvent(self, event) -> None:
        """绘制边缘高亮线条。"""
        super().paintEvent(event)
        if not self.hover_resize_direction:
            return

        painter = QPainter(self)
        pen = QPen(EDGE_HIGHLIGHT_COLOR, EDGE_HIGHLIGHT_WIDTH)
        painter.setPen(pen)
        rect = self.rect()

        d = self.hover_resize_direction
        if d in ("left", "right"):
            x = rect.left() if d == "left" else rect.right() - EDGE_HIGHLIGHT_WIDTH
            painter.drawLine(x, rect.top(), x, rect.bottom())
        elif d in ("top", "bottom"):
            y = rect.top() if d == "top" else rect.bottom() - EDGE_HIGHLIGHT_WIDTH
            painter.drawLine(rect.left(), y, rect.right(), y)
        elif d == "top-left":
            painter.drawLine(rect.left(), rect.top(), rect.left() + 20, rect.top())
            painter.drawLine(rect.left(), rect.top(), rect.left(), rect.top() + 20)
        elif d == "top-right":
            painter.drawLine(rect.right() - 20, rect.top(), rect.right(), rect.top())
            painter.drawLine(rect.right() - EDGE_HIGHLIGHT_WIDTH, rect.top(),
                             rect.right() - EDGE_HIGHLIGHT_WIDTH, rect.top() + 20)
        elif d == "bottom-left":
            painter.drawLine(rect.left(), rect.bottom() - EDGE_HIGHLIGHT_WIDTH,
                             rect.left() + 20, rect.bottom() - EDGE_HIGHLIGHT_WIDTH)
            painter.drawLine(rect.left(), rect.bottom() - 20, rect.left(), rect.bottom())
        elif d == "bottom-right":
            painter.drawLine(rect.right() - 20, rect.bottom() - EDGE_HIGHLIGHT_WIDTH,
                             rect.right(), rect.bottom() - EDGE_HIGHLIGHT_WIDTH)
            painter.drawLine(rect.right() - EDGE_HIGHLIGHT_WIDTH, rect.bottom() - 20,
                             rect.right() - EDGE_HIGHLIGHT_WIDTH, rect.bottom())


class CodeExecutorThread(QThread):
    """执行代码的线程"""
    execution_output = pyqtSignal(str)
    execution_error = pyqtSignal(str)

    def __init__(self, code, stdout, parent=None):
        super().__init__(parent)
        self.code = code
        self.stdout = stdout

        # 注册自动化指令类
        self._register_command_classes()
        # 注册自定义类
        self._register_custom_classes()
        # 注册函数
        self._register_functions()

    @staticmethod
    def _register_command_classes():
        """ 注册所有可用的自动化指令类 """
        command_classes = {
            # 鼠标操作
            "MousePressReleaseCmd": MousePressReleaseCmd,
            "MouseClickCmd": MouseClickCmd,
            "MouseMoveToCmd": MouseMoveToCmd,
            "MouseMoveRelCmd": MouseMoveRelCmd,
            "MouseDragToCmd": MouseDragToCmd,
            "MouseDragRelCmd": MouseDragRelCmd,
            "MouseScrollCmd": MouseScrollCmd,
            "MouseScrollHCmd": MouseScrollHCmd,
            # 键盘操作
            "KeyPressCmd": KeyPressCmd,
            "KeyReleaseCmd": KeyReleaseCmd,
            "KeyTapCmd": KeyTapCmd,
            "HotKeyCmd": HotKeyCmd,
            "KeyTypeTextCmd": KeyTypeTextCmd,
            # 图像操作
            "ImageMatchCmd": ImageMatchCmd,
            "ImageClickCmd": ImageClickCmd,
            "ImageOcrCmd": ImageOcrCmd,
            "ImageOcrClickCmd": ImageOcrClickCmd,
            # 执行Dos命令
            "ExecuteDosCmd": ExecuteDosCmd,
        }
        for name, cmd_class in command_classes.items():
            safe_globals_manager.register_command(name, cmd_class)

    @staticmethod
    def _register_custom_classes():
        """ 注册自定义类 """
        custom_classes = {
            # 图片识别工具类
            "OCRTool": OCRTool
        }
        for name, custom_class in custom_classes.items():
            safe_globals_manager.register_custom_class(name, custom_class)

    @staticmethod
    def _register_functions():
        """ 注册函数 """
        custom_functions = {
            # debug 函数
            "print_func_time": print_func_time,
            "print_command": print_command,
            "drawRectangle": drawRectangle
        }
        for name, func in custom_functions.items():
            safe_globals_manager.register_custom_function(name, func)

    def run(self, **kwargs):
        """运行代码"""
        self.execution_output.emit(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行代码<br>")
        try:
            # 获取执行环境
            additional_globals = kwargs.get("additional_globals", {})
            safe_globals = safe_globals_manager.create_restricted_exec_env(additional_globals)
            local_vars = {}  # 用于存储局部变量
            # print("执行环境:", safe_globals)
            # 使用重定向的标准输出
            with contextlib.redirect_stdout(self.stdout):
                exec(self.code, safe_globals, local_vars)
        except Exception as e:
            formatted_message = f"<p align='left'><font color='#FF0000' size='3'>" \
                                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] - {str(e)}" \
                                f"</font></p> <br>"
            self.execution_error.emit(formatted_message)


# 测试
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CodeEditor()
    window.show()
    sys.exit(app.exec_())
