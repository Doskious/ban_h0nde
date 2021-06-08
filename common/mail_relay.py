# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText
from frozendict import frozendict

from common.exceptions import ValidationError
from common.fargable import FargAble, kwargset


class SMTPClient(FargAble, kwargset):
    """Client that accepts useful arguments and attempts to send mail."""
    # pylint: disable=no-member
    _rargs = ['to', 'subject', 'body']
    _oargs = ['host', 'port', 'username', 'password', 'sender']
    term_map = frozendict({
        'to': 'recipient',
        'sender': 'mail_sender',
        'host': 'mail_host',
        'port': 'mail_port'
    })

    def __mid_init__(self, *args, **kwargs):
        fargs = self.fargs
        for term, reterm in self.term_map.items():
            if term in fargs:
                if term == 'to':
                    self.request['kwargs'][reterm] = fargs[term]
                else:
                    self.request['kwargs'][reterm] = str(fargs[term])
                if term in self.request['kwargs']:
                    del self.request['kwargs'][term]
                if term in self.rargs:
                    self.rargs[self.rargs.index(term)] = reterm
                elif term in self.oargs:
                    self.oargs[self.oargs.index(term)] = reterm

    def __init__(self, *args, **kwargs):
        lint_inits = self._rargs + self._oargs
        for argterm in lint_inits:
            setattr(self, argterm, None)
        super(SMTPClient, self).__init__(*args, **kwargs)
        self.smtp_client = smtplib.SMTP(self.mail_host, self.mail_port)

    def _init_smtp_conn(self):
        if all((self.username, self.password)):
            self.smtp_client.ehlo_or_helo_if_needed()
            self.smtp_client.starttls()
            self.smtp_client.login(self.username, self.password)
        else:
            raise ValueError(
                "Can't initialize SMTP connection without login credentials")

    def _make_mail(self, recipient):
        message = MIMEText(self.body, _charset='utf-8')
        message['From'] = self.mail_sender
        message['To'] = recipient
        message['Subject'] = self.subject
        return message.as_string()

    def send_mail(self):
        self._init_smtp_conn()
        bad_mail = []
        for recipient in self.recipient:
            try:
                self.smtp_client.sendmail(
                    self.mail_sender, recipient, self._make_mail(recipient))
            except Exception as e:
                bad_mail.append((recipient, e))
        self.smtp_client.quit()
        if bad_mail:
            raise ValidationError(bad_mail)
