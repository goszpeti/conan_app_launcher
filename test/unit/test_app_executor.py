import os
import stat
import platform
import sys
import tempfile
import time
from pathlib import Path
from subprocess import check_output
import conan_app_launcher
from conan_app_launcher.components.file_runner import (execute_app, open_file,
                                                       run_file)


def testChooseRunFile(base_fixture, tmp_path, mocker):
    """
    Tests, that the function call is propagated correctly
    Existant path with a filesize > 0 expected
    """
    # Mock away the calls
    mocker.patch('conan_app_launcher.components.file_runner.open_file')
    test_file = Path(tmp_path) / "test.txt"
    with open(test_file, "w") as f:
        f.write("test")

    run_file(test_file, False, "")

    conan_app_launcher.components.file_runner.open_file.assert_called_once_with(test_file)


def testChooseRunScript(base_fixture, tmp_path, mocker):
    """
    Tests, that the function call is propagated correctly
    Existant path with a filesize > 0 expected
    """
    if platform.system() != "Windows":
        return
    # Mock away the calls
    mocker.patch('conan_app_launcher.components.file_runner.execute_app')

    test_file = Path(tmp_path) / "test.bat"
    with open(test_file, "w") as f:
        f.write("test")

    run_file(test_file, False, "")

    conan_app_launcher.components.file_runner.execute_app.assert_called_once_with(test_file, False, "")


def testChooseRunExe(base_fixture, tmp_path, mocker):
    # Mock away the calls
    mocker.patch('conan_app_launcher.components.file_runner.execute_app')

    if platform.system() == "Linux":
        test_file = Path(tmp_path) / "test"
        with open(test_file, "w") as f:
            f.write("test")
        # use chmod to set as executable
        st = os.stat(str(test_file))
        os.chmod(str(test_file), st.st_mode | stat.S_IEXEC)
    elif platform.system() == "Windows":
        test_file = Path(tmp_path) / "test.exe"
        with open(test_file, "w") as f:
            f.write("test")

    run_file(test_file, False, "")

    conan_app_launcher.components.file_runner.execute_app.assert_called_once_with(test_file, False, "")


def testStartAppWithArgsNonCli(base_fixture):
    test_file = Path(tempfile.gettempdir(), "test.txt")
    executable = Path(sys.executable)
    is_console_app = False
    args = f"-c f=open(r'{str(test_file)}','w');f.write('test');f.close()"

    pid = execute_app(executable, is_console_app, args)

    time.sleep(1)
    assert test_file.is_file()
    os.remove(test_file)


def testStartAppWithArgsCliOption(base_fixture):
    test_file = Path(tempfile.gettempdir(), "test.txt")

    executable = Path(sys.executable)
    is_console_app = True
    args = f"-c f=open(r'{str(test_file)}','w');f.write('test');f.close()"
    pid = execute_app(executable, is_console_app, args)

    time.sleep(5)  # wait for terminal to spawn
    assert test_file.is_file()

    os.remove(test_file)


def testStartCliOptionApp(base_fixture):
    executable = Path(sys.executable)
    is_console_app = True
    args = ""
    pid = execute_app(executable, is_console_app, args)

    if platform.system() == "Linux":
        time.sleep(5)  # wait for terminal to spawn
        # check pid of created process
        ret = check_output(["xwininfo", "-name", "Terminal"]).decode("utf-8")
        assert "Terminal" in ret
        os.system("pkill --newest terminal")
    elif platform.system() == "Windows":
        assert pid > 0
        time.sleep(1)
        ret = check_output(f'tasklist /fi "PID eq {str(pid)}"')
        assert "python.exe" in ret.decode("utf-8")
        os.system("taskkill /PID " + str(pid))


def testStartScript(base_fixture, tmp_path):
    if platform.system() != "Windows":
        return
    res_file = Path(tmp_path) / "res.txt"
    assert not res_file.is_file()
    test_file = Path(tmp_path) / "test.bat"
    with open(test_file, "w") as f:
        f.write("echo test > " + str(res_file))

    pid = execute_app(test_file, False, "")

    time.sleep(2)  # wait for command to be executed

    assert res_file.is_file()


def testOpenFile(base_fixture):
    """ Test file opener by opening a text file and checking for the app to spawn"""
    test_file = Path(tempfile.gettempdir(), "test.txt")
    with open(str(test_file), "w") as f:
        f.write("test")

    open_file(test_file)

    time.sleep(3)  # wait for program to start
    if platform.system() == "Linux":
        # set for textfile
        ret = check_output(["xdg-mime", "default", "org.gnome.Terminal.desktop",
                            "text/plain"]).decode("utf-8")

        ret = check_output(["xdg-mime", "query", "default", "text/plain"]).decode("utf-8")
        # check pid of created process
        ret = check_output(["xwininfo", "-name", "Terminal"]).decode("utf-8")
        assert "Terminal" in ret
        os.system("pkill --newest terminal")
    elif platform.system() == "Windows":
        default_app = "notepad.exe"
        # this is application specific
        ret = check_output(f'tasklist /fi "IMAGENAME eq {default_app}"')
        assert default_app in ret.decode("utf-8")
        lines = ret.decode("utf-8").splitlines()
        line = lines[3].replace(" ", "")
        pid = line.split(default_app)[1].split("Console")[0]
        os.system("taskkill /PID " + pid)
    os.remove(test_file)
