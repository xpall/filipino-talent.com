from __future__ import annotations

from django import forms

from registry.services.rules import (
    ALLOWED_CNAME,
    GH_USER_RE,
    RESERVED,
    is_https_url,
    is_reserved,
    is_valid_subdomain_label,
    normalize_subdomain,
    to_domain_doc,
    validate_domain,
)


class SubmitForm(forms.Form):
    subdomain = forms.CharField(
        max_length=63,
        widget=forms.TextInput(
            attrs={
                "id": "subdomain",
                "placeholder": "juan-dela-cruz",
                "autocomplete": "off",
                "pattern": "[a-z0-9]([a-z0-9-]*[a-z0-9])?",
                "aria-describedby": "subdomain-hint",
            }
        ),
    )
    legal_name = forms.CharField(
        max_length=200,
        min_length=2,
        widget=forms.TextInput(
            attrs={
                "id": "legalName",
                "placeholder": "Juan Dela Cruz",
                "autocomplete": "name",
                "aria-describedby": "legalName-hint",
            }
        ),
    )
    portfolio_url = forms.URLField(
        max_length=500,
        widget=forms.URLInput(
            attrs={
                "id": "portfolioUrl",
                "placeholder": "https://juan-dela-cruz.github.io",
                "aria-describedby": "portfolioUrl-hint",
            }
        ),
    )
    github_username = forms.CharField(
        max_length=39,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "githubUsername",
                "placeholder": "juan-dela-cruz",
                "autocomplete": "username",
            }
        ),
    )
    record_type = forms.ChoiceField(
        choices=[
            ("CNAME", "CNAME: point to a host (recommended)"),
            ("A", "A: IPv4 address"),
            ("AAAA", "AAAA: IPv6 address"),
            ("TXT", "TXT: text record"),
        ],
        initial="CNAME",
        widget=forms.Select(attrs={"id": "recordType"}),
    )
    record_value = forms.CharField(
        max_length=512,
        widget=forms.TextInput(
            attrs={
                "id": "recordValue",
                "placeholder": "juan-dela-cruz.github.io",
                "autocomplete": "off",
                "list": "targets",
                "aria-describedby": "target-hint target-warning",
            }
        ),
    )
    agree_to_terms = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={"id": "agreeToTerms", "aria-describedby": "terms-hint"}
        ),
        error_messages={"required": "Please confirm this before continuing."},
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"id": "website", "tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_cname = ALLOWED_CNAME

    def clean_subdomain(self):
        value = normalize_subdomain(self.cleaned_data["subdomain"])
        if not is_valid_subdomain_label(value):
            raise forms.ValidationError(
                "Use lowercase letters, numbers and hyphens only (1-63 characters)."
            )
        if is_reserved(value, RESERVED):
            raise forms.ValidationError("That subdomain is reserved.")
        return value

    def clean_portfolio_url(self):
        value = self.cleaned_data["portfolio_url"].strip()
        if not is_https_url(value):
            raise forms.ValidationError("Enter a full https:// URL.")
        return value

    def clean_github_username(self):
        value = (self.cleaned_data.get("github_username") or "").strip()
        if value and not GH_USER_RE.fullmatch(value):
            raise forms.ValidationError("Enter a valid GitHub username.")
        return value

    def clean_record_value(self):
        return self.cleaned_data["record_value"].strip()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Could not process this request. Please try again.")
        if self.errors:
            return cleaned

        doc = to_domain_doc(
            {
                "github_username": cleaned.get("github_username"),
                "portfolio_url": cleaned.get("portfolio_url"),
                "record_type": cleaned.get("record_type"),
                "record_value": cleaned.get("record_value"),
            }
        )
        for error in validate_domain(
            cleaned.get("subdomain", ""),
            doc,
            reserved=RESERVED,
            allowed_cname=ALLOWED_CNAME,
        ):
            self.add_error(None, error)
        return cleaned
