from frozendict import frozendict

from common.assist import coercelist


LOG_LEVELS = frozendict({
    "NOTSET": 0,
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
    "FATAL": 50,
})


class LoggingUndefined(Exception):
    """Indicates that logging is undefined."""


class LoggingShim:
    levels = LOG_LEVELS

    def LogMsg(self, log_type, message, args=None):
        if args is None:
            args = tuple()
        else:
            args = tuple(coercelist(args))
        try:
            filled_message = message % args
        except TypeError:
            filled_message = message.format(*args)
        raise LoggingUndefined(
            f"Cannot log message `{filled_message}` as `{log_type}` properly, "
            f"logging manager is not defined.")

    def LogDebugMsg(self, message, args=None):
        self.LogMsg("DEBUG", message, args)

    def LogInfoMsg(self, message, args=None):
        self.LogMsg("INFO", message, args)

    def LogErrorMsg(self, message, args=None):
        self.LogMsg("ERROR", message, args)

    def LogWarningMsg(self, message, args=None):
        self.LogMsg("WARNING", message, args)


class LogManager:
    log_manager = None
    log_mgr_class = LoggingShim

    def __init__(self, *args, **kwargs):
        if self.log_manager is None:
            self.log_manager = self.log_mgr_class()
        super().__init__(*args, **kwargs)


class EmailLogManager(LogManager):

    def __init__(self, *args, **kwargs):
        self.config = frozendict({})
        super().__init__(*args, **kwargs)

    def email_notify(self, msg, subject=None):  # pylint: disable=unused-argument
        self.log_manager.LogErrorMsg("Unable to send mail - not configured")
