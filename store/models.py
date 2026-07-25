from django.contrib.auth.models import AbstractUser
from django.core.validators import URLValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse


class User(AbstractUser):
    """Custom user — adds the Lao shipping/contact fields the storefront needs.
    is_staff doubles as the "is admin" flag (grants access to /admin/ and the dashboard)."""
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField("ບ້ານ", max_length=255, blank=True)
    city = models.CharField("ເມືອງ", max_length=120, blank=True)
    province = models.CharField("ແຂວງ", max_length=120, blank=True)

    @property
    def is_admin(self):
        return self.is_staff

    def __str__(self):
        return self.get_full_name() or self.username


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    categories = models.ManyToManyField("Category", blank=True, related_name="brands")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    slug = models.SlugField(max_length=40, primary_key=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=40, help_text="Icon name from assets/icons.js")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "subcategories"

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Product(models.Model):
    name = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    price = models.PositiveIntegerField(help_text="ราคาเป็นกีบ (₭)")
    old_price = models.PositiveIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(default=0)
    is_preorder = models.BooleanField(default=False, help_text="ເປີດຂາຍແບບພຣີອໍເດີ້ (ລູກຄ້າສັ່ງຊື້ໄດ້ເຖິງແມ່ນສິນຄ້າໝົດຄັງ)")
    icon = models.CharField(max_length=10, default="💻", help_text="Emoji fallback when no image is set")
    tag = models.CharField(max_length=40, blank=True)
    desc = models.TextField(blank=True)
    specs = models.JSONField(default=list, blank=True, help_text="List of spec strings")
    featured = models.BooleanField(default=True, help_text="Show on homepage + all categories, not just its own category")
    best_seller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    source_link = models.TextField(blank=True, default="", validators=[URLValidator()], help_text="ລິ້ງແຫຼ່ງສິນຄ້າ (ບ່ອນສັ່ງເອົາມາຂາຍ) — ເຫັນສະເພາະໜ້າແອັດມິນ, ລູກຄ້າບໍ່ເຫັນ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.pk])

    @property
    def first_image(self):
        img = self.images.first()
        return img.display_url if img else None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(blank=True, default="", help_text="ໃສ່ລິ້ງຮູບແທນການອັບໂຫຼດໄຟລ໌ (ຖ້າໃສ່ ຈະໃຊ້ລິ້ງນີ້ແທນ)")
    order = models.PositiveIntegerField(default=0)

    @property
    def display_url(self):
        return self.image_url or (self.image.url if self.image else None)

    class Meta:
        ordering = ["order", "id"]


class Banner(models.Model):
    image = models.ImageField(upload_to="banners/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Banner #{self.pk}"


class BankAccount(models.Model):
    name = models.CharField(max_length=100)
    sub = models.CharField("ชื่อรอง (ภาษาลาว)", max_length=150, blank=True)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=100)
    branch = models.CharField(max_length=200, blank=True)
    qr = models.ImageField(upload_to="bank_qr/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class StatMetric(models.TextChoices):
    MEMBERS = "members", "ສະມາຊິກຮ້ານເຮົາ"
    SALES = "sales", "ຍອດຂາຍລວມ"
    COMPLETED_ORDERS = "completedOrders", "ອໍເດີສຳເລັດ"
    TOTAL_ORDERS = "totalOrders", "ອໍເດີທັງໝົດ"
    PRODUCTS = "products", "ສິນຄ້າທັງໝົດ"


class SiteSettings(models.Model):
    """Singleton row (always pk=1) holding all admin-editable site config."""
    store_name = models.CharField(max_length=100, default="NexByte")
    logo = models.ImageField(upload_to="site/", blank=True, null=True)

    contact_fb = models.URLField(blank=True, default="https://facebook.com/nexbytecomputer")
    contact_wa = models.CharField(max_length=30, blank=True, default="8562055551234")
    admin_notify_email = models.EmailField(blank=True, default="", help_text="ອີເມວຮັບແຈ້ງເຕືອນເມື່ອມີອໍເດີ້ໃໝ່ເຂົ້າມາ (ເວັ້ນວ່າງ = ບໍ່ສົ່ງແຈ້ງເຕືອນ)")

    price_calc_thb_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=620,
        help_text="ອັດຕາແລກປ່ຽນ: 1 ບາດໄທ (฿) ເທົ່າກັບຈັກກີບ (₭) — ໃຊ້ໃນເຄື່ອງຄິດໄລ່ລາຄາຕົ້ນທາງໜ້າເພີ່ມ/ແກ້ໄຂສິນຄ້າ",
    )
    price_calc_markup_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=25,
        help_text="ເປີເຊັນກຳໄລເລີ່ມຕົ້ນໃນເຄື່ອງຄິດໄລ່ລາຄາຕົ້ນທາງ (ແກ້ໄຂໄດ້ຕໍ່ສິນຄ້າ)",
    )

    stats_enabled = models.BooleanField(default=True)
    stat_metric_1 = models.CharField(max_length=20, choices=StatMetric.choices, default=StatMetric.MEMBERS)
    stat_metric_2 = models.CharField(max_length=20, choices=StatMetric.choices, default=StatMetric.SALES)
    stat_metric_3 = models.CharField(max_length=20, choices=StatMetric.choices, default=StatMetric.COMPLETED_ORDERS)
    stat_override_1 = models.FloatField(null=True, blank=True, help_text="เว้นว่าง = ใช้ค่าจริง")
    stat_override_2 = models.FloatField(null=True, blank=True)
    stat_override_3 = models.FloatField(null=True, blank=True)
    sales_adjustment = models.BigIntegerField(
        default=0,
        help_text="ยอดขายที่เก็บไว้จากคำสั่งซื้อที่ถูกลบ + ปรับด้วยมือ (บวกเข้ากับยอดขายรวมที่คำนวณจริง)",
    )

    theme_primary = models.CharField(max_length=9, default="#8b7cf6")
    theme_secondary = models.CharField(max_length=9, default="#a78bfa")
    theme_background = models.CharField(max_length=9, default="#0a0913")
    theme_text = models.CharField(max_length=9, default="#f3f1fa")
    theme_card_bg = models.CharField(max_length=9, default="#12101f")
    theme_button = models.CharField(max_length=9, default="#9686f9")
    theme_border = models.CharField(max_length=9, default="#ffffff")
    theme_header_bg = models.CharField(max_length=9, default="#0a0913")
    theme_footer_bg = models.CharField(max_length=9, default="#0a0913")
    theme_stat_icon = models.CharField(max_length=9, default="#8b7cf6")
    theme_panel_deep = models.CharField(max_length=9, default="#1c1832")
    theme_tabbar_bg = models.CharField(max_length=9, default="#171429")
    theme_bg_image = models.ImageField(upload_to="site/", blank=True, null=True)
    theme_bg_image_url = models.URLField(blank=True, default="", help_text="ໃສ່ລິ້ງຮູບແທນການອັບໂຫຼດໄຟລ໌ (ຖ້າໃສ່ ຈະໃຊ້ລິ້ງນີ້ແທນ)")
    logo_url = models.URLField(blank=True, default="", help_text="ໃສ່ລິ້ງຮູບແທນການອັບໂຫຼດໄຟລ໌ (ຖ້າໃສ່ ຈະໃຊ້ລິ້ງນີ້ແທນ)")
    theme_radius = models.CharField(max_length=20, default="12px")
    custom_css = models.TextField(blank=True, default="")

    popup_ad_enabled = models.BooleanField(default=False)
    popup_ad_image = models.ImageField(upload_to="site/", blank=True, null=True)
    popup_ad_link = models.URLField(blank=True, default="", help_text="ລິ້ງເມື່ອກົດໃສ່ຮູບ (ເວັ້ນວ່າງໄດ້ຖ້າບໍ່ຕ້ອງການ)")

    carrier_anousith_logo = models.ImageField(upload_to="site/", blank=True, null=True)
    carrier_rungaroon_logo = models.ImageField(upload_to="site/", blank=True, null=True)
    payment_ldb_logo = models.ImageField(upload_to="site/", blank=True, null=True)
    payment_bcel_logo = models.ImageField(upload_to="site/", blank=True, null=True)

    class Meta:
        verbose_name_plural = "site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site settings"


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=120)
    percent_off = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="carts")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def items_detailed(self):
        return [
            {"item": i, "product": i.product, "line_total": i.product.price * i.qty}
            for i in self.items.select_related("product")
        ]

    def subtotal(self):
        return sum(i["line_total"] for i in self.items_detailed())

    def discount(self):
        if not self.coupon:
            return 0
        return round(self.subtotal() * self.coupon.percent_off / 100)

    def total(self):
        return self.subtotal() - self.discount()

    def count(self):
        return sum(i.qty for i in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="wishlists")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    products = models.ManyToManyField(Product, blank=True, related_name="wishlisted_by")


