import email
import atexit
import traceback
import re
import random
from email.utils import parsedate_to_datetime
from email.header import decode_header
import imaplib
import logging
from datetime import datetime
from mimetypes import MimeTypes
import os
import time
from email.header import decode_header
from email import message
from chardet.universaldetector import UniversalDetector
from dateutil.parser import parse
from typing import List

class EmailBackup:
    def __init__(self, host: str, username: str, password: str, output_dir: str, use_ssl:bool = True, port: int = 993, sleep_time: int = 60, resume: bool = True) -> None:
        """
        Initialize the IMAP client and login to the email account.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.mail = None
        self.output_dir = output_dir
        self.sleep_time = sleep_time
        self.state_file = os.path.abspath(os.path.join(os.path.dirname(__file__), './state'))
        self.use_ssl = use_ssl
        self.resume = resume
        self.latest_email_id = None
        self.daemon = False
        self._configure_logger()
        self.logger.info(f"State file path: {self.state_file}")
        self.connect()

    def _configure_logger(self) -> None:
        """
        Configure the logger.
        """
        # Create a logs directory if it doesn't exist
        logs_dir = os.path.join(self.output_dir, '../', 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create a timestamped log file for each run of the script
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = os.path.join(logs_dir, f'{timestamp}_{self.username}.log')

        # Configure the logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Create a file handler for logging to a file
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

        # Create a console handler for logging to the console (CLI)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def connect(self, auto_authenticate: bool = True) -> None:
        """
        Connect to the mail server.
        """
        try:
            # If we should use ssl connections.
            if self.use_ssl:
                self.mail = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.mail = imaplib.IMAP4(self.host, self.port)
            # We do this as some might want to authenticate at a different stage can vary between email provider.
            if auto_authenticate:
                self._authenticate()
        except Exception as e:
            self.logger.error(f"Failed to connect to the server: {e}")
            raise

    def _authenticate(self) -> None:
        """
        Authenticate with the mail server.
        """
        try:
            # We authenticate the the host.
            self.mail.login(self.username, self.password)
        except Exception as e:
            self.logger.error(f"Failed to authenticate: {e}")
            raise

    def backup(self, mailbox: str = 'INBOX', daemon: bool = False) -> None:
        """
        Backup the mailbox.
        """
        try:
            # Select the mailbox to backup
            self.mail.select(mailbox)
            self.daemon = daemon
            atexit.register(self._save_state, self.latest_email_id)
            _i = 0
            while True:
                self.logger.info(f"Waking up from sleep from iteration {str(_i)} going for iteration {str(_i+1)} at {datetime.now().isoformat()}")
                _i += 1
                # Fetch the list of all email IDs
                # Get the latest email ID from the state
                latest_email_id = self._load_state()

                # If there is a latest email ID, fetch emails after that ID
                if latest_email_id is not None:
                    _, data = self.mail.uid('fetch', f'{int(latest_email_id) + 1}:*', '(BODY.PEEK[])')
                else:
                    # If there is no latest email ID, fetch all emails
                    _, data = self.mail.uid('fetch', '1:*', '(BODY.PEEK[])')

                # Extract the email IDs from the data
                mail_ids = []
                for response_part in data:
                    if isinstance(response_part, tuple):
                        mail_ids.append(response_part[0].decode('utf-8'))

                if self.daemon:
                    self.latest_email_id = self._load_state()
                # Get the list of new email IDs since the last backup
                new_mail_ids = self._get_new_mail_ids(mail_ids)
                for i in new_mail_ids:
                    # Backup each new email
                    self.latest_email_id = i
                    self._backup_email(i)
                if not self.daemon:
                    # If not in daemon mode, break the loop after the first backup
                    break
                # In daemon mode, remember the ID of the latest email and wait for a while before the next backup
                self._save_state(self.latest_email_id)

                self.logger.info(f"Loop complete {datetime.now().isoformat()}: Iteration {str(_i)} going to sleep now for {str(self.sleep_time)}")
                time.sleep(self.sleep_time)
            atexit.unregister(self._save_state, self.latest_email_id)
        except Exception as e:
            self.logger.error(f"Failed to backup email: {e}")
            self.logger.error(traceback.format_exc())
            raise
        except KeyboardInterrupt as e:
            self._save_state(self.latest_email_id)
            return

    def _save_state(self, latest_email_id):
        if not os.path.exists(os.path.dirname(self.state_file)):
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            f.write(str(latest_email_id))
            self.logger.info(f"State found saving: {str(self.latest_email_id)} in file: {self.state_file}")

    def _load_state(self):
        self.logger.info(f"Loading state")
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = f.read().strip()
                if state in ('', ' '):
                    self.logger.info(f"State empty setting state to 0")
                    state = 0
                self.logger.info(f"State loadable loaded id: {str(state)}")
                return state
        return None


    def _get_new_mail_ids(self, mail_ids: List[str]) -> List[str]:
        """
        Get the list of new email IDs since the last backup.
        """
        new_mail_ids = []
        for mail_id in mail_ids:
            # Extract the email ID from the fetch command response
            uid_match = re.search(r'UID (\d+)', mail_id)
            if uid_match:
                uid = uid_match.group(1)
                if int(uid) > int(self.latest_email_id):
                    new_mail_ids.append(uid)
        return new_mail_ids

    def _backup_email(self, i: str) -> None:
        """
        Backup an individual email.
        """
        try:
            # Fetch the raw email by ID
            _, data = self.mail.uid('fetch', str(i), '(BODY.PEEK[])')
            raw_email_data = data[0][1]

            # Detect the encoding of the raw email data
            detector = UniversalDetector()
            detector.feed(raw_email_data)
            detector.close()
            encoding = detector.result['encoding']

            # If the encoding detection failed, fall back to 'ISO-8859-1'
            if encoding is None:
                encoding = 'ISO-8859-1'

            # Decode the raw email data using the detected encoding
            raw_email = raw_email_data.decode(encoding)
            # Parse the raw email to get the email message
            email_message = email.message_from_string(raw_email)

            # Decode the subject of the email
            subject = decode_header(email_message['Subject'])[0][0]
            if isinstance(subject, bytes):
                # If the subject is encoded as bytes, decode it to a string
                subject = subject.decode()

            # Log the email subject and date
            self.logger.info(f"Backing up email with subject: {subject}")

            # Get the date and time of sending the email
            date_string = email_message['Date']
            # Remove the timezone description from the date string
            date_string = re.sub(r'\(.*\)', '', date_string)
            _datetime = parse(date_string)

            # Create a directory for the email using the subject and date
            # Replace invalid characters in the subject
            subject = re.sub(r'[\\/*?:"<>|]', "", subject)
            email_dir = os.path.join(self.output_dir, f"{_datetime.strftime('%Y-%m-%d_%H-%M-%S')}_{subject}")
            os.makedirs(email_dir, exist_ok=True)

            # Write the raw email to a .eml file
            with open(os.path.join(email_dir, f'{subject}.eml'), 'w', encoding='utf-8') as f:
                f.write(raw_email)

            # If the email has multiple parts, download each part as an attachment
            if email_message.is_multipart():
                for part_iteration_counter, part in enumerate(email_message.get_payload()):
                    self._backup_attachment(part, email_dir, part_iteration_counter)
        except Exception as e:
            self.logger.error(f"Failed to backup email: {e}")
            self.logger.error(traceback.format_exc())

    def _backup_attachment(self, part: message.Message, email_dir: str, part_num: int) -> None:
        try:
            # If the part is not an attachment, skip it
            if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                return
            # Get the filename of the attachment
            filename = part.get_filename()
            if not filename:
                # If the attachment does not have a filename, generate a filename from the part number and the content type
                mime = MimeTypes()
                ext = mime.guess_extension(part.get_content_type())
                if not ext:
                    ext = '.bin'
                filename = 'part-%03d%s' % (part_num, ext)
            # Replace invalid characters in the filename
            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
            # Remove non-ASCII characters
            filename = filename.encode("ascii", errors="ignore").decode()
            # Write the attachment to a file
            try:
                file_name = os.path.join(email_dir, filename)
                if os.path.exists(file_name):
                    # If file exists, append a suffix to the filename
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(file_name):
                        filename = f"{base}_{counter}{ext}"
                        file_name = os.path.join(email_dir, filename)
                        counter += 1
                with open(file_name, 'wb') as fp:
                    fp.write(part.get_payload(decode=True))
            except Exception as e:
                self.logger.error(f"Failed while writing/creating to file: '{os.path.join(email_dir, filename)}' exception: {e}")
        except Exception as e:
            self.logger.error(f"Failed to backup email attachment part: {part_num}. Exception: {e}")
        self.logger.info(f"Finished fownloading attachment part: {file_name}")


    def close(self) -> None:
        """
        Logout from the email account.
        """
        if self.mail.state != 'LOGOUT':
            self.mail.logout()
        else:
            self.logger.info("Already logged out.")
