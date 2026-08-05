from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    BankAccount, Banner, Brand, Cart, CartItem, Category, Coupon,
    Order, OrderItem, Product, ProductImage, SiteSettings, SubCategory,
    User, Wishlist,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "phone", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("ข้อมูลลูกค้า (MY KEYBOARD)", {"fields": ("phone", "address", "city", "province")}),
    )


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "order")
    inlines = [SubCategoryInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "price", "stock", "featured", "best_seller", "is_new")
    list_filter = ("category", "brand", "featured", "best_seller", "is_new")
    search_fields = ("name", "desc")
    inlines = [ProductImageInline]


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "order")


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_name", "account_number", "order")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "percent_off", "active")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "qty")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "shipping_name", "shipping_phone", "total", "status", "payment_method", "created_at")
    list_filter = ("status", "payment_method", "carrier")
    search_fields = ("shipping_name", "shipping_phone", "id")
    list_editable = ("status",)
    inlines = [OrderItemInline]
    readonly_fields = ("subtotal", "discount", "total", "coupon_code", "created_at")


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)

admin.site.site_header = "MY KEYBOARD — จัดการร้านค้า"
admin.site.site_title = "MY KEYBOARD Admin"
admin.site.index_title = "แดชบอร์ดผู้ดูแลระบบ"
