import socket

# pylint: disable=import-error
import win32serviceutil

import servicemanager
import win32event
import win32service
# pylint: enable=import-error

from watcher.core_app import CoreApplication


class SMWinservice(win32serviceutil.ServiceFramework):
    '''Base class to create winservice in Python'''

    _svc_name_ = 'pythonService'
    _svc_display_name_ = 'Python Service'
    _svc_description_ = 'Python Service Description'

    @classmethod
    def parse_command_line(cls):
        '''
        ClassMethod to parse the command line
        '''
        win32serviceutil.HandleCommandLine(cls)

    def __init__(self, args):
        '''
        Constructor of the winservice
        '''
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        '''
        Called when the service is asked to stop
        '''
        self.stop()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        '''
        Called when the service is asked to start
        '''
        self.start()
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def start(self):
        '''
        Override to add logic before the start
        eg. running condition
        '''

    def stop(self):
        '''
        Override to add logic before the stop
        eg. invalidating running condition
        '''

    def main(self):
        '''
        Main class to be ovverridden to add logic
        '''


class BaseAppServerSvc(SMWinservice):
    log_manager = servicemanager

    def start(self):
        self.isrunning = True

    def stop(self):
        self.isrunning = False

    def SvcDoRun(self):
        try:
            self.load_config()
            self.normal_start_email()
            super().SvcDoRun()
            self.normal_stop_email()
        except Exception as e:
            msg = "Configuration error: %s" % (e)
            self.log_manager.LogErrorMsg(msg)
            self.email_notify(msg)
