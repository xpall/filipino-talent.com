import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from registry.models import Submission
User = get_user_model()


def submission_data(**overrides):
    data = {
        "subdomain": "juan-dela-cruz",
        "legal_name": "Juan Dela Cruz",
        "portfolio_url": "https://juan-dela-cruz.github.io",
        "github_username": "juan-dela-cruz",
        "record_type": "CNAME",
        "record_value": "juan-dela-cruz.github.io",
        "agree_to_terms": "on",
        "website": "",
    }
    data.update(overrides)
    return data


class PublicPageTests(TestCase):
    def test_public_pages_render(self):
        for url in [
            "/",
            "/guide",
            "/guide/connect",
            "/guide/github-pages",
            "/directory",
            "/terms",
            "/health",
            "/robots.txt",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_submit_requires_login(self):
        response = self.client.get("/submit")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {"APP": {"client_id": "test", "secret": "test", "key": ""}}
        }
    )
    def test_login_page_renders(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue with Google")

    def test_legacy_trailing_slashes_redirect_to_canonical_paths(self):
        for path, target in [
            ("/submit/", "/submit"),
            ("/submit/done/1/", "/submit/done/1"),
            ("/directory/", "/directory"),
            ("/guide/", "/guide"),
            ("/guide/connect/", "/guide/connect"),
            ("/terms/", "/terms"),
            ("/account/", "/account"),
            ("/dashboard/", "/dashboard"),
            ("/health/", "/health"),
            ("/api/domains/", "/api/domains"),
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], target)

    def test_trailing_slash_redirect_preserves_query(self):
        response = self.client.get("/directory/?q=juan&sort=az")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/directory?q=juan&sort=az")

    def test_accounts_urls_keep_their_trailing_slash(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

    def test_post_to_trailing_slash_uses_308(self):
        response = self.client.post("/submit/")
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response["Location"], "/submit")

    def test_directory_lists_live_subdomains(self):
        Submission.objects.create(
            subdomain="juan",
            portfolio_url="https://juan.github.io",
            record_type="CNAME",
            record_value="juan.github.io",
            status=Submission.Status.LIVE,
        )
        response = self.client.get("/directory")
        self.assertContains(response, "juan")

    def test_api_domains(self):
        Submission.objects.create(
            subdomain="juan",
            portfolio_url="https://juan.github.io",
            record_type="CNAME",
            record_value="juan.github.io",
            status=Submission.Status.LIVE,
        )
        response = self.client.get("/api/domains")
        payload = response.json()
        self.assertEqual(len(payload["domains"]), 1)
        self.assertEqual(payload["domains"][0]["subdomain"], "juan")
        self.assertNotIn("email", payload["domains"][0])


@override_settings(MAX_LIVE_PER_USER=2, MAX_PER_EMAIL_PER_DAY=3, MAX_PER_IP_PER_DAY=6)
class SubmitFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="juan@example.com",
            email="juan@example.com",
            password="not-used",
        )
        self.client.force_login(self.user)

    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_submit_publishes_immediately(self, upsert):
        response = self.client.post("/submit", submission_data())
        self.assertEqual(response.status_code, 302)
        submission = Submission.objects.get(subdomain="juan-dela-cruz")
        self.assertEqual(submission.status, Submission.Status.LIVE)
        self.assertEqual(submission.email, "juan@example.com")
        self.assertIsNotNone(submission.published_at)
        upsert.assert_called()
        self.assertIn("/submit/done/", response["Location"])

    def test_submit_form_renders_for_authenticated_user(self):
        response = self.client.get("/submit")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose your subdomain")
        self.assertContains(response, self.user.email)

    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_duplicate_active_subdomain_rejected(self, upsert):
        self.client.post("/submit", submission_data())
        response = self.client.post("/submit", submission_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)

    @override_settings(MAX_LIVE_PER_USER=1)
    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_live_limit(self, upsert):
        self.client.post("/submit", submission_data())
        response = self.client.post(
            "/submit",
            submission_data(
                subdomain="another-name",
                record_value="another.github.io",
                portfolio_url="https://another.github.io",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)

    @patch("registry.services.publish.cloudflare.delete_records", return_value=1)
    def test_release_subdomain(self, delete):
        submission = Submission.objects.create(
            user=self.user,
            subdomain="juan",
            legal_name="Juan",
            email=self.user.email,
            portfolio_url="https://juan.github.io",
            record_type="CNAME",
            record_value="juan.github.io",
            status=Submission.Status.LIVE,
        )
        response = self.client.post(f"/submissions/{submission.pk}/release")
        self.assertRedirects(response, "/account")
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.REMOVED)
        self.assertIsNotNone(submission.dns_cleaned_at)
        delete.assert_called_once()

    def test_account_only_shows_own_submissions(self):
        Submission.objects.create(
            user=self.user,
            subdomain="mine",
            portfolio_url="https://mine.github.io",
            record_type="CNAME",
            record_value="mine.github.io",
            status=Submission.Status.LIVE,
        )
        other = User.objects.create_user(
            username="other@example.com", email="other@example.com"
        )
        Submission.objects.create(
            user=other,
            subdomain="theirs",
            portfolio_url="https://theirs.github.io",
            record_type="CNAME",
            record_value="theirs.github.io",
            status=Submission.Status.LIVE,
        )
        response = self.client.get("/account")
        self.assertContains(response, "mine")
        self.assertNotContains(response, "theirs")

    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_retry_pending(self, upsert):
        submission = Submission.objects.create(
            user=self.user,
            subdomain="pending-name",
            legal_name="Juan",
            email=self.user.email,
            portfolio_url="https://pending.github.io",
            record_type="CNAME",
            record_value="pending.github.io",
            status=Submission.Status.PENDING,
        )
        response = self.client.post(f"/submit/{submission.pk}/retry")
        self.assertRedirects(response, f"/submit/done/{submission.pk}")
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.LIVE)

    def test_submit_done_hidden_from_other_users(self):
        submission = Submission.objects.create(
            user=self.user,
            subdomain="private",
            portfolio_url="https://private.github.io",
            record_type="CNAME",
            record_value="private.github.io",
            status=Submission.Status.LIVE,
        )
        other = User.objects.create_user(
            username="other@example.com", email="other@example.com"
        )
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/submit/done/{submission.pk}").status_code, 404)


