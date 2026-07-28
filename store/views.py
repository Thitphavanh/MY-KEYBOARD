import csv
import io
from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout, views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Max, Min, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .cartutils import get_cart, get_wishlist, merge_session_cart_into_user
from .forms import CheckoutForm, PaymentForm, ProfileForm, RegisterForm
from .models import (
    BankAccount, Banner, Brand, CARRIER_FEES, Coupon, Order, OrderItem, OrderStatus,
    Product, SiteSettings, User, Category, SubCategory, ProductImage,
)

STAT_DEFS = {
    "members": {"label": "ສະມາຊິກຮ້ານເຮົາ", "icon": "user"},
    "sales": {"label": "ຍອດຂາຍລວມ", "icon": "chart"},
    "completedOrders": {"label": "ອໍເດີສຳເລັດ", "icon": "check"},
    "totalOrders": {"label": "ອໍເດີທັງໝົດ", "icon": "truck"},
    "products": {"label": "ສິນຄ້າທັງໝົດ", "icon": "grid"},
}


def _compute_stat_raw(key, settings_obj):
    if key == "members":
        return User.objects.count()
    if key == "sales":
        live_sum = Order.objects.aggregate(s=Sum("total"))["s"] or 0
        return live_sum + settings_obj.sales_adjustment
    if key == "completedOrders":
        return Order.objects.filter(status=OrderStatus.DELIVERED).count()
    if key == "totalOrders":
        return Order.objects.count()
    if key == "products":
        return Product.objects.count()
    return 0


def _store_stats(settings_obj):
    if not settings_obj.stats_enabled:
        return []
    slots = [
        (settings_obj.stat_metric_1, settings_obj.stat_override_1),
        (settings_obj.stat_metric_2, settings_obj.stat_override_2),
        (settings_obj.stat_metric_3, settings_obj.stat_override_3),
    ]
    stats = []
    for key, override in slots:
        if not key or key not in STAT_DEFS:
            continue
        raw = override if override is not None else _compute_stat_raw(key, settings_obj)
        stats.append({
            "key": key,
            "label": STAT_DEFS[key]["label"],
            "icon": STAT_DEFS[key]["icon"],
            "is_currency": key == "sales",
            "value": max(raw, 0),
        })
    return stats


