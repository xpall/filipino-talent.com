from django.urls import path

from . import views

urlpatterns = [
    path("directory", views.directory, name="directory"),
    path("api/domains", views.api_domains, name="api_domains"),
    path("submit", views.submit, name="submit"),
    path("submit/done/<int:pk>", views.submit_done, name="submit_done"),
    path("submit/<int:pk>/retry", views.retry_publish, name="retry_publish"),
    path("account", views.account, name="account"),
    path("submissions/<int:pk>/release", views.release_submission, name="release_submission"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("dashboard/<int:pk>/publish", views.dashboard_publish, name="dashboard_publish"),
    path("dashboard/<int:pk>/remove", views.dashboard_remove, name="dashboard_remove"),
    path("dashboard/<int:pk>/reject", views.dashboard_reject, name="dashboard_reject"),
]
