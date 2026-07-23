from .models import Cart, Wishlist


def _ensure_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    key = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=key, user__isnull=True)
    return cart


def get_wishlist(request):
    if request.user.is_authenticated:
        wl, _ = Wishlist.objects.get_or_create(user=request.user)
        return wl
    key = _ensure_session(request)
    wl, _ = Wishlist.objects.get_or_create(session_key=key, user__isnull=True)
    return wl


def merge_session_cart_into_user(request, user):
    """Called right after login — folds the anonymous session cart/wishlist into the user's."""
    session_key = request.session.session_key
    if not session_key:
        return
    session_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if session_cart:
        user_cart, _ = Cart.objects.get_or_create(user=user)
        for item in session_cart.items.all():
            existing = user_cart.items.filter(product=item.product).first()
            if existing:
                existing.qty += item.qty
                existing.save()
            else:
                item.cart = user_cart
                item.save()
        session_cart.delete()

    session_wl = Wishlist.objects.filter(session_key=session_key, user__isnull=True).first()
    if session_wl:
        user_wl, _ = Wishlist.objects.get_or_create(user=user)
        for p in session_wl.products.all():
            user_wl.products.add(p)
        session_wl.delete()
