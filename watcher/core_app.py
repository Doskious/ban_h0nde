"""
# WARNING!
# DO not use this script for malicious purposes!
# Original Author: daegontaven - taven#0001 -- see `original_nugget.py`
# README
# I have resigned from using discord indefinitely to pursue schoolwork.
# As such I will not be maintaining this script anymore.
# How to  Install
1 - Download Python 3.7 or 3.6   : https://www.python.org/downloads/
2 - Run this command  : python3 -m pip install discord.py
3 - Run this command  : python3  discord-ban-bot.py
4 - Invite bot to the servers you want to ban members from.
5 - Wait until banning is done. Don't close the terminal. This may take a while.
"""
# from json import load
# import pathlib
import re
import time

import discord

# from common.assist import coercelist, kwargset
# from common.exceptions import NoConfiguration, ValidationError
from common.get_path import BASE_DIR
from common.log_shim import EmailLogManager


TOKEN = ""      # Put your Bot token here
BAD_NAME = re.compile(
    r'.*([Tt][Ww][Ii][Tt]{2}[Ee][Rr]\.[Cc][Oo][Mm])(\/)[Hh]0[Nn][Dd][Ee].*')

class CoreApplication(EmailLogManager):
    """Core Daemon/Service Application Logic"""
    _svc_name_ = "ban_h0nde"
    _svc_display_name_ = "Discord Bot to Ban h0nde"
    _svc_description_ = "Ban any user found on the server with the wrong name"
    _sys_path = BASE_DIR
    isrunning = False

    @property
    def sys_path(self):
        return self._sys_path

    def __init__(self, *args, **kwargs):
        # self.settings_conf = pathlib.os.path.join(
        #     self.sys_path, "settings.json")
        super().__init__(*args, **kwargs)

    def normal_start_email(self):
        running_on = self.config.get('running_on', "DEFAULT")
        self.email_notify(
            f"Ban-h0nde (on {running_on}) has successfully started!",
            "[{deployed_context}] Ban-h0nde (on {running_on}) started")

    def normal_stop_email(self):
        running_on = self.config.get('running_on', "DEFAULT")
        self.email_notify(
            f"Ban-h0nde (on {running_on}) has been stopped "
            "through user agency or normal server operations.",
            "[{deployed_context}] Ban-h0nde (on {running_on}) stopped")

    def main(self):
        client = discord.Client()
        @client.event
        async def on_ready():
            self.log_manager.LogInfoMsg('Logged in!')
            for member in client.get_all_members():
                if not BAD_NAME.match(member.name):
                    continue
                await member.ban(
                    reason="Banned by Ban-h0nde", delete_message_days=7)
                self.log_manager.LogInfoMsg(f"Banned {member.display_name}!")
            self.log_manager.LogInfoMsg("Banning is complete!")
        try:
            client.run(TOKEN)
            while self.isrunning:
                time.sleep(5)
        except Exception as e:
            msg = f"Caught exception: {e}\n"
            self.log_manager.LogInfoMsg(msg)
            self.email_notify(msg)
        finally:
            running_on = self.config.get('running_on', "DEFAULT")
            stop_msg = f"Ban-h0nde (on {running_on}) is STOPPED."
            self.log_manager.LogInfoMsg(stop_msg)
        done_msg = "Banb-h0nde main process complete."
        self.log_manager.LogInfoMsg(done_msg)

    def load_config(self):
        # Check the git commit history for what was here before to read in
        # settings from a json-formatted file.
        self.config = {}
