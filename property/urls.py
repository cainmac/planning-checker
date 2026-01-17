from django.urls import path
from . import views

app_name = "property"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("searches/", views.search_list, name="search_list"),
    path("searches/new/", views.search_create, name="search_create"),
    path("searches/<int:pk>/edit/", views.search_edit, name="search_edit"),
    path("searches/<int:pk>/delete/", views.search_delete, name="search_delete"),

    path("listings/", views.listings_inbox, name="listings_inbox"),
    path("shortlist/", views.shortlist, name="shortlist"),
    path("shortlist/<int:listing_id>/add/", views.shortlist_add, name="shortlist_add"),
    path("shortlist/<int:listing_id>/remove/", views.shortlist_remove, name="shortlist_remove"),

    path("webhooks/inbound-email/", views.inbound_email_webhook, name="inbound_email_webhook"),
]
