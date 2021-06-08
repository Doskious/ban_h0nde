from json import load
import pathlib
import time

from frozendict import frozendict

from common.assist import coercelist, kwargset
from common.exceptions import NoConfiguration, ValidationError
from common.get_path import BASE_DIR
from common.log_shim import EmailLogManager


class CoreApplication(EmailLogManager):
    """Core Daemon/Service Application Logic"""
    _svc_name_ = "watcher_transfer"
    _svc_display_name_ = "Path-Watcher File-Transfer Handler"
    _svc_description_ = "SCP transfer of matching files"
    _sys_path = BASE_DIR
    isrunning = False

    @property
    def sys_path(self):
        return self._sys_path

    def __init__(self, *args, **kwargs):
        self.settings_conf = pathlib.os.path.join(
            self.sys_path, "settings.json")
        super().__init__(*args, **kwargs)

    def normal_start_email(self):
        running_on = self.config.get('running_on', "UNDEFINED")
        self.email_notify(
            f"Watcher-Transfer (on {running_on}) has successfully started!",
            "[{deployed_context}] Watcher-Transfer (on {running_on}) started")

    def normal_stop_email(self):
        running_on = self.config.get('running_on', "UNDEFINED")
        self.email_notify(
            f"Watcher-Transfer (on {running_on}) has been stopped "
            "through user agency or normal server operations.",
            "[{deployed_context}] Watcher-Transfer (on {running_on}) stopped")

    def main(self):
        observers = []
        observer = Observer()
        bad_monitor_config = {}
        for fcat, monitor_paths in self.config['monitor_categories'].items():
            for idir in monitor_paths:
                ipath = pathlib.Path(idir)
                if not all([ipath.exists(), ipath.is_dir()]):
                    if fcat not in bad_monitor_config:
                        bad_monitor_config[fcat] = []
                    bad_monitor_config[fcat].append(idir)
                    continue
                eh = eventHandler(
                    config=self.config, category=fcat,
                    log_manager=self.log_manager)
                observer.schedule(eh, path=idir, recursive=True)
                self.log_manager.LogInfoMsg(f"Watching {idir}")
                observers.append(observer)
        if bad_monitor_config:
            bad_monitor_config_msg = []
            for bad_cat, bad_list in bad_monitor_config.items():
                if not bad_list:
                    continue
                if not bad_monitor_config_msg:
                    bad_monitor_config_msg.append("Directories not found:")
                joined_bad_list = " ;  ".join(bad_list)
                bad_monitor_config_msg.append(f"{bad_cat}: {joined_bad_list}")
            if bad_monitor_config_msg:
                bad_monitor_config_msg.append(
                    "Unable to monitor non-existent paths.")
                message_for_email = "\n".join(bad_monitor_config_msg)
                self.log_manager.LogWarningMsg(message_for_email)
                self.email_notify(message_for_email)
        try:
            observer.start()
            while self.isrunning:
                time.sleep(1)
        except Exception as e:
            running_on = self.config.get('running_on', "UNDEFINED")
            msg = (
                f"Caught exception: {e}\n"
                f"Watcher-Transfer (on {running_on}) is STOPPED.")
            self.log_manager.LogInfoMsg(msg)
            self.email_notify(msg)
        finally:
            for o in observers:
                o.unschedule_all()
                # stop observer if interrupted
                o.stop()
            stop_msg = "Watcher-Transfer watchers unscheduled."
            self.log_manager.LogInfoMsg(stop_msg)
        for o in observers:
            # Wait until the thread terminates before exit
            o.join()
        done_msg = "Watcher-Transfer main process complete."
        self.log_manager.LogInfoMsg(done_msg)

    def load_config(self):
        """
        Loads the configuration settings at run-time

        Required values:
            config['attempts_config']['retries'] -- int
            config['attempts_config']['interval'] -- int
            config['sftp_base_target_path'] -- path-string
            config['email_addressing'] -- dict
            config['always_transfer'] -- list
            config['deployed_context'] -- string
            config['running_on'] -- string
            config['monitor_categories'] -- dict
        """
        required_top_settings = {
            "attempts_config": dict,
            "sftp_base_target_path": str,
            "email_addressing": dict,
            "always_transfer": list,
            "deployed_context": str,
            "running_on": str,
            "monitor_categories": dict
        }
        required_sub_settings = {
            "attempts_config": {
                "retries": int,
                "interval": int
            }
        }
        # Special checks to ensure the setting is formatted properly.
        # sftp_base_target_path needs to be a correctly-formatted target path
        # for the destination system, to identify the target sub-directory
        # under which the transfers will land.
        # IF the destination is not jailed, this will be an absolute path from
        # root.  (Not sure how it would be formatted for a Windows-based
        # destination.)  If the destination is jailed, this will be the
        # apparent path within the jail.
        # Checking for this without initializing the connection is ... hard to
        # handle properly without making assumptions...
        # special_checks = {
        #     "sftp_base_target_path": None
        # }
        conf = pathlib.Path(self.settings_conf)
        try:
            if not conf.exists():
                raise NoConfiguration("settings.json configuration missing")
            with open(self.settings_conf, 'r') as json_in:
                self.config = kwargset(**load(json_in))
            bad_settings = {}
            for key, cls_type in required_top_settings.items():
                if key not in self.config:
                    bad_settings[key] = f"Required value `{key}` missing."
                    continue
                test_val = self.config[key]
                if not isinstance(test_val, cls_type):
                    bad_type_name = type(test_val).__name__
                    bad_settings[key] = (
                        f"Invalid data-structure: "
                        f"{key} should be {cls_type.__name__}, "
                        f"not {bad_type_name}.")
                if key in required_sub_settings:
                    for subkey, sub_type in required_sub_settings[key].items():
                        skey = f"{key}.{subkey}"
                        if subkey not in test_val:
                            bad_settings[skey] =\
                                f"Required value `{skey}` missing."
                        test_subval = test_val[subkey]
                        if not isinstance(test_subval, sub_type):
                            bad_sub_type_name = type(test_subval).__name__
                            bad_settings[skey] = (
                                f"Invalid data-structure: "
                                f"{skey} should be {sub_type.__name__}, "
                                f"not {bad_sub_type_name}.")
            if bad_settings:
                raise ValidationError(bad_settings)
        except Exception as e:
            message = (
                "Unable to start service; please provide correct "
                f"configuration in {self.settings_conf}.\n\nException: {e}")
            raise NoConfiguration(message)
