from .cartutils import get_cart, get_wishlist
from .models import Brand, Category, SiteSettings


def site_context(request):
    settings_obj = SiteSettings.load()
    categories = Category.objects.prefetch_related("subcategories").all()

    cart_count = 0
    wishlist_count = 0
    try:
        cart_count = get_cart(request).count()
        wishlist_count = get_wishlist(request).products.count()
    except Exception:
        pass

    return {
        "site_settings": settings_obj,
        "nav_categories": categories,
        "nav_brands": Brand.objects.all()[:6],
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
    }
