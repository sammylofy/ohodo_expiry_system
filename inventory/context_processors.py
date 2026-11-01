from .models import StoreProfile


def store_profile_context(request):
    """Injects singleton StoreProfile and store_name into every template."""
    try:
        profile = StoreProfile.get_solo()
        return {
            'store_profile': profile,
            'store_name': profile.store_name,
        }
    except Exception:
        return {
            'store_profile': None,
            'store_name': 'Ohodo Retail Store',
        }