def home(request):
    settings_obj = SiteSettings.load()
    active_cat = request.GET.get("cat", "all")
    search_term = request.GET.get("search", "").strip()
    sort = request.GET.get("sort", "default")

    products = Product.objects.select_related("category", "brand").prefetch_related("images")
    if active_cat != "all":
        products = products.filter(category_id=active_cat)
    else:
        products = products.filter(featured=True)
    if search_term:
        products = products.filter(Q(name__icontains=search_term) | Q(brand__name__icontains=search_term))

    if sort == "price-asc":
        products = products.order_by("price")
    elif sort == "price-desc":
        products = products.order_by("-price")
    elif sort == "rating":
        products = products.order_by("-rating")

    wishlist_ids = set(get_wishlist(request).products.values_list("pk", flat=True))

    context = {
        "banners": Banner.objects.all(),
        "stats": _store_stats(settings_obj),
        "best_sellers": Product.objects.filter(best_seller=True)[:8],
        "new_arrivals": Product.objects.filter(is_new=True)[:8],
        "products": products,
        "result_count": products.count(),
        "active_cat": active_cat,
        "search_term": search_term,
        "sort": sort,
        "wishlist_ids": wishlist_ids,
    }
    return render(request, "store/index.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    search_term = request.GET.get("search", "").strip()
    sort = request.GET.get("sort", "default")
    brand_ids = [b for b in request.GET.getlist("brand") if b.strip()]

    sub_param = request.GET.get("sub", "").strip()
    selected_subcategory = None
    if sub_param.isdigit():
        selected_subcategory = category.subcategories.filter(pk=sub_param).first()

    all_products = Product.objects.select_related("category", "brand").prefetch_related("images").filter(category=category)

    products = all_products
    if selected_subcategory:
        products = products.filter(subcategory=selected_subcategory)

    price_bounds = products.aggregate(lo=Min("price"), hi=Max("price"))
    price_min = price_bounds["lo"] or 0
    price_max = price_bounds["hi"] or 0

    min_price_param = request.GET.get("min_price", "").strip()
    max_price_param = request.GET.get("max_price", "").strip()
    selected_min = int(min_price_param) if min_price_param.isdigit() else price_min
    selected_max = int(max_price_param) if max_price_param.isdigit() else price_max

    if search_term:
        products = products.filter(Q(name__icontains=search_term) | Q(brand__name__icontains=search_term))

    if selected_subcategory:
        brands = Brand.objects.filter(products__subcategory=selected_subcategory).distinct()
    else:
        brands = Brand.objects.filter(products__category=category).distinct()

    if brand_ids:
        products = products.filter(brand_id__in=brand_ids)

    if min_price_param.isdigit():
        products = products.filter(price__gte=selected_min)
    if max_price_param.isdigit():
        products = products.filter(price__lte=selected_max)

    if sort == "price-asc":
        products = products.order_by("price")
    elif sort == "price-desc":
        products = products.order_by("-price")
    elif sort == "rating":
        products = products.order_by("-rating")

    wishlist_ids = set(get_wishlist(request).products.values_list("pk", flat=True))

    grouped_subcategories = []
    if not selected_subcategory and category.subcategories.exists():
        prod_list = list(products)
        subcats = category.subcategories.all()
        for sub in subcats:
            sub_prods = [p for p in prod_list if p.subcategory_id == sub.pk]
            if sub_prods:
                grouped_subcategories.append({
                    "subcategory": sub,
                    "products": sub_prods,
                })
        uncategorized = [p for p in prod_list if p.subcategory_id is None]
        if uncategorized:
            grouped_subcategories.append({
                "subcategory": None,
                "name": "ສິນຄ້າອື່ນໆ",
                "products": uncategorized,
            })

    context = {
        "category": category,
        "products": products,
        "grouped_subcategories": grouped_subcategories,
        "result_count": products.count(),
        "search_term": search_term,
        "sort": sort,
        "brands": brands,
        "selected_brand_ids": brand_ids,
        "selected_subcategory": selected_subcategory,
        "price_min": price_min,
        "price_max": price_max,
        "selected_min": selected_min,
        "selected_max": selected_max,
        "wishlist_ids": wishlist_ids,
    }
    return render(request, "store/category.html", context)


def search_suggest(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        products = Product.objects.filter(name__icontains=query).select_related("brand")[:6]
        results = [
            {
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": str(p.price),
                "image": p.first_image or "",
            }
            for p in products
        ]
    return JsonResponse({"results": results})


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category", "brand").prefetch_related("images"), pk=pk)
    wishlist = get_wishlist(request)
    related = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:4]
    context = {
        "product": product,
        "in_wishlist": wishlist.products.filter(pk=product.pk).exists(),
        "related": related,
    }
    return render(request, "store/product_detail.html", context)


def cart_view(request):
    cart = get_cart(request)
    context = {
        "cart": cart,
        "items": cart.items_detailed(),
        "subtotal": cart.subtotal(),
        "discount": cart.discount(),
        "total": cart.total(),
    }
    return render(request, "store/cart.html", context)


def cart_add(request, pk):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        qty = max(int(request.POST.get("qty", 1) or 1), 1)
        cart = get_cart(request)
        item, created = cart.items.get_or_create(product=product, defaults={"qty": qty})
        if not created:
            item.qty += qty
            item.save()
        message = f"ເພີ່ມ {product.name} ລົງກະຕ່າແລ້ວ"
        if is_ajax:
            return JsonResponse({"success": True, "message": message, "cart_count": cart.count()})
        messages.success(request, message)
    return redirect(request.POST.get("next") or "cart")


def cart_update(request, pk):
    if request.method == "POST":
        cart = get_cart(request)
        qty = int(request.POST.get("qty", 1) or 0)
        item = cart.items.filter(product_id=pk).first()
        if item:
            if qty <= 0:
                item.delete()
            else:
                item.qty = qty
                item.save()
    return redirect("cart")


def cart_remove(request, pk):
    if request.method == "POST":
        get_cart(request).items.filter(product_id=pk).delete()
    return redirect("cart")


def cart_apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        coupon = Coupon.objects.filter(code=code, active=True).first()
        cart = get_cart(request)
        if coupon:
            from django.utils import timezone
            # Check expiration date
            if coupon.valid_until and coupon.valid_until < timezone.now():
                messages.error(request, "ໂຄ້ດສ່ວນຫຼຸດນີ້ໝົດອາຍຸແລ້ວ")
            # Check maximum uses limit
            elif coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
                messages.error(request, "ໂຄ້ດສ່ວນຫຼຸດນີ້ຖືກໃຊ້ຄົບຈຳນວນແລ້ວ")
            else:
                cart.coupon = coupon
                cart.save()
                messages.success(request, f"ໃຊ້ຄູປອງ {coupon.label} ແລ້ວ")
        else:
            messages.error(request, "ໂຄ້ດສ່ວນຫຼຸດບໍ່ຖືກຕ້ອງ")
    return redirect("cart")


def cart_remove_coupon(request):
    cart = get_cart(request)
    cart.coupon = None
    cart.save()
    return redirect("cart")


def wishlist_view(request):
    wl = get_wishlist(request)
    products = wl.products.all()
    context = {"products": products, "wishlist_ids": set(products.values_list("pk", flat=True))}
    return render(request, "store/wishlist.html", context)


def wishlist_toggle(request, pk):
    if request.method == "POST":
        wl = get_wishlist(request)
        product = get_object_or_404(Product, pk=pk)
        if wl.products.filter(pk=product.pk).exists():
            wl.products.remove(product)
            messages.info(request, "ນຳອອກຈາກລາຍການທີ່ມັກແລ້ວ")
        else:
            wl.products.add(product)
            messages.success(request, "ເພີ່ມລົງລາຍການທີ່ມັກແລ້ວ")
    return redirect(request.POST.get("next") or "wishlist")


@login_required
def checkout_view(request):
    cart = get_cart(request)
    if not cart.items.exists():
        messages.error(request, "ກະຕ່າສິນຄ້າຫວ່າງເປົ່າ")
        return redirect("cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = cart.subtotal()
            order.discount = cart.discount()
            order.shipping_fee = CARRIER_FEES.get(order.carrier, 0)
            order.total = cart.total() + order.shipping_fee
            
            if cart.coupon:
                order.coupon_code = cart.coupon.code
                cart.coupon.uses_count += 1
                cart.coupon.save()
            else:
                order.coupon_code = ""
                
            order.status = OrderStatus.PENDING
            order.save()
            
            # Auto-save shipping details back to the user profile
            u = request.user
            u.first_name = order.shipping_name
            u.phone = order.shipping_phone
            u.province = order.shipping_province
            u.city = order.shipping_city
            u.address = order.shipping_village
            u.save()
            
            for detail in cart.items_detailed():
                OrderItem.objects.create(
                    order=order, product=detail["product"], product_name=detail["product"].name,
                    unit_price=detail["product"].price, qty=detail["item"].qty,
                )
            cart.items.all().delete()
            cart.coupon = None
            cart.save()
            request.session["pending_order_id"] = order.id
            return redirect("payment")
    else:
        u = request.user
        form = CheckoutForm(initial={
            "shipping_name": u.first_name, "shipping_phone": u.phone,
            "shipping_province": u.province, "shipping_city": u.city, "shipping_village": u.address,
        })

    context = {
        "form": form, "cart": cart, "items": cart.items_detailed(),
        "subtotal": cart.subtotal(), "discount": cart.discount(), "total": cart.total(),
        "carrier_fees": {c.value: fee for c, fee in CARRIER_FEES.items()},
    }
    return render(request, "store/checkout.html", context)


def _notify_admin_new_order(order, request=None):
    settings_obj = SiteSettings.load()
    to_email = settings_obj.admin_notify_email
    if not to_email:
        return

    def abs_url(path):
        return request.build_absolute_uri(path) if request is not None else path

    items_data = []
    for item in order.items.all():
        product_url = abs_url(item.product.get_absolute_url()) if item.product else None
        image_url = abs_url(item.product.first_image) if item.product and item.product.first_image else None
        items_data.append({"item": item, "product_url": product_url, "image_url": image_url})

    context = {
        "order": order,
        "items_data": items_data,
        "admin_url": abs_url(reverse("admin_order_detail", args=[order.pk])),
        "store_name": settings_obj.store_name,
    }
    html_message = render_to_string("store/email/order_notification.html", context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=f"[{settings_obj.store_name}] ອໍເດີ້ໃໝ່ #{order.order_number}",
            message=plain_message,
            from_email=None,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception:
        pass


@login_required
def payment_view(request):
    order_id = request.session.get("pending_order_id")
    order = get_object_or_404(Order, pk=order_id, user=request.user) if order_id else None
    if not order:
        return redirect("orders")

    if request.method == "POST":
        form = PaymentForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            order.status = OrderStatus.PREPARING
            order.save()
            del request.session["pending_order_id"]
            _notify_admin_new_order(order, request=request)
            messages.success(request, "ສົ່ງຂໍ້ມູນການຊຳລະເງິນແລ້ວ ຂອບໃຈທີ່ໃຊ້ບໍລິການ")
            return redirect("order_detail", pk=order.pk)
    else:
        form = PaymentForm(instance=order)

    return render(request, "store/payment.html", {"form": form, "order": order, "banks": BankAccount.objects.all()})


def orders_view(request):
    query = request.GET.get("q", "").strip()
    orders = None
    searched = bool(query)

    if query:
        order_pk = None
        digits = query.upper().replace("NB", "").lstrip("0")
        if digits.isdigit():
            order_pk = int(digits)
        orders = Order.objects.filter(
            Q(pk=order_pk) | Q(shipping_phone__icontains=query)
        ).prefetch_related("items")
    elif request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).prefetch_related("items")

    return render(request, "store/orders.html", {"orders": orders, "query": query, "searched": searched})


def order_detail_view(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    is_owner = request.user.is_authenticated and order.user_id == request.user.id
    is_admin = request.user.is_authenticated and request.user.is_admin
    if not (is_owner or is_admin):
        return redirect("orders")
    return render(request, "store/order_detail.html", {"order": order})


class NexbytePasswordResetView(auth_views.PasswordResetView):
    def form_valid(self, form):
        self.extra_email_context = {"site_settings": SiteSettings.load()}
        return super().form_valid(form)


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    if request.user.is_authenticated:
        if not next_url:
            next_url = "admin_dashboard" if request.user.is_staff else "home"
        return redirect(next_url)
    error = None
    if request.method == "POST":
        email_or_username = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        
        # Try to authenticate using the input as the username
        user = authenticate(request, username=email_or_username, password=password)
        
        # If it fails, try to find the user by email first and then authenticate using their username
        if not user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                db_user = User.objects.filter(email=email_or_username).first()
                if db_user:
                    user = authenticate(request, username=db_user.username, password=password)
            except Exception:
                pass
                
        if user:
            login(request, user)
            merge_session_cart_into_user(request, user)
            if not next_url:
                next_url = "admin_dashboard" if user.is_staff else "home"
            return redirect(next_url)
        error = "ອີເມວ/ຊື່ຜູ້ໃຊ້ ຫຼື ລະຫັດຜ່ານບໍ່ຖືກຕ້ອງ"
    return render(request, "store/login.html", {"error": error, "next": next_url or ""})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            merge_session_cart_into_user(request, user)
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "store/register.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "ບັນທຶກໂປຣໄຟລ໌ແລ້ວ")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "store/profile.html", {"form": form})


def contact_view(request):
    return render(request, "store/contact.html")


@login_required(login_url='login')
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "ທ່ານບໍ່ມີສິດເຂົ້າເຖິງໜ້ານີ້")
        return redirect("home")
    orders = Order.objects.all()
    today = timezone.now().date()
    now = timezone.now()

    revenue_this_month = Order.objects.filter(
        created_at__year=now.year, created_at__month=now.month
    ).aggregate(s=Sum("total"))["s"] or 0

    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    chart = []
    for d in days:
        total = Order.objects.filter(created_at__date=d).aggregate(s=Sum("total"))["s"] or 0
        chart.append({"label": d.strftime("%a %d/%m"), "total": total})
    max_total = max([c["total"] for c in chart] + [1])
    for c in chart:
        c["height"] = max(round(c["total"] / max_total * 150), 4) if c["total"] else 3

    context = {
        "total_members": User.objects.count(),
        "revenue_this_month": revenue_this_month,
        "total_orders": orders.count(),
        "pending_orders": orders.filter(status__in=[OrderStatus.PENDING, OrderStatus.PREPARING]).count(),
        "chart": chart,
        "recent_orders": orders[:5],
    }
    return render(request, "store/dashboard.html", context)


# ==============================================================================
# CUSTOM BACKOFFICE CRUD VIEW FUNCTIONS
# ==============================================================================

from .forms import ProductForm, CategoryForm, SubCategoryForm, BrandForm, BannerForm, BankAccountForm, SiteSettingsForm, CouponForm

# Helper decorator for checking staff
def staff_required(view_func):
    @login_required(login_url='login')
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "ທ່ານບໍ່ມີສິດເຂົ້າເຖິງໜ້ານີ້")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ----------------- PRODUCT CRUD -----------------

@staff_required
def admin_product_list(request):
    query = request.GET.get('q', '')
    cat_slug = request.GET.get('category', '')
    
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(desc__icontains=query))
    if cat_slug:
        products = products.filter(category_id=cat_slug)
        
    categories = Category.objects.all()
    context = {
        "products": products,
        "categories": categories,
        "query": query,
        "selected_category": cat_slug,
        "active_sub": "products",
    }
    return render(request, "store/admin_product_list.html", context)

