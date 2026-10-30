from django.urls import include, path

urlpatterns = [path("widgets/flowtoken/", include("py_flowtoken.adapters.django.urls"))]
