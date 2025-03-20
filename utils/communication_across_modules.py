from pubsub import pub


def sent_exception_to_logWidget(msg: str):
    """ 将异常信息发送到日志窗口 """
    new_msg = "<p align='left'><font color='#FF585D' size='3'>" + msg + "</font></p>"
    pub.sendMessage('command_running_exception', message=new_msg)


def sent_message_to_logWidget(msg: str):
    """ 将日志信息发送到日志窗口 """
    new_msg = "<p align='left'><font color='#66ADA7' size='3'>" + msg + "</font></p>"
    pub.sendMessage('command_running_progress', message=new_msg)