@staff_required
def admin_product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            # Handle multiple product image uploads
            images = request.FILES.getlist('new_images')
            for img in images:
                ProductImage.objects.create(product=product, image=img)
            # Handle image links entered instead of file uploads
            image_urls = request.POST.getlist('new_image_urls')
            for url in image_urls:
                url = url.strip()
                if url:
                    ProductImage.objects.create(product=product, image_url=url)
            messages.success(request, "ເພີ່ມສິນຄ້າສຳເລັດແລ້ວ")
            if "again" in request.POST:
                return redirect(f"{reverse('admin_product_create')}?prefill={product.pk}")
            return redirect("admin_product_list")
    else:
        initial = None
        prefill_id = request.GET.get("prefill")
        if prefill_id:
            prefill_product = Product.objects.filter(pk=prefill_id).first()
            if prefill_product:
                initial = {
                    "name": prefill_product.name,
                    "brand": prefill_product.brand_id,
                    "category": prefill_product.category_id,
                    "subcategory": prefill_product.subcategory_id,
                    "price": prefill_product.price,
                    "old_price": prefill_product.old_price,
                    "stock": prefill_product.stock,
                    "is_preorder": prefill_product.is_preorder,
                    "icon": prefill_product.icon,
                    "tag": prefill_product.tag,
                    "desc": prefill_product.desc,
                    "featured": prefill_product.featured,
                    "best_seller": prefill_product.best_seller,
                    "is_new": prefill_product.is_new,
                    "source_link": prefill_product.source_link,
                    "specs_raw": "\n".join(prefill_product.specs) if isinstance(prefill_product.specs, list) else "",
                }
        form = ProductForm(initial=initial)

    context = {
        "form": form,
        "title": "ເພີ່ມສິນຄ້າໃໝ່",
        "active_sub": "products",
        "subcategories": SubCategory.objects.select_related("category").all(),
    }
    return render(request, "store/admin_product_form.html", context)


