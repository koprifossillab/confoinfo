from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search_all"),
    path("plan/", views.plan, name="plan_all"),
    path("settings/", views.settings_page, name="settings"),
    path("calendar.ics", views.calendar_ics, name="calendar_ics"),
    path("api/talks/", views.api_talks, name="api_talks"),
    path("healthz", views.healthz, name="healthz"),
    # 학회 하나. 위의 이름(search·plan·settings·api·healthz)과 겹치는 slug 는
    # 위가 먼저 잡는다 — loader.SLUG_RE 가 아니라 여기가 막는 자리다 (RESERVED)
    path("<slug:slug>/", views.program, name="program"),
    path("<slug:slug>/sessions/", views.sessions, name="sessions"),
    path("<slug:slug>/session/<str:code>/", views.session_detail, name="session_detail"),
    path("<slug:slug>/talk/<int:pk>/", views.talk_detail, name="talk_detail"),
    path("<slug:slug>/abstract/<int:pk>/", views.abstract_detail, name="abstract_detail"),
    path("<slug:slug>/search/", views.search, name="search"),
    path("<slug:slug>/plan/", views.plan, name="plan"),
]

# 학회 slug 로 쓰면 그 학회 화면이 위의 경로에 가려 안 열린다
RESERVED = {"search", "plan", "settings", "api", "healthz", "static", "calendar.ics"}
