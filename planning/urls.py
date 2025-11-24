from django.urls import path
from . import views

urlpatterns = [
    path("", views.planning_search, name="planning_search"),
    path("watch/", views.create_watch, name="create_watch"),
    path("watch/thanks/", views.watch_thanks, name="watch_thanks"),
    path("watches/", views.watch_list, name="watch_list"),
]