IMPORT_CSV_COLUMNS = [
    "name", "category", "subcategory", "brand", "price", "old_price", "stock",
    "desc", "tag", "icon", "specs", "image_urls", "featured", "best_seller", "is_new", "source_link",
]


def _parse_bool(value, default=False):
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "ແມ່ນ", "ใช่")


@staff_required
def admin_product_import(request):
    results = None
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "ກະລຸນາເລືອກໄຟລ໌ CSV")
        else:
            try:
                decoded = csv_file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                decoded = None
                messages.error(request, "ອ່ານໄຟລ໌ບໍ່ໄດ້ — ກະລຸນາບັນທຶກເປັນ CSV (UTF-8) ແລ້ວລອງໃໝ່")
            if decoded is not None:
                reader = csv.DictReader(io.StringIO(decoded))
                created = 0
                errors = []
                for i, row in enumerate(reader, start=2):  # row 1 is the header
                    name = (row.get("name") or "").strip()
                    category_key = (row.get("category") or "").strip()
                    price_raw = (row.get("price") or "").strip()
                    if not name or not category_key or not price_raw:
                        errors.append(f"ແຖວ {i}: ຂາດ name/category/price")
                        continue
                    category = Category.objects.filter(
                        Q(slug__iexact=category_key) | Q(name__iexact=category_key)
                    ).first()
                    if not category:
                        errors.append(f"ແຖວ {i}: ບໍ່ພົບໝວດໝູ່ '{category_key}'")
                        continue
                    try:
                        price = int(float(price_raw))
                    except ValueError:
                        errors.append(f"ແຖວ {i}: ລາຄາບໍ່ຖືກຕ້ອງ '{price_raw}'")
                        continue

                    old_price_raw = (row.get("old_price") or "").strip()
                    old_price = None
                    if old_price_raw:
                        try:
                            old_price = int(float(old_price_raw))
                        except ValueError:
                            errors.append(f"ແຖວ {i}: ລາຄາເກົ່າບໍ່ຖືກຕ້ອງ '{old_price_raw}'")
                            continue

                    stock_raw = (row.get("stock") or "").strip()
                    try:
                        stock = int(float(stock_raw)) if stock_raw else 0
                    except ValueError:
                        stock = 0

                    subcategory = None
                    sub_key = (row.get("subcategory") or "").strip()
                    if sub_key:
                        subcategory = category.subcategories.filter(name__iexact=sub_key).first()

                    brand = None
                    brand_key = (row.get("brand") or "").strip()
                    if brand_key:
                        brand, _ = Brand.objects.get_or_create(name=brand_key)

                    specs_raw = (row.get("specs") or "").strip()
                    specs = [s.strip() for s in specs_raw.split("|") if s.strip()]

                    with transaction.atomic():
                        product = Product.objects.create(
                            name=name,
                            category=category,
                            subcategory=subcategory,
                            brand=brand,
                            price=price,
                            old_price=old_price,
                            stock=stock,
                            desc=(row.get("desc") or "").strip(),
                            tag=(row.get("tag") or "").strip(),
                            icon=(row.get("icon") or "").strip() or "💻",
                            specs=specs,
                            featured=_parse_bool(row.get("featured"), default=True),
                            best_seller=_parse_bool(row.get("best_seller"), default=False),
                            is_new=_parse_bool(row.get("is_new"), default=False),
                            source_link=(row.get("source_link") or "").strip(),
                        )
                        image_urls_raw = (row.get("image_urls") or "").strip()
                        for url in [u.strip() for u in image_urls_raw.split("|") if u.strip()]:
                            ProductImage.objects.create(product=product, image_url=url)
                    created += 1

                results = {"created": created, "errors": errors}
                if created and not errors:
                    messages.success(request, f"ນຳເຂົ້າສິນຄ້າສຳເລັດ {created} ລາຍການ")
                elif created:
                    messages.warning(request, f"ນຳເຂົ້າສຳເລັດ {created} ລາຍການ, ມີ {len(errors)} ແຖວຜິດພາດ")
                elif not errors:
                    messages.error(request, "ໄຟລ໌ CSV ບໍ່ມີຂໍ້ມູນ")

    context = {
        "active_sub": "products",
        "results": results,
        "columns": IMPORT_CSV_COLUMNS,
    }
    return render(request, "store/admin_product_import.html", context)


