from __future__ import annotations

import ipaddress
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from registry.forms import DirectoryEntryForm, SubmitForm
from registry.models import Submission
from registry.permissions import admin_required, is_admin
from registry.services.publish import PublishError, publish_submission, unpublish_submission
from registry.services.rules import connect_guide_for_target, normalize_subdomain


def client_ip(request) -> str | None:
    raw = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
        or ""
    )
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def directory(request):
    domains = Submission.objects.filter(status=Submission.Status.LIVE).order_by(
        "-published_at", "-created_at"
    )
    return render(
        request,
        "directory.html",
        {"domains": domains, "total": domains.count()},
    )


def api_domains(request):
    domains = Submission.objects.filter(status=Submission.Status.LIVE).order_by(
        "-published_at", "-created_at"
    )
    payload = {
        "domains": [
            {
                "subdomain": item.subdomain,
                "portfolio_url": item.portfolio_url,
                "github_username": item.github_username or None,
                "record_type": item.record_type,
                "record_value": item.record_value,
                "status": "active",
                "created_at": (item.published_at or item.created_at).isoformat().replace("+00:00", "Z"),
            }
            for item in domains
        ]
    }
    response = JsonResponse(payload)
    response["Cache-Control"] = "public, max-age=120"
    return response


def _rate_limit_error(request) -> str | None:
    since = timezone.now() - timedelta(hours=24)
    ip = client_ip(request)
    if ip and Submission.objects.filter(ip=ip, created_at__gte=since).count() >= settings.MAX_PER_IP_PER_DAY:
        return "Too many requests from this network today. Please try again tomorrow."
    if (
        Submission.objects.filter(
            email__iexact=request.user.email, created_at__gte=since
        ).count()
        >= settings.MAX_PER_EMAIL_PER_DAY
    ):
        return "Too many requests from this account today. Please try again tomorrow."
    active = Submission.objects.filter(
        user=request.user,
        status__in=[Submission.Status.PENDING, Submission.Status.LIVE],
    ).count()
    if active >= settings.MAX_LIVE_PER_USER:
        return (
            f"You already have {active} active subdomain"
            f"{'' if active == 1 else 's'} (the limit is {settings.MAX_LIVE_PER_USER}). "
            "Release one from your account before requesting another."
        )
    return None


@login_required
def submit(request):
    initial = {
        "legal_name": request.user.get_full_name() or "",
        "record_type": "CNAME",
    }
    if request.method == "POST":
        form = SubmitForm(request.POST)
        if form.is_valid():
            limited = _rate_limit_error(request)
            if limited:
                form.add_error(None, limited)
            else:
                subdomain = normalize_subdomain(form.cleaned_data["subdomain"])
                existing = Submission.objects.filter(
                    subdomain__iexact=subdomain,
                    status__in=[Submission.Status.PENDING, Submission.Status.LIVE],
                ).first()
                if existing:
                    if existing.is_owned_by(request.user) and existing.is_pending:
                        form.add_error(
                            None,
                            "You already have a pending request for this name. "
                            "Retry publishing it from your account.",
                        )
                    else:
                        form.add_error(None, f'"{subdomain}" has already been requested.')
                else:
                    submission = Submission(
                        user=request.user,
                        subdomain=subdomain,
                        legal_name=form.cleaned_data["legal_name"].strip(),
                        email=request.user.email,
                        portfolio_url=form.cleaned_data["portfolio_url"],
                        github_username=form.cleaned_data["github_username"],
                        record_type=form.cleaned_data["record_type"],
                        record_value=form.cleaned_data["record_value"],
                        status=Submission.Status.PENDING,
                        ip=client_ip(request),
                        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:1000],
                    )
                    try:
                        submission.save()
                    except IntegrityError:
                        form.add_error(None, f'"{subdomain}" has already been requested.')
                    else:
                        try:
                            publish_submission(submission)
                            messages.success(
                                request,
                                f"{subdomain}.{settings.ZONE} is live.",
                            )
                        except PublishError as exc:
                            submission.last_error = str(exc)
                            submission.save(update_fields=["last_error", "updated_at"])
                            messages.warning(
                                request,
                                "Your request was saved, but DNS publishing failed. "
                                "You can retry it from your account.",
                            )
                        return redirect("submit_done", pk=submission.pk)
    else:
        form = SubmitForm(initial=initial)

    return render(
        request,
        "submit.html",
        {"form": form, "allowed_cname": form.allowed_cname},
    )


def _submission_for_user(request, pk: int) -> Submission:
    submission = get_object_or_404(Submission, pk=pk)
    if not (submission.is_owned_by(request.user) or is_admin(request.user)):
        raise Http404
    return submission


