import threading
from pathlib import Path
from typing import List

from PyQt5 import QtCore, QtWidgets

import conan_app_launcher as this
from conan_app_launcher.base import Logger
from conan_app_launcher.components import ConanWorker, parse_config_file
from conan_app_launcher.settings import LAST_CONFIG_FILE, Settings
from conan_app_launcher.ui.layout_entries import AppUiEntry, TabUiGrid
from conan_app_launcher.ui.qt.app_grid import Ui_MainWindow


class MainUi(QtWidgets.QMainWindow):
    """ Instantiates MainWindow and holds all UI objects """
    conan_info_updated = QtCore.pyqtSignal()
    new_message_logged = QtCore.pyqtSignal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._tab_info: List[TabUiGrid] = []
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        # connect logger to console widget to log possible errors at init
        Logger.init_qt_logger(self)
        self._ui.console.setFontPointSize(10)

        self._about_dialog = AboutDialog(self)
        self._ui.menu_about_action.triggered.connect(self._about_dialog.show)

        # TODO set last Path on dir
        self._ui.menu_open_config_file_action.triggered.connect(self.open_config_file_dialog)
        self.conan_info_updated.connect(self.update_layout)
        self.new_message_logged.connect(self.write_log)

        self.init_gui()

    def closeEvent(self, event):
        """ Remove qt logger, so it doesn't log into a non existant object """
        self.new_message_logged.disconnect(self.write_log)
        Logger.remove_qt_logger()
        super().closeEvent(event)

    @property
    def ui(self):
        """ Contains all gui objects defined in Qt .ui file. Subclasses need access to this. """
        return self._ui

    def open_config_file_dialog(self):
        """" Open File Dialog and load config file """
        dialog_path = Path.home()
        config_file_path = Path(self._settings.get(LAST_CONFIG_FILE))
        if config_file_path.exists():
            dialog_path = config_file_path.parent
        dialog = QtWidgets.QFileDialog(caption="Select JSON Config File",
                                       directory=str(dialog_path), filter="JSON files (*.json)")
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._settings.set(LAST_CONFIG_FILE, dialog.selectedFiles()[0])
            self._re_init()

    def create_layout(self):
        tab = None
        for tab_info in self._tab_info:
            # TODO: need to save object locally, otherwise it can be destroyed in the underlying C++ layer
            self._tab = TabUiGrid(tab_info.name)
            row = 0  # 3
            column = 0  # 4
            for app_info in tab_info.get_app_entries():

                # add in order of occurence
                app = AppUiEntry(tab.tab_scroll_area_widgets, app_info)
                tab.apps.append(app)
                tab.tab_grid_layout.addLayout(app, row, column, 1, 1)
                column += 1
                if column == 4:
                    column = 0
                    row += 1
            self._ui.tabs.addTab(tab, tab_info.name)

    def update_layout(self):
        # ungrey entries and set correct icon and add hover text
        for tab in self._ui.tabs.findChildren(TabUiGrid):
            for app in tab.apps:
                app.update_entry()

    def init_gui(self):
        # reset gui and objects
        while self._ui.tabs.count() > 0:
            self._ui.tabs.removeTab(0)
        config_file_path = Path(self._settings.get(LAST_CONFIG_FILE))
        if config_file_path.is_file():
            self._tab_info = parse_config_file(config_file_path)
        this.conan_worker = ConanWorker(self._tab_info, self.conan_info_updated)
        self.create_layout()

    def _re_init(self):
        this.conan_worker.finish_working(3)
        self.init_gui()

    def write_log(self, text):
        """ Write the text signalled by the logger """
        self._ui.console.append(text)


class AboutDialog(QtWidgets.QDialog):
    """ Defines Help->About Dialog """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setModal(True)
        ok_button = QtWidgets.QDialogButtonBox.Ok
        self._text = QtWidgets.QLabel(self)
        self._text.setText("Conan App Launcher\n" + this.__version__ + "\n" +
                           "Copyright (C), 2020, Péter Gosztolya")

        self._button_box = QtWidgets.QDialogButtonBox(ok_button)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self._text)
        self.layout.addWidget(self._button_box)
        self.setLayout(self.layout)