@staff_required
def admin_product_import_template(request):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(IMPORT_CSV_COLUMNS)
    writer.writerow([
        "ຕົວຢ່າງ ເມົ້າໄຮ້ສາຍ", "computer-accessories", "", "Logitech", "250000", "300000", "10",
        "ລາຍລະອຽດສິນຄ້າ...", "Hot", "🖱️",
        "DPI 16000|Battery 70h", "https://example.com/mouse1.jpg|https://example.com/mouse2.jpg",
        "yes", "no", "yes", "https://shopee.co.th/...",
    ])
    response = HttpResponse(output.getvalue().encode("utf-8-sig"), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=product_import_template.csv"
    return response


@staff_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            # Handle delete images
            delete_image_ids = request.POST.getlist('delete_images')
            if delete_image_ids:
                ProductImage.objects.filter(id__in=delete_image_ids, product=product).delete()
            # Handle multiple product image uploads
            images = request.FILES.getlist('new_images')
            for img in images:
                ProductImage.objects.create(product=product, image=img)
            # Handle image links entered instead of file uploads
            image_urls = request.POST.getlist('new_image_urls')
            for url in image_urls:
                url = url.strip()
                if url:
                    ProductImage.objects.create(product=product, image_url=url)
            messages.success(request, "ແກ້ໄຂສິນຄ້າສຳເລັດແລ້ວ")
            return redirect("admin_product_list")
    else:
        form = ProductForm(instance=product)
        
    context = {
        "form": form,
        "product": product,
        "title": "ແກ້ໄຂສິນຄ້າ",
        "active_sub": "products",
        "subcategories": SubCategory.objects.select_related("category").all(),
    }
    return render(request, "store/admin_product_form.html", context)

@staff_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, "ລຶບສິນຄ້າສຳເລັດແລ້ວ")
        return redirect("admin_product_list")
    return render(request, "store/admin_product_delete.html", {"product": product, "active_sub": "products"})