def submit_done(request, pk: int):
    submission = _submission_for_user(request, pk)
    connect = (
        connect_guide_for_target(submission.record_value)
        if submission.record_type == "CNAME"
        else None
    )
    return render(
        request,
        "submit_done.html",
        {"submission": submission, "connect": connect},
    )


@login_required
@require_POST
def retry_publish(request, pk: int):
    submission = _submission_for_user(request, pk)
    if submission.status not in (Submission.Status.PENDING, Submission.Status.LIVE):
        messages.error(request, "This subdomain can no longer be published.")
        return redirect("account")
    try:
        publish_submission(submission)
        messages.success(request, f"{submission.subdomain}.{settings.ZONE} is live.")
    except PublishError as exc:
        submission.last_error = str(exc)
        submission.save(update_fields=["last_error", "updated_at"])
        messages.error(request, f"Could not publish the DNS record: {exc}")
    return redirect("submit_done", pk=submission.pk)


@login_required
def account(request):
    submissions = Submission.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request,
        "account/account.html",
        {"submissions": submissions},
    )


@login_required
@require_POST
def release_submission(request, pk: int):
    submission = _submission_for_user(request, pk)
    if submission.status in (Submission.Status.REMOVED, Submission.Status.REJECTED):
        messages.info(request, "That subdomain is already released.")
        return redirect("account")
    try:
        unpublish_submission(submission, Submission.Status.REMOVED)
        messages.success(
            request,
            f"{submission.subdomain}.{settings.ZONE} was released.",
        )
    except PublishError as exc:
        submission.last_error = str(exc)
        submission.save(update_fields=["last_error", "updated_at"])
        messages.error(request, f"Could not remove the DNS record: {exc}")
    return redirect("account")


@admin_required
def dashboard(request):
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    submissions = Submission.objects.select_related("user").order_by("-created_at")
    if status in Submission.Status.values:
        submissions = submissions.filter(status=status)
    if query:
        submissions = submissions.filter(
            Q(subdomain__icontains=query)
            | Q(email__icontains=query)
            | Q(legal_name__icontains=query)
            | Q(portfolio_url__icontains=query)
        )
    paginator = Paginator(submissions, 50)
    page = paginator.get_page(request.GET.get("page"))
    counts = {
        "live": Submission.objects.filter(status=Submission.Status.LIVE).count(),
        "pending": Submission.objects.filter(status=Submission.Status.PENDING).count(),
        "removed": Submission.objects.filter(status=Submission.Status.REMOVED).count(),
        "rejected": Submission.objects.filter(status=Submission.Status.REJECTED).count(),
    }
    return render(
        request,
        "dashboard/index.html",
        {
            "page": page,
            "status": status,
            "query": query,
            "counts": counts,
            "status_choices": Submission.Status.choices,
        },
    )


@admin_required
def dashboard_edit(request, pk: int):
    submission = get_object_or_404(Submission, pk=pk)
    if request.method == "POST":
        form = DirectoryEntryForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Updated the directory entry for {submission.subdomain}.{settings.ZONE}.",
            )
            return redirect("dashboard")
    else:
        form = DirectoryEntryForm(instance=submission)
    return render(
        request,
        "dashboard/edit.html",
        {"form": form, "submission": submission},
    )


@admin_required
@require_POST
def dashboard_publish(request, pk: int):
    submission = get_object_or_404(Submission, pk=pk)
    try:
        publish_submission(submission)
        messages.success(request, f"{submission.subdomain}.{settings.ZONE} is live.")
    except PublishError as exc:
        submission.last_error = str(exc)
        submission.save(update_fields=["last_error", "updated_at"])
        messages.error(request, f"Publish failed: {exc}")
    return redirect("dashboard")


@admin_required
@require_POST
def dashboard_remove(request, pk: int):
    submission = get_object_or_404(Submission, pk=pk)
    try:
        unpublish_submission(submission, Submission.Status.REMOVED)
        messages.success(request, f"{submission.subdomain}.{settings.ZONE} was removed.")
    except PublishError as exc:
        submission.last_error = str(exc)
        submission.save(update_fields=["last_error", "updated_at"])
        messages.error(request, f"Remove failed: {exc}")
    return redirect("dashboard")


@admin_required
@require_POST
def dashboard_reject(request, pk: int):
    submission = get_object_or_404(Submission, pk=pk)
    try:
        unpublish_submission(submission, Submission.Status.REJECTED)
        messages.success(request, f"{submission.subdomain}.{settings.ZONE} was rejected.")
    except PublishError as exc:
        submission.last_error = str(exc)
        submission.save(update_fields=["last_error", "updated_at"])
        messages.error(request, f"Reject failed: {exc}")
    return redirect("dashboard")
