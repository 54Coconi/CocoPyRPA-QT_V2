from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QFont


class JSONHighlighter(QSyntaxHighlighter):
    """
    JSON 数据高亮器
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # 高亮格式
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("blue"))
        self.key_format.setFontWeight(QFont.Bold)  # 使用 QFont.Bold

        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("darkgreen"))

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("darkred"))

        self.boolean_format = QTextCharFormat()
        self.boolean_format.setForeground(QColor("purple"))
        self.boolean_format.setFontWeight(QFont.Bold)  # 使用 QFont.Bold

        self.null_format = QTextCharFormat()
        self.null_format.setForeground(QColor("gray"))
        self.null_format.setFontWeight(QFont.Bold)  # 使用 QFont.Bold

        # 正则表达式
        self.rules = [
            (QRegularExpression(r'"[^"]*"(?=\s*:)'), self.key_format),  # 键
            (QRegularExpression(r':\s*"[^"]*"'), self.value_format),  # 字符串值
            (QRegularExpression(r'\b\d+\.?\d*\b'), self.number_format),  # 数字
            (QRegularExpression(r'\btrue\b|\bfalse\b'), self.boolean_format),  # 布尔值
            (QRegularExpression(r'\bnull\b'), self.null_format),  # null
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                # print(f"Match found: {match.captured()}")
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
