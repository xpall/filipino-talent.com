from django.test import SimpleTestCase

from registry.forms import SubmitForm


def form_data(**overrides):
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


class SubmitFormTests(SimpleTestCase):
    def test_valid_form(self):
        form = SubmitForm(data=form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_terms_required(self):
        form = SubmitForm(data=form_data(agree_to_terms=""))
        self.assertFalse(form.is_valid())
        self.assertIn("agree_to_terms", form.errors)

    def test_https_required(self):
        form = SubmitForm(data=form_data(portfolio_url="http://example.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("portfolio_url", form.errors)

    def test_invalid_subdomain(self):
        form = SubmitForm(data=form_data(subdomain="juan_dela"))
        self.assertFalse(form.is_valid())
        self.assertIn("subdomain", form.errors)

    def test_reserved_subdomain(self):
        form = SubmitForm(data=form_data(subdomain="admin"))
        self.assertFalse(form.is_valid())
        self.assertIn("subdomain", form.errors)

    def test_unsupported_cname(self):
        form = SubmitForm(data=form_data(record_value="example.com"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_honeypot(self):
        form = SubmitForm(data=form_data(website="https://spam.example"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_a_record(self):
        form = SubmitForm(
            data=form_data(
                record_type="A",
                record_value="203.0.113.10",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
