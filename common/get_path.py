import pathlib
import sys


BASE_DIR = pathlib.os.path.dirname((
    pathlib.os.path.dirname(pathlib.os.path.abspath(__file__))))


def exe_path(default_path=BASE_DIR, on_windows=False):
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the build environment
        # extends the sys module by a flag `frozen=True`
        # This should return the directory to look for the settings.json
        # file.
        # On Windows, that's in C:\ProgramData\ban_h0nde\
        # On Linux, that's in /etc/ban_h0nde/
        if on_windows:
            app_path_list = (
                "C:\\ProgramData", "ban_h0nde", 'settings.json')
        else:
            app_path_list = (
                '/etc', 'ban_h0nde', 'settings.json')
        application_path = pathlib.os.path.join(*app_path_list)
        # check to see if this path exists.  If not, try to create it, or
        # fall back to sys.executable
        settings_path = pathlib.Path(application_path)
        if not settings_path.parent.exists():
            try:
                settings_path.parent.mkdir()
            except:  # pylint: disable=bare-except
                application_path = sys.executable
    else:
        application_path = default_path  # Pass in as __file__
    return pathlib.os.path.dirname(pathlib.os.path.abspath(application_path))
