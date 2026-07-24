from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('api/search-suggest/', views.search_suggest, name='search_suggest'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/coupon/', views.cart_apply_coupon, name='cart_apply_coupon'),
    path('cart/coupon/remove/', views.cart_remove_coupon, name='cart_remove_coupon'),

    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:pk>/', views.wishlist_toggle, name='wishlist_toggle'),

    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_view, name='payment'),
    path('orders/', views.orders_view, name='orders'),
    path('orders/<int:pk>/', views.order_detail_view, name='order_detail'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='store/password_reset.html',
        email_template_name='store/email/password_reset_email.html',
        subject_template_name='store/email/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='store/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='store/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='store/password_reset_complete.html',
    ), name='password_reset_complete'),

    path('contact/', views.contact_view, name='contact'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/products/', views.admin_product_list, name='admin_product_list'),
    path('dashboard/products/create/', views.admin_product_create, name='admin_product_create'),
    path('dashboard/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('dashboard/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('dashboard/categories/', views.admin_category_list, name='admin_category_list'),
    path('dashboard/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('dashboard/categories/<slug:slug>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('dashboard/categories/<slug:slug>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('dashboard/categories/sub/create/', views.admin_subcategory_create, name='admin_subcategory_create'),
    path('dashboard/categories/sub/quick-create/', views.admin_subcategory_quick_create, name='admin_subcategory_quick_create'),
    path('dashboard/categories/sub/<int:pk>/edit/', views.admin_subcategory_edit, name='admin_subcategory_edit'),
    path('dashboard/categories/sub/<int:pk>/delete/', views.admin_subcategory_delete, name='admin_subcategory_delete'),
    path('dashboard/brands/', views.admin_brand_list, name='admin_brand_list'),
    path('dashboard/brands/create/', views.admin_brand_create, name='admin_brand_create'),
    path('dashboard/brands/<int:pk>/edit/', views.admin_brand_edit, name='admin_brand_edit'),
    path('dashboard/brands/<int:pk>/delete/', views.admin_brand_delete, name='admin_brand_delete'),
    path('dashboard/orders/', views.admin_order_list, name='admin_order_list'),
    path('dashboard/orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
    path('dashboard/orders/<int:pk>/status/', views.admin_order_status_update, name='admin_order_status_update'),
    path('dashboard/orders/<int:pk>/delete/', views.admin_order_delete, name='admin_order_delete'),
    path('dashboard/banners/', views.admin_banner_list, name='admin_banner_list'),
    path('dashboard/banners/<int:pk>/delete/', views.admin_banner_delete, name='admin_banner_delete'),
    path('dashboard/bank-accounts/', views.admin_bank_list, name='admin_bank_list'),
    path('dashboard/bank-accounts/create/', views.admin_bank_create, name='admin_bank_create'),
    path('dashboard/bank-accounts/<int:pk>/edit/', views.admin_bank_edit, name='admin_bank_edit'),
    path('dashboard/bank-accounts/<int:pk>/delete/', views.admin_bank_delete, name='admin_bank_delete'),
    path('dashboard/settings/', views.admin_settings_edit, name='admin_settings_edit'),
    path('dashboard/members/', views.admin_member_list, name='admin_member_list'),
    path('dashboard/members/<int:pk>/role/', views.admin_member_role_update, name='admin_member_role_update'),
    path('dashboard/members/<int:pk>/status/', views.admin_member_status_update, name='admin_member_status_update'),
    path('dashboard/members/<int:pk>/delete/', views.admin_member_delete, name='admin_member_delete'),
    path('dashboard/coupons/', views.admin_coupon_list, name='admin_coupon_list'),
    path('dashboard/coupons/<int:pk>/delete/', views.admin_coupon_delete, name='admin_coupon_delete'),
]