@staff_required
def admin_product_bulk_delete(request):
    if request.method == "POST":
        ids = request.POST.getlist("selected")
        deleted_count, _ = Product.objects.filter(pk__in=ids).delete()
        if ids:
            messages.success(request, f"ລຶບສິນຄ້າສຳເລັດ {len(ids)} ລາຍການ")
        else:
            messages.error(request, "ກະລຸນາເລືອກສິນຄ້າກ່ອນລົບ")
    return redirect("admin_product_list")


# ----------------- CATEGORY CRUD -----------------

@staff_required
def admin_category_list(request):
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()
    context = {
        "categories": categories,
        "subcategories": subcategories,
        "active_sub": "categories",
    }
    return render(request, "store/admin_category_list.html", context)

@staff_required
def admin_category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມໝວດໝູ່ສຳເລັດແລ້ວ")
            return redirect("admin_category_list")
    else:
        form = CategoryForm()
    return render(request, "store/admin_category_form.html", {"form": form, "title": "ເພີ່ມໝວດໝູ່", "active_sub": "categories"})

@staff_required
def admin_category_edit(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "ແກ້ໄຂໝວດໝູ່ສຳເລັດແລ້ວ")
            return redirect("admin_category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "store/admin_category_form.html", {"form": form, "category": category, "title": "ແກ້ໄຂໝວດໝູ່", "active_sub": "categories"})

@staff_required
def admin_category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        category.delete()
        messages.success(request, "ລຶບໝວດໝູ່ສຳເລັດແລ້ວ")
        return redirect("admin_category_list")
    return render(request, "store/admin_category_delete.html", {"category": category, "active_sub": "categories"})


# ----------------- SUBCATEGORY CRUD -----------------

@staff_required
def admin_subcategory_create(request):
    if request.method == "POST":
        form = SubCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມໝວດໝູ່ຍ່ອຍສຳເລັດແລ້ວ")
            return redirect("admin_category_list")
    else:
        form = SubCategoryForm()
    return render(request, "store/admin_category_form.html", {"form": form, "title": "ເພີ່ມໝວດໝູ່ຍ່ອຍ", "active_sub": "categories"})

@staff_required
def admin_subcategory_quick_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    category_slug = request.POST.get("category", "").strip()
    name = request.POST.get("name", "").strip()
    if not category_slug or not name:
        return JsonResponse({"error": "ກະລຸນາເລືອກໝວດຫຼັກ ແລະ ໃສ່ຊື່ໝວດຍ່ອຍ"}, status=400)
    category = Category.objects.filter(slug=category_slug).first()
    if not category:
        return JsonResponse({"error": "ບໍ່ພົບໝວດຫຼັກ"}, status=400)
    subcategory = SubCategory.objects.create(category=category, name=name)
    return JsonResponse({"id": subcategory.pk, "name": subcategory.name, "category": category.slug})

@staff_required
def admin_subcategory_edit(request, pk):
    subcategory = get_object_or_404(SubCategory, pk=pk)
    if request.method == "POST":
        form = SubCategoryForm(request.POST, instance=subcategory)
        if form.is_valid():
            form.save()
            messages.success(request, "ແກ້ໄຂໝວດໝູ່ຍ່ອຍສຳເລັດແລ້ວ")
            return redirect("admin_category_list")
    else:
        form = SubCategoryForm(instance=subcategory)
    return render(request, "store/admin_category_form.html", {"form": form, "subcategory": subcategory, "title": "ແກ້ໄຂໝວດໝູ່ຍ່ອຍ", "active_sub": "categories"})

@staff_required
def admin_subcategory_delete(request, pk):
    subcategory = get_object_or_404(SubCategory, pk=pk)
    if request.method == "POST":
        subcategory.delete()
        messages.success(request, "ລຶບໝວດໝູ່ຍ່ອຍສຳເລັດແລ້ວ")
        return redirect("admin_category_list")
    return render(request, "store/admin_subcategory_delete.html", {"subcategory": subcategory, "active_sub": "categories"})


# ----------------- BRAND CRUD -----------------

@staff_required
def admin_brand_list(request):
    brands = Brand.objects.prefetch_related("categories").all()
    context = {
        "brands": brands,
        "active_sub": "brands",
    }
    return render(request, "store/admin_brand_list.html", context)

@staff_required
def admin_brand_create(request):
    if request.method == "POST":
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມແບຣນສຳເລັດແລ້ວ")
            return redirect("admin_brand_list")
    else:
        form = BrandForm()
    return render(request, "store/admin_brand_form.html", {"form": form, "title": "ເພີ່ມແບຣນ", "active_sub": "brands"})

@staff_required
def admin_brand_edit(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == "POST":
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, "ແກ້ໄຂແບຣນສຳເລັດແລ້ວ")
            return redirect("admin_brand_list")
    else:
        form = BrandForm(instance=brand)
    return render(request, "store/admin_brand_form.html", {"form": form, "brand": brand, "title": "ແກ້ໄຂແບຣນ", "active_sub": "brands"})

@staff_required
def admin_brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == "POST":
        brand.delete()
        messages.success(request, "ລຶບແບຣນສຳເລັດແລ້ວ")
        return redirect("admin_brand_list")
    return render(request, "store/admin_brand_delete.html", {"brand": brand, "active_sub": "brands"})


# ----------------- ORDER CRUD -----------------

@staff_required
def admin_order_list(request):
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '')
    
    orders = Order.objects.all()
    if status_filter:
        orders = orders.filter(status=status_filter)
    if query:
        orders = orders.filter(Q(shipping_name__icontains=query) | Q(shipping_phone__icontains=query) | Q(id__icontains=query))
        
    context = {
        "orders": orders,
        "status_choices": OrderStatus.choices,
        "selected_status": status_filter,
        "query": query,
        "active_sub": "orders",
    }
    return render(request, "store/admin_order_list.html", context)

