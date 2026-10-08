from confoinfoweb.version import VERSION


def version(request):
    return {"version": VERSION}
