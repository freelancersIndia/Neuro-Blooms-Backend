from user_agents import parse
from apps.accounts.models.session import UserSession

class SessionService:
    @staticmethod
    def create_session(user, refresh_token_jti: str, ip_address: str, user_agent: str) -> UserSession:
        ua = parse(user_agent or '')
        browser = f"{ua.browser.family} {ua.browser.version_string}"

        if ua.is_pc:
            device = "Desktop"
        elif ua.is_mobile:
            device = "Mobile"
        elif ua.is_tablet:
            device = "Tablet"
        elif ua.is_bot:
            device = "Bot"
        else:
            device = ua.device.family or "Unknown"

        return UserSession.objects.create(
            user=user,
            refresh_token_jti=refresh_token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            browser=browser,
            device=device,
            is_active=True
        )

    @staticmethod
    def deactivate_session(refresh_token_jti: str) -> None:
        UserSession.objects.filter(refresh_token_jti=refresh_token_jti).update(is_active=False)

    @staticmethod
    def deactivate_all_sessions(user) -> None:
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
