"""Email body templates.

Each builder returns a ``(text, html)`` tuple. The HTML is responsive and uses
inline styles so it renders on mobile and in clients that strip ``<style>``.
"""

from __future__ import annotations


def password_reset_email(link: str, expires_minutes: int) -> tuple[str, str]:
    """Build the password-reset email bodies."""
    text = (
        "Reset your Brasaland password\n\n"
        "We received a request to reset your password. Open the link below to "
        "choose a new one:\n"
        f"{link}\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used "
        "once.\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    html = f"""\
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reset your Brasaland password</title>
  </head>
  <body style="margin:0;padding:0;background-color:#1c1917;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#1c1917;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#0c0a09;border:1px solid rgba(252,211,77,0.15);border-radius:16px;padding:32px;">
            <tr>
              <td style="text-align:center;">
                <p style="margin:0 0 4px;font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:#fcd34d;">Brasaland</p>
                <h1 style="margin:0 0 16px;font-size:22px;color:#fef3c7;">Reset your password</h1>
              </td>
            </tr>
            <tr>
              <td style="font-size:15px;line-height:1.6;color:#d6d3d1;">
                <p style="margin:0 0 20px;">We received a request to reset your password. Tap the button below to choose a new one.</p>
              </td>
            </tr>
            <tr>
              <td style="text-align:center;padding:8px 0 20px;">
                <a href="{link}" style="display:inline-block;background-color:#f59e0b;color:#1c1917;font-weight:600;font-size:15px;text-decoration:none;padding:12px 28px;border-radius:12px;">Reset password</a>
              </td>
            </tr>
            <tr>
              <td style="font-size:13px;line-height:1.6;color:#a8a29e;">
                <p style="margin:0 0 8px;">Or paste this link into your browser:</p>
                <p style="margin:0 0 20px;word-break:break-all;"><a href="{link}" style="color:#fcd34d;">{link}</a></p>
                <p style="margin:0 0 4px;">This link expires in {expires_minutes} minutes and can only be used once.</p>
                <p style="margin:0;">If you didn't request this, you can safely ignore this email.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    return text, html


__all__ = ["password_reset_email"]
