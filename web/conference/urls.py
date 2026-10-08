from django.urls import path

from . import views

# **경로는 전부 파일로 구울 수 있어야 한다** — 쿼리 문자열로 갈리는 화면을 두지 않는다
# (build_site · 002). 슬래시로 끝나면 `…/index.html`, 아니면 그 이름의 파일이 된다.
urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search_all"),
    path("plan/", views.plan, name="plan_all"),
    path("settings/", views.settings_page, name="settings"),
    path("talks.json", views.talks_json, name="talks_all"),
    path("search.json", views.search_json, name="search_index_all"),
    path("404.html", views.not_found, name="not_found"),
    path("i18n/<str:lang>.json", views.i18n_json, name="i18n_all"),
    # 학회 하나. 위의 이름과 겹치는 slug 는 위가 먼저 잡는다 — loader 가 막는다 (RESERVED)
    path("<slug:slug>/", views.program, name="program"),
    path("<slug:slug>/day/<str:day>/", views.program, name="program_day"),
    path("<slug:slug>/sessions/", views.sessions, name="sessions"),
    path("<slug:slug>/session/<str:code>/", views.session_detail, name="session_detail"),
    path("<slug:slug>/talk/<int:pk>/", views.talk_detail, name="talk_detail"),
    path("<slug:slug>/talk/<int:pk>/talk.ics", views.talk_ics, name="talk_ics"),
    path("<slug:slug>/abstract/<int:pk>/", views.abstract_detail, name="abstract_detail"),
    path("<slug:slug>/search/", views.search, name="search"),
    path("<slug:slug>/plan/", views.plan, name="plan"),
    path("<slug:slug>/talks.json", views.talks_json, name="talks"),
    path("<slug:slug>/search.json", views.search_json, name="search_index"),
    path("<slug:slug>/i18n/<str:lang>.json", views.i18n_json, name="i18n"),
]

# 학회 slug 로 쓰면 그 학회 화면이 위의 경로에 가려 안 열린다 (static 은 정적 파일 자리)
RESERVED = {"search", "plan", "settings", "static", "talks.json", "search.json", "404.html", "i18n"}
