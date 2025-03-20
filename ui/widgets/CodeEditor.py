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

import re
import sys
import jedi
import contextlib

from screeninfo import screeninfo

from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon, QPixmap
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget,
                             QFileDialog, QMessageBox, QPushButton, QTextEdit)

from core.commands.image_commands import *
from core.commands.keyboard_commands import *
from core.commands.mouse_commands import *
from core.commands.script_commands import ExecuteDosCmd
from core.my_apis import CUSTOM_APIS
from core.safe_globals import safe_globals_manager  # 安全全局变量管理器

from ui.widgets.CocoTitleBar import TitleBar, set_button_color, set_button_hover_color
from ui.widgets.code_editor_ui import Ui_CodeEditorUI

from utils.debug import print_command
from utils.opencv_funcs import drawRectangle

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
/*鼠标放在按钮上方*/
QPushButton:hover {
    background-color: rgba(80,118,80,255);
    border:2px outset rgba(36, 36, 36, 0);  /* 凹陷透明边框 */
}
/*鼠标点击按钮*/
QPushButton:pressed {
    background-color: rgba(33,62,33,255);
    border:4px outset rgba(36, 36, 36, 0);  /* 凹陷透明边框 */
}
"""


class PythonLexer(QsciLexerPython):
    """ Python 语法高亮 """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_styles()

    def setup_styles(self):
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
    """ Python 代码编辑器 """
    code_executed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lexer = PythonLexer()  # 创建语法高亮器
        self.api = QsciAPIs(self.lexer)  # 创建API
        self.custom_apis = {}  # 自定义的API
        self.setup_editor()
        self.setup_autocomplete()
        self.init_custom_apis()

        # 连接补全列表激活信号
        self.userListActivated.connect(self.handle_user_list_selection)

        # 添加一个变量来存储当前补全的起始位置
        self.completion_start_position = 0

    def setup_editor(self):
        """配置编辑器基本设置"""
        # 设置编码
        self.setUtf8(True)

        # 设置字体
        font = QFont("Consolas", 12)  # 设置字体
        self.setFont(font)  # 设置编辑器的字体
        self.setMarginsFont(font)  # 设置行号的字体

        # 设置缩进
        self.setIndentationsUseTabs(False)  # 设置是否使用制表符进行缩进
        self.setTabWidth(4)  # 设置制表符的宽度
        self.setIndentationGuides(True)  # 设置缩进指示
        self.setTabIndents(True)  # 设置制表符缩进
        self.setAutoIndent(True)  # 设置自动缩进
        self.setBackspaceUnindents(True)  # 设置退格键缩进

        # 设置自动换行
        self.setWrapMode(QsciScintilla.WrapWord)  # 设置自动换行

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

        # 设置代码折叠
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)  # 设置折叠样式
        self.setFoldMarginColors(QColor("#2D2A2E"), QColor("#2D2A2E"))  # 设置折叠区域的颜色

    def setup_autocomplete(self):
        """配置自动补全功能"""

        self.setAutoCompletionSource(QsciScintilla.AcsAll)  # 设置自动补全源
        self.setAutoCompletionThreshold(1)  # 输入1个字符后触发自动补全
        self.setAutoCompletionCaseSensitivity(False)  # 大小写不敏感
        self.setAutoCompletionReplaceWord(True)  # 补全时替换当前单词
        self.setAutoCompletionUseSingle(QsciScintilla.AcusNever)  # 多个选项时显示列表

        # 启用自动补全列表中的上下键导航
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETAUTOHIDE, False)
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETCHOOSESINGLE, True)

        self.keyPressEvent = self.custom_keyPressEvent

    def init_custom_apis(self):
        """初始化自定义API"""
        self.custom_apis = CUSTOM_APIS

    def add_custom_class(self, class_name, methods=None, attributes=None):
        """添加自定义类的补全信息"""
        self.custom_apis[class_name] = {
            'type': 'class',
            'methods': methods or [],
            'attributes': attributes or []
        }

    def get_completions(self, line_text, position):
        """获取补全列表"""
        print("当前行文本:", line_text)
        try:
            # 获取当前文档内容和光标位置
            text = self.text()
            line_number = self.getCursorPosition()[0] + 1
            column = position

            # 使用jedi获取补全
            script = jedi.Script(text)
            completions = script.complete(line_number, column)

            # 获取当前对象名称
            obj_name = self.extract_class_name(line_text)

            # 添加自定义API补全
            custom_completions = []
            if obj_name in self.custom_apis:
                custom_class = self.custom_apis[obj_name]
                custom_completions.extend(custom_class['methods'])
                custom_completions.extend(custom_class['attributes'])

            # 添加jedi补全
            completion_list = []
            for comp in completions:
                if comp.type == 'function':
                    completion_list.append(f"{comp.name}()")
                else:
                    completion_list.append(comp.name)

            # 合并补全结果
            completion_list.extend(custom_completions)

            return sorted(set(completion_list))

        except Exception as e:
            print(f"补全错误: {str(e)}")
            return []

    def custom_keyPressEvent(self, event):
        """自定义按键事件处理"""
        # Enter 或 Tab 键处理补全
        if self.isListActive():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                # 让 QsciScintilla 处理这个事件，以便完成补全
                QsciScintilla.keyPressEvent(self, event)
                return
            elif event.key() in (Qt.Key_Up, Qt.Key_Down):
                # 允许补全列表上下导航
                self.SendScintilla(QsciScintilla.SCI_LINEUP if event.key() == Qt.Key_Up else QsciScintilla.SCI_LINEDOWN)
                return

        # 显示补全列表(按下 . 或空格)
        if event.key() == Qt.Key_Period or event.key() == Qt.Key_Space:
            QsciScintilla.keyPressEvent(self, event)
            line, pos = self.getCursorPosition()
            line_text = self.text(line)

            # 记录当前输入点号的位置作为补全开始位置
            self.completion_start_position = pos

            completions = self.get_completions(line_text, pos)
            if completions:
                self.showUserList(1, completions)
            return

        # 其余按键默认处理
        QsciScintilla.keyPressEvent(self, event)

        # 自动更新补全列表
        if self.isListActive():
            line, pos = self.getCursorPosition()
            line_text = self.text(line)
            completions = self.get_completions(line_text, pos)
            if completions:
                self.showUserList(1, completions)

    def handle_user_list_selection(self, list_id, selection):
        """处理用户从补全列表中选择项目的事件"""
        if list_id == 1:  # 确保是我们的补全列表
            print(f"选中的补全项: {selection}")
            # 获取当前行和位置
            line, current_pos = self.getCursorPosition()

            # 计算需要保留的文本长度（从补全开始位置到当前位置）
            if current_pos > self.completion_start_position:
                # 如果用户在补全列表显示后输入了字符，我们需要删除这些字符
                self.setSelection(line, self.completion_start_position, line, current_pos)
                self.removeSelectedText()

            # 在补全开始位置插入选中的补全项
            self.insert(selection)

            # 将光标移动到插入文本的末尾
            new_pos = self.completion_start_position + len(selection)
            self.setCursorPosition(line, new_pos)

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


class Stream(QObject):
    """ 标准输出流 """
    newText = pyqtSignal(str)

    def write(self, text):
        """ 重写 write 方法 """
        self.newText.emit(str(text))


class CodeEditor(QWidget, Ui_CodeEditorUI):
    """ 代码编辑器窗口 """

    def __init__(self, parent=None):
        super(CodeEditor, self).__init__(parent)
        self.setupUi(self)
        # 设置标题栏按钮颜色,一定要在初始化标题栏之前
        set_button_color()
        set_button_hover_color()

        self.titleBar = TitleBar(self)  # 创建标题栏
        self.current_file = None  # 初始化当前文件
        self.stdout = Stream()  # 初始化标准输出实例
        self.executor_thread = None  # 初始化执行代码的线程
        self.editor = PythonEditor(self)  # 创建编辑器

        self.setup_ui()
        self.setup_connections()
        self.setup_stdout_redirect()  # 设置标准输出重定向

    def setup_ui(self):
        """设置界面"""
        self.setWindowFlags(Qt.FramelessWindowHint)  # 设置窗口无边框
        self.setGeometry(100, 100, 1000, 700)  # 设置窗口初始尺寸
        # self.setMinimumSize(600, 30)  # 设置窗口最小尺寸
        # 获取屏幕的大小和位置用于居中显示
        monitor = screeninfo.get_monitors()[0]
        x = (monitor.width - self.width()) // 2
        y = (monitor.height - self.height()) // 2
        self.move(x, y)
        # 添加标题栏, 将其添加到垂直布局的顶部
        self.mainVerticalLayout.insertWidget(0, self.titleBar)
        # 设置标题栏图标
        self.titleBar.SetIcon(QPixmap(":/icons/logo2"))
        # 设置标题
        self.titleBar.SetTitle("代码编辑器")
        # 添加代码编辑器
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.widget_codeEdit.setLayout(layout)
        # 设置日志窗口
        self.textEdit_log.setReadOnly(True)  # 设置为只读
        self.textEdit_log.ensureCursorVisible()  # 确保光标可见
        self.textEdit_log.setLineWrapColumnOrWidth(500)  # 设置自动换行
        self.textEdit_log.setLineWrapMode(QTextEdit.WidgetWidth)  # 设置换行模式
        # 设置分裂器的初始大小比例
        self.splitter.setSizes([500, 100])

    def setup_connections(self):
        """ 设置信号和槽 """
        self.toolButton_new.clicked.connect(self.new_file)
        self.toolButton_open.clicked.connect(self.open_file)
        self.toolButton_save.clicked.connect(self.save_file)
        self.toolButton_saveAs.clicked.connect(self.save_file_as)
        self.toolButton_run.clicked.connect(self.run_code)

    def setup_stdout_redirect(self):
        """ 设置标准输出重定向 """
        self.stdout.newText.connect(self.append_log)

    def append_log(self, log: str):
        """添加日志文本"""
        cursor = self.textEdit_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        # 检查 log 是否包含 HTML 标签
        if re.search(r'<[^>]+>', log):
            cursor.insertHtml(log)
        else:
            cursor.insertText(log)
        self.textEdit_log.setTextCursor(cursor)
        self.textEdit_log.ensureCursorVisible()

        # 滚动到底部
        self.textEdit_log.verticalScrollBar().setValue(
            self.textEdit_log.verticalScrollBar().maximum())

    def new_file(self):
        """新建文件"""
        if self.maybe_save():
            self.editor.clear()
            self.current_file = None
            self.setWindowTitle("Python Editor - 新文件")

    def open_file(self):
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

    def save_file(self):
        """保存文件"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self):
        """另存为"""
        fname, _ = QFileDialog.getSaveFileName(
            self, '保存文件', '', 'Python files (*.py);;All files (*.*)')
        if fname:
            self._save_to_file(fname)

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
                self.save_file()  # 保存文件
                return True  # 返回 True 表示可以关闭窗口
            elif msg_box.clickedButton().text() == "取消":
                return False  # 返回 False 表示不关闭窗口
        return True

    def run_code(self):
        """运行代码"""
        code = self.editor.text()
        # 清空日志窗口
        self.textEdit_log.clear()
        # 设置运行按钮不可用
        self.toolButton_run.setDisabled(True)
        # 创建执行代码的线程
        self.executor_thread = CodeExecutorThread(code, self.stdout)
        self.executor_thread.execution_output.connect(self.append_log)
        self.executor_thread.execution_error.connect(self.append_log)
        self.executor_thread.finished.connect(lambda: self.toolButton_run.setDisabled(False))
        self.executor_thread.start()

    def closeEvent(self, event):
        """ 关闭窗口时的事件 """
        if self.maybe_save():
            self.editor.clear()  # 清空编辑器
            self.textEdit_log.clear()  # 清空日志窗口
            self.editor.setModified(False)  # 设置编辑器未修改
            event.accept()
        else:
            event.ignore()

    def showEvent(self, event):
        """ 窗口显示时的事件 """
        self.editor.setFocus()


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
