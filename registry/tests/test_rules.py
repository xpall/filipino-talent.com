from django.test import SimpleTestCase

from registry.services.rules import (
    connect_guide_for_target,
    is_ipv4,
    is_ipv6,
    is_reserved,
    is_valid_subdomain_label,
    match_allowed_suffix,
    normalize_subdomain,
    to_cloudflare_records,
    validate_domain,
)


def doc(record_type="CNAME", value="juan.github.io", **extra):
    record = {"value": value}
    record.update(extra)
    return {
        "owner": {"github": "juan", "portfolio": "https://juan.github.io"},
        "records": {record_type: record},
    }


class RulesTests(SimpleTestCase):
    def test_normalize_subdomain(self):
        self.assertEqual(normalize_subdomain("  Juan-Dela-Cruz "), "juan-dela-cruz")

    def test_subdomain_validation(self):
        self.assertTrue(is_valid_subdomain_label("juan-dela-cruz"))
        self.assertTrue(is_valid_subdomain_label("a"))
        self.assertFalse(is_valid_subdomain_label("-juan"))
        self.assertFalse(is_valid_subdomain_label("juan-"))
        self.assertFalse(is_valid_subdomain_label("Juan"))
        self.assertFalse(is_valid_subdomain_label("a" * 64))

    def test_reserved(self):
        self.assertTrue(is_reserved("admin"))
        self.assertTrue(is_reserved("api"))
        self.assertTrue(is_reserved("filipino-talent"))
        self.assertFalse(is_reserved("my-portfolio"))

    def test_allowed_suffix(self):
        self.assertTrue(match_allowed_suffix("juan.github.io"))
        self.assertTrue(match_allowed_suffix("project.pages.dev"))
        self.assertFalse(match_allowed_suffix("example.com"))

    def test_ip_validation(self):
        self.assertTrue(is_ipv4("203.0.113.10"))
        self.assertFalse(is_ipv4("999.1.1.1"))
        self.assertTrue(is_ipv6("2001:db8::1"))
        self.assertFalse(is_ipv6("not-an-ip"))

    def test_valid_cname_document(self):
        self.assertEqual(validate_domain("juan", doc()), [])

    def test_cname_backreference_and_suffix(self):
        errors = validate_domain("juan", doc(value="juan.filipino-talent.com"))
        self.assertTrue(any("must not point back" in error for error in errors))

        errors = validate_domain("juan", doc(value="example.com"))
        self.assertTrue(any("not an allowed target" in error for error in errors))

    def test_proxied_cname_rejected(self):
        errors = validate_domain("juan", doc(proxied=True))
        self.assertTrue(any("cannot be proxied" in error for error in errors))

    def test_ip_record_validation(self):
        self.assertEqual(validate_domain("juan", doc("A", "203.0.113.10")), [])
        self.assertTrue(validate_domain("juan", doc("A", "not-an-ip")))
        self.assertEqual(validate_domain("juan", doc("AAAA", "2001:db8::1")), [])

    def test_reserved_and_invalid_names(self):
        self.assertTrue(validate_domain("admin", doc()))
        self.assertTrue(validate_domain("Bad_Name", doc()))

    def test_cloudflare_records(self):
        records = to_cloudflare_records("juan", doc(), "filipino-talent.com")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "juan.filipino-talent.com")
        self.assertEqual(records[0]["comment"], "managed-by:filipino-talent")
        self.assertFalse(records[0]["proxied"])

    def test_connect_guide_mapping(self):
        self.assertEqual(connect_guide_for_target("juan.github.io")["label"], "GitHub Pages")
        self.assertEqual(connect_guide_for_target("x.pages.dev")["anchor"], "cloudflare-pages")
        self.assertIsNone(connect_guide_for_target("example.com"))
