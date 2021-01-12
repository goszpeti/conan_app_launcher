"""
Entry module of Conan App Launcher
Sets up cmd arguments, config file and starts the gui
"""
import os
import sys
import traceback
import platform
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

import conan_app_launcher as this
from conan_app_launcher.settings import Settings
from conan_app_launcher.base import Logger
from conan_app_launcher.ui.main_window import MainUi

try:
    # this is a workaround for windows, so that on the taskbar the
    # correct icon will be shown (and not the default python icon)
    from PyQt5.QtWinExtras import QtWin
    MY_APP_ID = 'ConanAppLauncher.' + this.__version__
    QtWin.setCurrentProcessExplicitAppUserModelID(MY_APP_ID)
except ImportError:
    pass

# define Qt so we can use it like the namespace in C++
Qt = QtCore.Qt


def main():
    """
    Start the Qt application
    """

    if platform.system() == "Darwin":
        print("Mac OS is currently not supported.")
        sys.exit(1)
    # Redirect stdout and stderr for usage with pythonw as executor -
    # otherwise conan will not work
    if sys.executable.endswith("pythonw.exe"):
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.path.join(os.getenv("TEMP"),
                                       "stderr-" + this.PROG_NAME), "w")
    # init logger first
    this.base_path = Path(__file__).absolute().parent
    this.asset_path: Path = this.base_path / "assets"
    logger = Logger()

    # apply Qt attributes (only at init possible)
    QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # start Qt app and ui
    if not this.qt_app:
        this.qt_app = QtWidgets.QApplication([])
    icon = QtGui.QIcon(str(this.asset_path / "icons" / "icon.ico"))

    # font_file = r"C:\sw-dev\159687-interface-icon-assets\font\Flaticon.ttf"
    # font_id = QtGui.QFontDatabase.addApplicationFont(str(font_file))
    # if font_id != -1:
    #     font_db = QtGui.QFontDatabase()
    #     font_styles = font_db.styles("Flaticon")
    #     font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
    #     for font_family in font_families:
    #         font = font_db.font(font_family, font_styles[0], 10)
    #     this.qt_app.setFont(font)

    settings_file_path = Path.home() / ".cal_config"
    settings = Settings(ini_file=settings_file_path)

    this.main_window = MainUi(settings)
    this.main_window.init_gui()
    this.main_window.setWindowIcon(icon)
    this.main_window.show()

    try:
        this.qt_app.exec_()
    except:  # pylint:disable=bare-except
        trace_back = traceback.format_exc()
        logger.error(f"Application crashed: \n{trace_back}")
    finally:
        if this.conan_worker:  # cancel conan worker tasks on exit
            this.conan_worker.finish_working()


if __name__ == "__main__":
    main()