class OrderStatus(models.TextChoices):
    PENDING = "pending", "ລໍຖ້າຊຳລະເງິນ"
    PREPARING = "preparing", "ກຳລັງກຽມສິນຄ້າ"
    SHIPPING = "shipping", "ກຳລັງຈັດສົ່ງ"
    DELIVERED = "delivered", "ຈັດສົ່ງສຳເລັດ"


class Carrier(models.TextChoices):
    ANOUSITH = "anousith", "Anousith Logistics"
    RUNGAROON = "rungaroon", "รุ่งอรุณ ขนส่ง"


CARRIER_FEES = {
    Carrier.ANOUSITH: 25000,
    Carrier.RUNGAROON: 20000,
}

LAO_PROVINCES = [
    "ນະຄອນຫຼວງວຽງຈັນ", "ຫຼວງພະບາງ", "ຈຳປາສັກ", "ສະຫວັນນະເຂດ", "ຄຳມ່ວນ",
    "ບໍລິຄຳໄຊ", "ຫຼວງນ້ຳທາ", "ໄຊຍະບູລີ", "ອຸດົມໄຊ", "ຜົ້ງສາລີ",
    "ເຊກອງ", "ອັດຕະປື", "ສາລະວັນ", "ຊຽງຂວາງ",
]


class PaymentMethod(models.TextChoices):
    LDB = "ldb", "LDB Bank"
    ONE = "one", "BCEL Bank"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)

    shipping_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=30)
    shipping_province = models.CharField("ແຂວງ", max_length=120)
    shipping_city = models.CharField("ເມືອງ", max_length=120)
    shipping_village = models.CharField("ບ້ານ", max_length=150)
    shipping_branch = models.CharField("ສາຂາ", max_length=150, blank=False, default="")
    carrier = models.CharField(max_length=20, choices=Carrier.choices, default=Carrier.ANOUSITH)

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    payment_slip = models.ImageField(upload_to="slips/", blank=True, null=True)

    coupon_code = models.CharField(max_length=30, blank=True)
    subtotal = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField(default=0)
    shipping_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"NB{self.pk:08d}"

    @property
    def order_number(self):
        return f"NB{self.pk:08d}"


@receiver(pre_delete, sender=Order)
def _bank_sales_total_on_order_delete(sender, instance, **kwargs):
    """Keep the store's lifetime sales total from dropping when an order is deleted,
    no matter which admin UI (custom dashboard or Django /admin/) is used."""
    SiteSettings.objects.filter(pk=1).update(sales_adjustment=models.F("sales_adjustment") + instance.total)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.PositiveIntegerField()
    qty = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.unit_price * self.qty
