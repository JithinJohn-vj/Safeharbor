from django.urls import path

from . import views

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("session/<uuid:session_id>/", views.session_detail, name="session_detail"),
]
