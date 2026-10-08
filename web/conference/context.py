from confoinfoweb.version import VERSION


def version(request):
    return {"version": VERSION}


def translations(request):
    """이 화면에 미리 번역해 둔 언어들 (006) — base.html 이 JS 에 넘긴다."""
    from . import enrich
    from .models import Conference
    m = getattr(request, "resolver_match", None)
    slug = (m.kwargs.get("slug") if m else None)
    slugs = [slug] if slug else list(Conference.objects.values_list("slug", flat=True))
    return {"tr_langs": sorted({lang for s in slugs for lang in enrich.languages(s)})}
