from django.urls import path
from . import views

urlpatterns = [
    path("", views.planning_search, name="planning_search"),
    path("watches/", views.watch_list, name="watch_list"),
    path("watch/thanks/", views.watch_thanks, name="watch_thanks"),
    path("alert/", views.create_alert, name="planning_create_alert"),
]
