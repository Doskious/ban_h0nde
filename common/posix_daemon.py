import logging
from logging import handlers
import pathlib
import pwd
import signal
import sys
from daemonize import Daemonize

from common.assist import coercelist
from common.constants import ERRTS
from common.flux import NewDelorean
from common.log_shim import LoggingShim

from watcher.core_app import CoreApplication


class EchoLogManager(LoggingShim):

    def LogMsg(self, log_type, message, args=None):
        if args is None:
            args = tuple()
        else:
            args = tuple(coercelist(args))
        try:
            filled_message = message % args
        except TypeError:
            filled_message = message.format(*args)
        now = NewDelorean()
        timestamp = now.format_datetime(ERRTS)
        print(f"[{timestamp}] {log_type}: {filled_message}")


class DaemonLogManager(EchoLogManager):
    logger = None

    def __init__(self, daemon_logger=None):
        if isinstance(daemon_logger, logging.Logger):
            self.logger = daemon_logger
        super().__init__()

    def LogMsg(self, log_type: str, message: str, args=None):
        if not isinstance(self.logger, logging.Logger):
            return super().LogMsg(log_type, message, args)
        try:
            log_type = int(log_type)
        except ValueError:
            if log_type not in self.levels:
                raise ValueError(
                    '`log_type` value invalid, must be one of: '
                    '{}'.format(", ".join(self.levels)))
            else:
                log_type = self.levels[log_type]
        if args is None:
            args = tuple()
        else:
            args = tuple(coercelist(args))
        self.logger.log(log_type, message, *args)


class RunAsRoot(Exception):
    """Raised to indicate that the daemon is running as root."""


class BaseAppServerSvc(CoreApplication, Daemonize):
    log_mgr_class = DaemonLogManager
    _usr_path = None

    @property
    def sys_path(self):
        if self._usr_path is None:
            try:
                if pathlib.os.geteuid() == 0:
                    raise RunAsRoot
                usr_local = pathlib.Path(
                    pathlib.os.path.join(
                        pathlib.Path.home(),
                        ".config", "portransferd"))
                usr_local.mkdir(parents=True, exist_ok=True)
                self._usr_path = usr_local.resolve()
            except RunAsRoot:
                self._usr_path = self._sys_path
        return self._usr_path

    def __init__(self, *args, **kwargs):
        self.normal_stop = False
        system_logging = False
        if self.log_manager is None:
            if issubclass(self.log_mgr_class, DaemonLogManager):
                system_logging = True
        pid_path = pathlib.os.path.join(
            self.sys_path, f"{self._svc_name_}.pid")
        pid = pathlib.os.path.abspath(pid_path)
        action = self.cls_action
        super().__init__(self._svc_name_, pid, action, *args, **kwargs)
        if system_logging:
            self.logger = logging.getLogger(self.app)
            self.logger.setLevel(logging.DEBUG)
            # Display log messages only on defined handlers.
            self.logger.propagate = False  # Initialize syslog.
            # It will correctly work on OS X, Linux and FreeBSD.
            if sys.platform == "darwin":
                syslog_address = "/var/run/syslog"
            else:
                syslog_address = "/dev/log"
            # We will continue with syslog initialization only if actually
            # have such capabilities on the machine we are running this.
            if pathlib.os.path.exists(syslog_address):
                syslog = handlers.SysLogHandler(syslog_address)
                if self.verbose:
                    syslog.setLevel(logging.DEBUG)
                else:
                    syslog.setLevel(logging.INFO)
                # Try to mimic to normal syslog messages.
                formatter = logging.Formatter(
                    "%(asctime)s %(name)s: %(message)s", "%b %e %H:%M:%S")
                syslog.setFormatter(formatter)
                self.logger.addHandler(syslog)
                self.log_manager = self.log_mgr_class(self.logger)

    @classmethod
    def parse_command_line(cls):
        '''
        ClassMethod to parse the command line
        '''
        fg_daemon = cls(foreground=True)
        fg_daemon.start()

    def cls_action(self):
        """
        Wrapper to self-invoke
        """
        try:
            self.load_config()
            self.normal_start_email()
            self.main()
            self.normal_stop_email()
        except Exception as e:
            msg = f"Configuration error: {e}"
            self.log_manager.LogErrorMsg(msg)
            self.email_notify(msg)

    def normal_stop_email(self):
        """
        Send notification for normal stopping.
        """
        self.normal_stop = True
        super().normal_stop_email()

    def start(self):
        """
        Start daemonization process.
        """
        self.isrunning = True
        super().start()

    def stop(self):
        """
        stop other already running Daemon service, via SIGTERM
        """
        # Change uid
        if self.user:
            try:
                uid = pwd.getpwnam(self.user).pw_uid
            except KeyError:
                self.log_manager.LogErrorMsg(f"User {self.user} not found.")
                sys.exit(1)
            try:
                pathlib.os.setuid(uid)
            except OSError:
                self.log_manager.LogErrorMsg("Unable to change uid.")
                sys.exit(1)
        try:
            with open(self.pid, "r") as old_pidfile:
                old_pid = old_pidfile.read()
            pathlib.os.kill(int(old_pid), signal.SIGTERM)
        except FileNotFoundError:
            self.log_manager.LogErrorMsg(
                f"Unable to locate {self.pid} indicating process to end.")
        except PermissionError:
            self.log_manager.LogErrorMsg(
                f"Unable to terminate process, {self.user} lacks permissions.")
        except Exception as e:
            self.log_manager.LogErrorMsg(e)

    def sigterm(self, signum, frame):
        """
        These actions will be done after SIGTERM.
        """
        self.log_manager.LogWarningMsg(
            "Caught signal %s. Stopping daemon.", signum)
        def ureg_obs_timeout(signum, frame):  # pylint: disable=unused-argument
            message = "Observer unregistration timeout... Force-stopping"
            self.log_manager.LogErrorMsg(message)
            self.email_notify(message)
            self.exit(1)
        signal.signal(signal.SIGALRM, ureg_obs_timeout)
        self.isrunning = False
        signal.alarm(10)

    def exit(self, exit_code=0):  # pylint: disable=arguments-differ
        """
        Cleanup pid file at exit.
        """
        self.log_manager.LogWarningMsg("Stopping daemon.")
        pathlib.os.remove(self.pid)
        if not self.normal_stop:
            message = "Watcher-Transfer stopped abnormally."
            # Try to let us know, but take nothing for granted...
            try:
                self.email_notify(message)
            except:  # pylint: disable=bare-except
                pass
            try:
                self.log_manager.LogErrorMsg(message)
            except:  # pylint: disable=bare-except
                pass
        sys.exit(exit_code)
