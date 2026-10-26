import time

import jwt
from django.test import SimpleTestCase
from jwt.algorithms import has_crypto

from allauth.socialaccount.internal.jwtkit import verify_and_decode


class SocialAccountDependencyTests(SimpleTestCase):
    """Guard the Google ID-token dependencies.

    django-allauth does not install PyJWT by default. Without the
    ``socialaccount`` extra, the Google callback fails with
    ``ModuleNotFoundError: No module named 'jwt'``.
    """

    def test_jwt_crypto_support_is_installed(self):
        import cryptography.x509  # noqa: F401

        self.assertTrue(has_crypto)
        self.assertTrue(jwt.__version__)

    def test_google_id_token_can_be_decoded(self):
        token = jwt.encode(
            {
                "iss": "https://accounts.google.com",
                "aud": "test-client",
                "exp": int(time.time()) + 300,
            },
            key="test-secret-key-that-is-32-bytes-long",
            algorithm="HS256",
        )
        data = verify_and_decode(
            credential=token,
            keys_url="https://example.invalid/keys",
            issuer="https://accounts.google.com",
            audience="test-client",
            lookup_kid=None,
            verify_signature=False,
        )
        self.assertEqual(data["aud"], "test-client")
