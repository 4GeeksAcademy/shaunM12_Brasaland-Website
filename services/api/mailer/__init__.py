"""Outgoing email for the Brasaland API.

Named ``mailer`` (not ``email``) so it does not shadow Python's stdlib ``email``
package, which other libraries import.
"""

from .sender import send_email, send_password_reset_email, send_verification_email

__all__ = ["send_email", "send_verification_email", "send_password_reset_email"]
