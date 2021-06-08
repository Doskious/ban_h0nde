import sys
import time

try:
    import servicemanager
    from common.win_service import BaseAppServerSvc
    ON_WINDOWS = True
    SYS_PATH = "C:\\ProgramData\\PorTransfer\\"
except ImportError:
    from common.posix_daemon import BaseAppServerSvc
    ON_WINDOWS = False
    SYS_PATH = "/etc/portransferd/"


class AppServerSvc(BaseAppServerSvc):
    _sys_path = SYS_PATH


if __name__ == '__main__':
    try:
        invocation = sys.argv[1]
    except IndexError:
        invocation = True
    if invocation and isinstance(invocation, bool):
        if ON_WINDOWS:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            msg = "Daemon invocation requires {start|stop|restart} argument."
            daemon = AppServerSvc()
            daemon.log_manager.LogWarningMsg(msg)
            print(msg)
    elif not ON_WINDOWS and invocation.lower() == "start":
        daemon = AppServerSvc()
        daemon.start()
    elif not ON_WINDOWS and invocation.lower() == "stop":
        daemon = AppServerSvc()
        daemon.stop()
    elif not ON_WINDOWS and invocation.lower() == "restart":
        daemon = AppServerSvc()
        daemon.stop()
        time.sleep(10)
        daemon.start()
    else:
        AppServerSvc.parse_command_line()
