from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.index),
    path("stream", views.stream, name="stream"),
    path("flowtoken/", include("py_flowtoken.adapters.django.urls")),
]
