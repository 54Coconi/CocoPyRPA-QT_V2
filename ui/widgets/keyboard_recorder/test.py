from PyQt5.QtWidgets import QApplication

from ui.widgets.keyboard_recorder import Controller

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    controller = Controller(_exit_key="tab + esc")
    controller.start_recording()

    sys.exit(app.exec_())