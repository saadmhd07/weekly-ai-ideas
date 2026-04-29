from __future__ import annotations

import html
import os
import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path


@dataclass(slots=True)
class EmailConfig:
    host: str
    port: int
    username: str
    password: str
    sender: str
    recipient: str
    use_tls: bool = True


def load_email_config() -> EmailConfig:
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing email configuration in .env: {', '.join(missing)}")
    return EmailConfig(
        host=os.environ["SMTP_HOST"],
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.environ["SMTP_USER"],
        password=os.environ["SMTP_PASSWORD"],
        sender=os.environ["EMAIL_FROM"],
        recipient=os.environ["EMAIL_TO"],
        use_tls=os.getenv("SMTP_TLS", "true").lower() not in {"0", "false", "no"},
    )


def send_markdown_email(path: Path, subject: str | None = None) -> None:
    config = load_email_config()
    markdown = path.read_text(encoding="utf-8")
    message = EmailMessage()
    message["Subject"] = subject or default_subject(path, markdown)
    message["From"] = config.sender
    message["To"] = config.recipient
    message.set_content(markdown)
    message.add_alternative(markdown_to_email_html(markdown), subtype="html")

    with smtplib.SMTP(config.host, config.port, timeout=60) as smtp:
        if config.use_tls:
            smtp.starttls()
        smtp.login(config.username, config.password)
        smtp.send_message(message)


def latest_output(pattern: str = "ideabox-*.md", output_dir: Path = Path("output")) -> Path:
    files = sorted(output_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        raise RuntimeError(f"No file found in {output_dir} with pattern {pattern}")
    return files[0]


def default_subject(path: Path, markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return f"GenAI Side Project Radar - {path.stem}"


def markdown_to_email_html(markdown: str) -> str:
    body = render_markdown_body(markdown)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0; padding:0; background:#f3efe7; color:#201b16;">
  <div style="display:none; max-height:0; overflow:hidden; opacity:0;">GenAI Side Project Radar</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3efe7; padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:760px; width:100%; background:#fffaf0; border:1px solid #e5d8c2; border-radius:18px; overflow:hidden;">
          <tr>
            <td style="padding:34px 36px 18px 36px; background:linear-gradient(135deg,#1e3a32,#965f2c); color:#fffaf0;">
              <div style="font-family:Georgia,serif; font-size:13px; letter-spacing:1.8px; text-transform:uppercase; opacity:.82;">GenAI Side Project Radar</div>
              <div style="font-family:Georgia,serif; font-size:32px; line-height:1.12; font-weight:700; margin-top:8px;">Ta boîte à idées hebdo</div>
              <div style="font-family:Arial,sans-serif; font-size:15px; line-height:1.5; opacity:.9; margin-top:10px;">Des signaux GenAI transformés en projets buildables, publiables et potentiellement vendables.</div>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 36px 40px 36px; font-family:Arial,sans-serif; font-size:15px; line-height:1.58;">
              {body}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_markdown_body(markdown: str) -> str:
    parts: list[str] = []
    in_list = False
    in_card = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    def close_card() -> None:
        nonlocal in_card
        if in_card:
            close_list()
            parts.append("</div>")
            in_card = False

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            close_card()
            parts.append(f"<h1 style='{style_h1()}'>{inline_md(line[2:])}</h1>")
        elif line.startswith("## "):
            close_card()
            parts.append(f"<h2 style='{style_h2()}'>{inline_md(line[3:])}</h2>")
        elif line.startswith("### "):
            close_card()
            in_card = True
            parts.append(f"<div style='{style_card()}'>")
            parts.append(f"<h3 style='{style_h3()}'>{inline_md(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                parts.append(f"<ul style='{style_ul()}'>")
                in_list = True
            parts.append(f"<li style='{style_li()}'>{inline_md(line[2:])}</li>")
        elif ": " in line and not line.startswith("http"):
            close_list()
            label, value = line.split(": ", 1)
            parts.append(
                f"<p style='{style_p()}'><strong style='color:#7c3f16;'>{html.escape(label)}:</strong> {inline_md(value)}</p>"
            )
        else:
            close_list()
            parts.append(f"<p style='{style_p()}'>{inline_md(line)}</p>")
    close_card()
    close_list()
    return "\n".join(parts)


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r"<a href='\2' style='color:#0f6b5c; text-decoration:underline;'>\1</a>",
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code style='background:#f0e2ca; padding:2px 5px; border-radius:5px;'>\1</code>", escaped)
    return escaped


def style_h1() -> str:
    return "font-family:Georgia,serif; font-size:28px; line-height:1.2; color:#1e3a32; margin:0 0 22px 0;"


def style_h2() -> str:
    return "font-family:Georgia,serif; font-size:22px; line-height:1.25; color:#1e3a32; margin:34px 0 14px 0; padding-top:10px; border-top:2px solid #eadbc3;"


def style_h3() -> str:
    return "font-family:Georgia,serif; font-size:18px; line-height:1.3; color:#201b16; margin:0 0 12px 0;"


def style_card() -> str:
    return "background:#ffffff; border:1px solid #eadbc3; border-left:5px solid #c46f2b; border-radius:14px; padding:18px 18px 14px 18px; margin:16px 0; box-shadow:0 2px 8px rgba(55,38,20,.05);"


def style_p() -> str:
    return "font-family:Arial,sans-serif; font-size:15px; line-height:1.58; color:#2b241d; margin:8px 0;"


def style_ul() -> str:
    return "margin:8px 0 18px 0; padding-left:22px;"


def style_li() -> str:
    return "font-family:Arial,sans-serif; font-size:15px; line-height:1.55; color:#2b241d; margin:7px 0;"
