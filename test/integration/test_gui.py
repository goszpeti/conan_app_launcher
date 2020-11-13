"""
This test starts the application.
It is called z_integration, so that it launches last.
"""

import os
import sys
import platform
import tempfile
import time
from pathlib import Path
from subprocess import check_output

import conan_app_launcher as app
from conan_app_launcher.components import AppEntry
from conan_app_launcher.base import Logger
from conan_app_launcher.settings import *
from conan_app_launcher.ui import main_ui
from conan_app_launcher.ui.layout_entries import AppUiEntry, TabUiGrid
from PyQt5 import QtCore, QtWidgets


def testSelectConfigFileDialog(base_fixture, qtbot, mocker):
    logger = Logger()  # init logger
    temp_dir = tempfile.gettempdir()
    temp_ini_path = os.path.join(temp_dir, "config.ini")

    settings = Settings(ini_file=Path(temp_ini_path))

    main_gui = main_ui.MainUi(settings)
    main_gui.show()
    qtbot.addWidget(main_gui)
    qtbot.waitExposed(main_gui, 3000)
    selection = "C:/new_config.json"
    mocker.patch.object(QtWidgets.QFileDialog, 'exec_',
                        return_value=QtWidgets.QDialog.Accepted)
    mocker.patch.object(QtWidgets.QFileDialog, 'selectedFiles',
                        return_value=[selection])

    main_gui._ui.menu_open_config_file_action.trigger()
    time.sleep(3)
    assert settings.get(LAST_CONFIG_FILE) == selection
    app.conan_worker.finish_working()
    Logger.remove_qt_logger()


def testMultipleAppsUngreying(base_fixture, qtbot):
    logger = Logger()  # init logger
    temp_dir = tempfile.gettempdir()
    temp_ini_path = os.path.join(temp_dir, "config.ini")

    settings = Settings(ini_file=Path(temp_ini_path))
    config_file_path = base_fixture.testdata_path / "config_file/multiple_apps_same_package.json"
    settings.set(LAST_CONFIG_FILE, str(config_file_path))

    main_gui = main_ui.MainUi(settings)
    main_gui.show()
    qtbot.addWidget(main_gui)
    qtbot.waitExposed(main_gui, 3000)

    # wait for all tasks to finish
    app.conan_worker._worker.join()
    main_gui.update_layout()  # TODO: signal does not emit in test, must call manually

    # check app icons first two should be ungreyed, third is invalid->not ungreying
    for tab in main_gui._ui.tabs.findChildren(TabUiGrid):
        for test_app in tab.apps:
            if test_app._app_info.name in ["App1 with spaces", "App1 new"]:
                assert not test_app._app_button._greyed_out
            elif test_app._app_info.name in ["App1 wrong path", "App2"]:
                assert test_app._app_button._greyed_out
    app.conan_worker.finish_working()
    Logger.remove_qt_logger()


def testTabsCleanupOnLoadConfigFile(base_fixture, qtbot):
    logger = Logger()  # init logger
    temp_dir = tempfile.gettempdir()
    temp_ini_path = os.path.join(temp_dir, "config.ini")

    settings = Settings(ini_file=Path(temp_ini_path))
    config_file_path = base_fixture.testdata_path / "app_config.json"
    settings.set(LAST_CONFIG_FILE, str(config_file_path))

    main_gui = main_ui.MainUi(settings)
    qtbot.addWidget(main_gui)
    main_gui.show()
    qtbot.waitExposed(main_gui, 3000)
    tabs_num = 2  # two tabs in this file
    assert main_gui._ui.tabs.count() == tabs_num

    qtbot.addWidget(main_gui)
    qtbot.waitExposed(main_gui, 3000)

    app.conan_worker.finish_working()

    main_gui._re_init()  # re-init with same file

    assert main_gui._ui.tabs.count() == tabs_num
    app.conan_worker.finish_working()
    Logger.remove_qt_logger()


def testStartupWithExistingConfigAndOpenMenu(base_fixture, qtbot):
    logger = Logger()  # init logger
    temp_ini_path = os.path.join(tempfile.gettempdir(), "config.ini")

    settings = Settings(ini_file=Path(temp_ini_path))
    config_file_path = base_fixture.testdata_path / "app_config.json"
    settings.set(LAST_CONFIG_FILE, str(config_file_path))
    main_gui = main_ui.MainUi(settings)
    qtbot.addWidget(main_gui)

    main_gui.show()
    qtbot.waitExposed(main_gui, 3000)
    main_gui._ui.menu_about_action.trigger()
    time.sleep(3)
    assert main_gui._about_dialog.isEnabled()
    qtbot.mouseClick(main_gui._about_dialog._button_box.buttons()[0], QtCore.Qt.LeftButton)
    app.conan_worker.finish_working()
    Logger.remove_qt_logger()


def testOpenApp(base_fixture, qtbot):
    parent = QtWidgets.QWidget()
    parent.setObjectName("parent")

    if platform.system() == "Linux":
        app_info = AppEntry("test", "abcd/1.0.0@usr/stable", Path(sys.executable), "", "", True, Path("."))
    elif platform.system() == "Windows":
        app_info = AppEntry("test", "abcd/1.0.0@usr/stable",
                            Path(sys.executable), "", "", True, Path("."))

    app_ui = AppUiEntry(parent, app_info)
    qtbot.addWidget(parent)
    parent.show()
    app_ui.app_clicked()
    time.sleep(5)  # wait for terminal to spawn
    # check pid of created process
    if platform.system() == "Linux":
        ret = check_output(["xwininfo", "-name", "Terminal"]).decode("utf-8")
        assert "Terminal" in ret
        os.system("pkill --newest terminal")
    elif platform.system() == "Windows":
        # check windowname of process - default shell spawns with path as windowname
        ret = check_output(f'tasklist /fi "WINDOWTITLE eq {str(sys.executable)}"')
        assert "python.exe" in ret.decode("utf-8")
        lines = ret.decode("utf-8").splitlines()
        line = lines[3].replace(" ", "")
        pid = line.split("python.exe")[1].split("Console")[0]
        os.system("taskkill /PID " + pid)
