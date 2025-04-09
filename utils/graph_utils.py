import random
import time
from pydantic import EmailStr
from chains.notice_extraction import NoticeEmailExtract
from utils.logging_config import LOGGER

def send_escalation_email(
    notice_email_extract: NoticeEmailExtract,
    escalation_emails: list[EmailStr],
) -> None:
    LOGGER.info("Sending escalation email...")
    for email in escalation_emails:
        time.sleep(1)
        LOGGER.info(f"Escalation email sent to {email}")


def create_legal_ticket(
        current_follow_ups: dict[str, bool] | None,
        notice_email_extract: NoticeEmailExtract
) -> str | None:
    LOGGER.info("Creating legal ticker for notice...")
    time.sleep(2)

    follow_ups = [
        None,
        """Does this message mention the states of Texas,
        Georgia, or New Jersey?""",
        """Did this notice involve an issue with FakeAirCo's
        HVAC system?""",
    ]

    if current_follow_ups:
        follow_ups = [
            f for f in follow_ups if f not in current_follow_ups.keys()
        ]
    follow_up = random.choice(follow_ups)

    if not follow_up:
        LOGGER.info("Legal ticker created.")
        return follow_up
    
    LOGGER.info("Follow-up is required before creating this ticker")
    return follow_up