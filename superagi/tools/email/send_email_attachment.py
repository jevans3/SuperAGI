import imaplib
import mimetypes
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Type

from pydantic import BaseModel, Field
from superagi.helper.imap_email import ImapEmail
from superagi.tools.base_tool import BaseTool
from superagi.config.config import get_config


class SendEmailAttachmentInput(BaseModel):
    to: str = Field(..., description="Email Address of the Receiver, default email address is 'example@example.com'")
    subject: str = Field(..., description="Subject of the Email to be sent")
    body: str = Field(..., description="Email Body to be sent")
    filename: str = Field(..., description="Name of the file to be sent as an Attachment with Email")


class SendEmailAttachmentTool(BaseTool):
    """
    Send an Email with Attachment tool

    Attributes:
        name : The name.
        description : The description.
        args_schema : The args schema.
    """
    name: str = "Send Email with Attachment"
    args_schema: Type[BaseModel] = SendEmailAttachmentInput
    description: str = "Send an Email with a file attached to it"

    def _execute(self, to: str, subject: str, body: str, filename: str) -> str:
        """
        Execute the send email tool with attachment.

        Args:
            to : The email address of the receiver.
            subject : The subject of the email.
            body : The body of the email.
            filename : The name of the file to be sent as an attachment with the email.

        Returns:

        """
        input_root_dir = get_config('RESOURCES_INPUT_ROOT_DIR')
        output_root_dir = get_config('RESOURCES_OUTPUT_ROOT_DIR')
        final_path = None

        if input_root_dir is not None:
            input_root_dir = input_root_dir if input_root_dir.startswith("/") else os.getcwd() + "/" + input_root_dir
            input_root_dir = input_root_dir if input_root_dir.endswith("/") else input_root_dir + "/"
            final_path = input_root_dir + filename

        if final_path is None or not os.path.exists(final_path):
            if output_root_dir is not None:
                output_root_dir = output_root_dir if output_root_dir.startswith(
                    "/") else os.getcwd() + "/" + output_root_dir
                output_root_dir = output_root_dir if output_root_dir.endswith("/") else output_root_dir + "/"
                final_path = output_root_dir + filename
        attachment = os.path.basename(final_path)
        return self.send_email_with_attachment(to, subject, body, final_path, attachment)

    def send_email_with_attachment(self, to, subject, body, attachment_path, attachment) -> str:
        """
        Send an email with attachment.

        Args:
            to : The email address of the receiver.
            subject : The subject of the email.
            body : The body of the email.
            attachment_path : The path of the file to be sent as an attachment with the email.
            attachment : The name of the file to be sent as an attachment with the email.

        Returns:
            
        """
        email_sender = self.tool_kit_config.default_tool_config_func('EMAIL_ADDRESS')
        email_password = self.tool_kit_config.default_tool_config_func('EMAIL_PASSWORD')
        if email_sender == "" or email_sender.isspace():
            return "Error: Email Not Sent. Enter a valid Email Address."
        if email_password == "" or email_password.isspace():
            return "Error: Email Not Sent. Enter a valid Email Password."
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = email_sender
        message["To"] = to
        signature = self.tool_kit_config.default_tool_config_func('EMAIL_SIGNATURE')
        if signature:
            body += f"\n{signature}"
        message.set_content(body)
        if attachment_path:
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(attachment_path, "rb") as file:
                message.add_attachment(file.read(), maintype=maintype, subtype=subtype, filename=attachment)

        send_to_draft = self.tool_kit_config.default_tool_config_func('EMAIL_DRAFT_MODE')

        if message["To"] == "example@example.com" or send_to_draft:
            draft_folder = self.tool_kit_config.default_tool_config_func('EMAIL_DRAFT_FOLDER')
            imap_server = self.tool_kit_config.default_tool_config_func('EMAIL_IMAP_SERVER')
            conn = ImapEmail().imap_open(draft_folder, email_sender, email_password, imap_server)
            conn.append(
                draft_folder,
                "",
                imaplib.Time2Internaldate(time.time()),
                str(message).encode("UTF-8")
            )
            return f"Email went to {draft_folder}"
        else:
            smtp_host = self.tool_kit_config.default_tool_config_func('EMAIL_SMTP_HOST')
            smtp_port = self.tool_kit_config.default_tool_config_func('EMAIL_SMTP_PORT')
            with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(email_sender, email_password)
                smtp.send_message(message)
                smtp.quit()
            return f"Email was sent to {to}"
