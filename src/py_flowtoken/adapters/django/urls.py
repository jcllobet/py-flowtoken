from django.urls import path

from .views import asset

app_name = "py_flowtoken"
urlpatterns = [path("<str:filename>", asset, name="asset")]
