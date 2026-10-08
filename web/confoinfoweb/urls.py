from django.urls import include, path

urlpatterns = [
    path("", include("conference.urls")),
]
