from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Populate the Django user from the Google profile.

    Google is the only provider and its email is verified, so connecting an
    existing local user by email is safe. In practice the database starts empty
    and every user is created through the social flow.
    """

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.first_name:
            user.first_name = data.get("first_name") or data.get("given_name") or ""
        if not user.last_name:
            user.last_name = data.get("last_name") or data.get("family_name") or ""
        return user