@staff_required
def admin_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status_choices = OrderStatus.choices
    context = {
        "order": order,
        "status_choices": status_choices,
        "active_sub": "orders",
    }
    return render(request, "store/admin_order_detail.html", context)

@staff_required
def admin_order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in OrderStatus.choices]:
            order.status = new_status
            order.save()
            messages.success(request, "ອັບເດດສະຖານະສຳເລັດແລ້ວ")
    return redirect("admin_order_detail", pk=pk)

@staff_required
def admin_order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.status != OrderStatus.DELIVERED:
        messages.error(request, "ລຶບໄດ້ສະເພາະຄຳສັ່ງຊື້ທີ່ 'ຈັດສົ່ງສຳເລັດ' ເທົ່ານັ້ນ")
        return redirect("admin_order_list")
    if request.method == "POST":
        order.delete()
        messages.success(request, "ລຶບຄຳສັ່ງຊື້ສຳເລັດແລ້ວ")
        return redirect("admin_order_list")
    return render(request, "store/admin_order_delete.html", {"order": order, "active_sub": "orders"})


# ----------------- BANNER CRUD -----------------

@staff_required
def admin_banner_list(request):
    banners = Banner.objects.all()
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມແບນເນີສຳເລັດແລ້ວ")
            return redirect("admin_banner_list")
    else:
        form = BannerForm()
    context = {
        "banners": banners,
        "form": form,
        "active_sub": "banners",
    }
    return render(request, "store/admin_banner_list.html", context)

@staff_required
def admin_banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    if request.method == "POST":
        banner.delete()
        messages.success(request, "ລຶບແບນເນີສຳເລັດແລ້ວ")
    return redirect("admin_banner_list")


