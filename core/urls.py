from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("guide", views.guide_index, name="guide"),
    path("guide/connect", views.guide_connect, name="guide_connect"),
    path("guide/<slug:slug>", views.guide_page, name="guide_page"),
    path("terms", views.terms, name="terms"),
    path("health", views.health, name="health"),
    path("robots.txt", views.robots, name="robots"),
]
