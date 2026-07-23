from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .cartutils import get_cart, get_wishlist, merge_session_cart_into_user
from .forms import CheckoutForm, PaymentForm, ProfileForm, RegisterForm
from .models import (
    BankAccount, Banner, CARRIER_FEES, Coupon, Order, OrderItem, OrderStatus,
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
    return render(request, "store/home.html", context)


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
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        qty = max(int(request.POST.get("qty", 1) or 1), 1)
        cart = get_cart(request)
        item, created = cart.items.get_or_create(product=product, defaults={"qty": qty})
        if not created:
            item.qty += qty
            item.save()
        messages.success(request, f"ເພີ່ມ {product.name} ລົງກະຕ່າແລ້ວ")
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
            messages.success(request, "ສົ່ງຂໍ້ມູນການຊຳລະເງິນແລ້ວ ຂອບໃຈທີ່ໃຊ້ບໍລິການ")
            return redirect("orders")
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

from .forms import ProductForm, CategoryForm, SubCategoryForm, BannerForm, BankAccountForm, SiteSettingsForm, CouponForm

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
            messages.success(request, "ເພີ່ມສິນຄ້າສຳເລັດແລ້ວ")
            return redirect("admin_product_list")
    else:
        form = ProductForm()
        
    context = {
        "form": form,
        "title": "ເພີ່ມສິນຄ້າໃໝ່",
        "active_sub": "products",
    }
    return render(request, "store/admin_product_form.html", context)

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
            messages.success(request, "ແກ້ໄຂສິນຄ້າສຳເລັດແລ້ວ")
            return redirect("admin_product_list")
    else:
        form = ProductForm(instance=product)
        
    context = {
        "form": form,
        "product": product,
        "title": "ແກ້ໄຂສິນຄ້າ",
        "active_sub": "products",
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