# ----------------- BANK ACCOUNT CRUD -----------------

@staff_required
def admin_bank_list(request):
    banks = BankAccount.objects.all()
    context = {
        "banks": banks,
        "active_sub": "banks",
    }
    return render(request, "store/admin_bank_list.html", context)

@staff_required
def admin_bank_create(request):
    if request.method == "POST":
        form = BankAccountForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມບັນຊີທະນາຄານສຳເລັດແລ້ວ")
            return redirect("admin_bank_list")
    else:
        form = BankAccountForm()
    return render(request, "store/admin_bank_form.html", {"form": form, "title": "ເພີ່ມບັນຊີທະນາຄານ", "active_sub": "banks"})

@staff_required
def admin_bank_edit(request, pk):
    bank = get_object_or_404(BankAccount, pk=pk)
    if request.method == "POST":
        form = BankAccountForm(request.POST, request.FILES, instance=bank)
        if form.is_valid():
            form.save()
            messages.success(request, "ແກ້ໄຂບັນຊີທະນາຄານສຳເລັດແລ້ວ")
            return redirect("admin_bank_list")
    else:
        form = BankAccountForm(instance=bank)
    return render(request, "store/admin_bank_form.html", {"form": form, "bank": bank, "title": "ແກ້ໄຂບັນຊີທະນາຄານ", "active_sub": "banks"})

@staff_required
def admin_bank_delete(request, pk):
    bank = get_object_or_404(BankAccount, pk=pk)
    if request.method == "POST":
        bank.delete()
        messages.success(request, "ລຶບບັນຊີທະນາຄານສຳເລັດແລ້ວ")
        return redirect("admin_bank_list")
    return render(request, "store/admin_bank_delete.html", {"bank": bank, "active_sub": "banks"})


# ----------------- SITE SETTINGS CRUD -----------------

@staff_required
def admin_settings_edit(request):
    settings = SiteSettings.load()
    if request.method == "POST":
        form = SiteSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "ບັນທຶກການຕັ້ງຄ່າເວັບໄຊສຳເລັດແລ້ວ")
            return redirect("admin_settings_edit")
    else:
        form = SiteSettingsForm(instance=settings)
    return render(request, "store/admin_settings.html", {"form": form, "settings": settings, "active_sub": "settings"})


# ----------------- MEMBER MANAGEMENT -----------------

@staff_required
def admin_member_list(request):
    query = request.GET.get("q", "").strip()
    members = User.objects.all().order_by("-date_joined")
    if query:
        members = members.filter(
            Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query)
        )
    context = {
        "members": members,
        "query": query,
        "active_sub": "members",
    }
    return render(request, "store/admin_member_list.html", context)

@staff_required
def admin_member_role_update(request, pk):
    member = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if member == request.user:
            messages.error(request, "ທ່ານບໍ່ສາມາດປ່ຽນບົດບາດຂອງຕົນເອງໄດ້")
        else:
            role = request.POST.get("role")
            if role == "admin":
                member.is_staff = True
            else:
                member.is_staff = False
            member.save()
            messages.success(request, "ອັບເດດບົດບາດສຳເລັດແລ້ວ")
    return redirect("admin_member_list")

@staff_required
def admin_member_status_update(request, pk):
    member = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if member == request.user:
            messages.error(request, "ທ່ານບໍ່ສາມາດບລັອກຕົນເອງໄດ້")
        else:
            status = request.POST.get("status")
            if status == "block":
                member.is_active = False
            else:
                member.is_active = True
            member.save()
            messages.success(request, "ອັບເດດສະຖານະສະມາຊິກສຳເລັດແລ້ວ")
    return redirect("admin_member_list")

@staff_required
def admin_member_delete(request, pk):
    member = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if member == request.user:
            messages.error(request, "ທ່ານບໍ່ສາມາດລຶບບັນຊີຂອງຕົນເອງໄດ້")
        else:
            member.delete()
            messages.success(request, "ລຶບສະມາຊິກສຳເລັດແລ້ວ")
    return redirect("admin_member_list")


# ----------------- COUPON CRUD -----------------

@staff_required
def admin_coupon_list(request):
    coupons = Coupon.objects.all().order_by("-id")
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "ເພີ່ມໂຄ້ດສ່ວນຫຼຸດສຳເລັດແລ້ວ")
            return redirect("admin_coupon_list")
    else:
        form = CouponForm()
    
    context = {
        "coupons": coupons,
        "form": form,
        "active_sub": "coupons",
    }
    return render(request, "store/admin_coupon_list.html", context)

@staff_required
def admin_coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        coupon.delete()
        messages.success(request, "ລຶບໂຄ້ດສ່ວນຫຼຸດສຳເລັດແລ້ວ")
    return redirect("admin_coupon_list")
