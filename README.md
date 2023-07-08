# Email Backup

This is a script to backup emails from an IMAP server. It can run in a one-off mode or in a daemon mode where it continuously backs up new emails. The script uses the IMAP protocol to connect to the email server and download the emails. 

## IMAP

IMAP stands for Internet Mail Access Protocol. It's a method used by email clients to retrieve messages from a mail server. The default IMAP port is 143, and the default IMAP SSL (IMAPS) port is 993. 

Most email services support IMAP. Here are the IMAP server hostnames for some common email services:

- Gmail: imap.gmail.com
- Outlook.com / Hotmail.com: imap-mail.outlook.com
- Yahoo Mail: imap.mail.yahoo.com
- AOL Mail: imap.aol.com

## Arguments

The script accepts the following command-line arguments:

- `--username`: Your email username.
- `--password`: Your email password.
- `--server`: The IMAP server hostname. Default is `imap.gmail.com`.
- `--port`: The IMAP server port. Default is `993`.
- `--output`: The output directory where the emails will be saved. Default is `./emails`.
- `--daemon`: Run in daemon mode. If this argument is present, the script will run in daemon mode. If it's absent, the script will run in one-off mode.

## Usage

To run the script, you need to provide your email username and password. The script will connect to the IMAP server, download all emails from the inbox, and save them to the local file system. Each email is saved to a separate .eml file, and attachments are saved to separate files as well.

Here's how to run the script with all arguments:

```bash
python email_backup/app.py --username your-email@gmail.com --password your-password --server imap.gmail.com --port 993 --output ./emails
```

Replace "your-email@gmail.com" and "your-password" with your actual email and password. Replace "./emails" with the path on your host system where you want to save the emails.

## Daemon Mode

In daemon mode, the script will continuously monitor the email account for new emails and back them up as they arrive. This is useful if you want to maintain a real-time backup of your emails.

To run the script in daemon mode, add the `--daemon` argument:

```bash
python email_backup/app.py --username your-email@gmail.com --password your-password --server imap.gmail.com --port 993 --output ./emails --daemon
```

## Docker

The script can also be run in a Docker container. This is useful if you want to run the script in a self-contained environment or deploy it to a Docker-capable host.

To build the Docker image, run:

```bash
docker build -t email_backup .
```

To run the script in a Docker container, run:

```bash
docker run -v /path/to/emails:/app/emails email_backup python email_backup/app.py --username your-email@gmail.com --password your-password --server imap.gmail.com --port 993 --output /app/emails
```

Replace "/path/to/emails" with the path on your host system where you want to save the emails.

To run the script in daemon mode in a Docker container, add the `--daemon` argument:

```bash
docker run -v /path/to/emails:/app/emails email_backup python email_backup/app.py --username your-email@gmail.com --password your-password --server imap.gmail.com --port 993 --output /app/emails --daemon
```

## Docker Compose

You can also use Docker Compose to run the script. This is useful if you want to run the script with a single command, or if you want to run multiple instances of the script.

To run the script with Docker Compose, run:

```bash
docker-compose up
```

This will start the script in daemon mode. The emails will be saved to the `./emails` directory on your host system.