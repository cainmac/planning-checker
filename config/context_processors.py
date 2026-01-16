from django.conf import settings

def branding(request):
    return {
        "BRAND_NAME": settings.BRAND_NAME,
        "BRAND_TAGLINE": settings.BRAND_TAGLINE,
        "BRAND_SHORT_NAME": settings.BRAND_SHORT_NAME,
    }