@override_settings(ADMIN_EMAILS={"admin@example.com"})
class DashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@example.com", email="admin@example.com"
        )
        self.user = User.objects.create_user(
            username="juan@example.com", email="juan@example.com"
        )
        self.submission = Submission.objects.create(
            user=self.user,
            subdomain="juan",
            legal_name="Juan",
            email=self.user.email,
            portfolio_url="https://juan.github.io",
            record_type="CNAME",
            record_value="juan.github.io",
            status=Submission.Status.LIVE,
        )

    def test_dashboard_requires_admin(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/dashboard").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    @patch("registry.services.publish.cloudflare.delete_records", return_value=1)
    def test_admin_remove(self, delete):
        self.client.force_login(self.admin)
        response = self.client.post(f"/dashboard/{self.submission.pk}/remove")
        self.assertRedirects(response, "/dashboard")
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.REMOVED)

    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_admin_publish_pending(self, upsert):
        pending = Submission.objects.create(
            user=self.user,
            subdomain="pending",
            portfolio_url="https://pending.github.io",
            record_type="CNAME",
            record_value="pending.github.io",
            status=Submission.Status.PENDING,
        )
        self.client.force_login(self.admin)
        response = self.client.post(f"/dashboard/{pending.pk}/publish")
        self.assertRedirects(response, "/dashboard")
        pending.refresh_from_db()
        self.assertEqual(pending.status, Submission.Status.LIVE)


class SyncDnsTests(TestCase):
    @patch("registry.services.publish.cloudflare.upsert_record", return_value="created")
    def test_sync_publishes_pending(self, upsert):
        submission = Submission.objects.create(
            subdomain="pending",
            portfolio_url="https://pending.github.io",
            record_type="CNAME",
            record_value="pending.github.io",
            status=Submission.Status.PENDING,
        )
        call_command("sync_dns", stdout=io.StringIO(), stderr=io.StringIO())
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.LIVE)
        upsert.assert_called()

    @patch("registry.services.publish.cloudflare.delete_records", return_value=1)
    def test_sync_cleans_removed(self, delete):
        submission = Submission.objects.create(
            subdomain="removed",
            portfolio_url="https://removed.github.io",
            record_type="CNAME",
            record_value="removed.github.io",
            status=Submission.Status.REMOVED,
        )
        call_command("sync_dns", stdout=io.StringIO(), stderr=io.StringIO())
        submission.refresh_from_db()
        self.assertIsNotNone(submission.dns_cleaned_at)
        delete.assert_called_once()


class ImportLegacyTests(TestCase):
    def test_import_from_file(self):
        payload = {
            "domains": [
                {
                    "subdomain": "jeffreyjay",
                    "portfolio_url": "https://thejeffreyjay.github.io",
                    "github_username": "thejeffreyjay",
                    "record_type": "CNAME",
                    "record_value": "thejeffreyjay.github.io",
                    "status": "active",
                    "created_at": "2026-10-19T19:45:09.162Z",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "domains.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            call_command(
                "import_legacy",
                file=str(path),
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        submission = Submission.objects.get(subdomain="jeffreyjay")
        self.assertEqual(submission.status, Submission.Status.LIVE)
        self.assertIsNone(submission.user)
        self.assertEqual(submission.portfolio_url, "https://thejeffreyjay.github.io")
