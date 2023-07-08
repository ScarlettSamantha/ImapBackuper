import argparse
import atexit
from os import path
import os

from .email_backup import EmailBackup

def main():
    parser = argparse.ArgumentParser(description='Backup emails from an IMAP server to a local directory.')
    parser.add_argument('--username', required=True, help='The username for the IMAP server.')
    parser.add_argument('--password', required=True, help='The password for the IMAP server.')
    parser.add_argument('--server', required=True, help='The IMAP server to connect to.')
    parser.add_argument('--port', type=int, default=993, help='The port to use to connect to the IMAP server.')
    parser.add_argument('--use_ssl', type=bool, default=True, help='Whether to use SSL to connect to the IMAP server.')
    parser.add_argument('--directory', required=False, default=path.abspath(path.join(path.basename(__file__), '../emails')), help='The directory to backup the emails to.')
    parser.add_argument('--sleep_timeout', required=False, default=60, help='How long the main loop in daemon mode sleeps in seconds for before the next import session')
    parser.add_argument('--imap_import_folder', type=str, default='INBOX', required=False, help='The Imap folder that is used to backup defualt is Inbox (cappital sensitive)')
    parser.add_argument('--daemon', action='store_true', default=False, help='Switches between daemon mode and the default run once mode.')
    parser.add_argument('--no-resume', action='store_true', default=False, help='If this switch is active it will not attempt to resume the latest download session.')
    args = parser.parse_args()

    backup = EmailBackup(username=args.username, password=args.password, host=args.server, output_dir=args.directory, port=args.port, use_ssl=args.use_ssl, sleep_time=args.sleep_timeout, resume=not args.no_resume)
    backup.connect()
    atexit.register(backup.close)
    backup.backup(args.imap_import_folder, args.daemon)
    
if __name__ == "__main__":
    if os.getenv('DAEMON').lower() == 'true':
        os.sys.argv.append('--daemon')
    main()
