from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    LAO_PROVINCES,
    Order,
    User,
    Product,
    Category,
    SubCategory,
    Brand,
    Banner,
    BankAccount,
    SiteSettings,
    Coupon,
)


class RegisterForm(UserCreationForm):
    name = forms.CharField(label="ຊື່ - ນາມສະກຸນ", max_length=150)
    phone = forms.CharField(label="ເບີໂທ", max_length=30)
    email = forms.EmailField(label="ອີເມວ")

    error_messages = {
        **UserCreationForm.error_messages,
        "password_mismatch": "ລະຫັດຜ່ານທັງສອງບໍ່ກົງກັນ",
    }

    class Meta:
        model = User
        fields = ["name", "phone", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("ອີເມວນີ້ຖືກໃຊ້ສະໝັກແລ້ວ")
        return email

    def save(self, commit=True):
        # Drop any stale, never-verified signup that used this email/username before.
        User.objects.filter(email=self.cleaned_data["email"], is_active=False).delete()
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["name"]
        user.phone = self.cleaned_data["phone"]
        user.is_active = False
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    province = forms.ChoiceField(
        label="ແຂວງ",
        choices=[("", "-- ເລືອກແຂວງ --")] + [(p, p) for p in LAO_PROVINCES],
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "phone", "province", "city", "address"]
        labels = {
            "first_name": "ຊື່ - ນາມສະກຸນ",
            "phone": "ເບີໂທ",
            "city": "ເມືອງ",
            "address": "ບ້ານ",
        }


class CheckoutForm(forms.ModelForm):
    shipping_province = forms.ChoiceField(
        label="ແຂວງ",
        choices=[("", "-- ເລືອກແຂວງ --")] + [(p, p) for p in LAO_PROVINCES],
    )

    class Meta:
        model = Order
        fields = ["shipping_name", "shipping_phone", "shipping_province", "shipping_city", "shipping_village", "shipping_branch", "carrier"]
        labels = {
            "shipping_name": "ຊື່ລູກຄ້າ",
            "shipping_phone": "ເບີໂທ",
            "shipping_city": "ເມືອງ",
            "shipping_village": "ບ້ານ",
            "shipping_branch": "ສາຂາ",
            "carrier": "ບໍລິສັດຈັດສົ່ງ",
        }
        widgets = {"carrier": forms.RadioSelect}


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["payment_method", "payment_slip"]
        labels = {"payment_method": "ຊ່ອງທາງການຊຳລະເງິນ", "payment_slip": "ແນບສະລິບໂອນເງິນ"}

    def clean_payment_slip(self):
        payment_slip = self.cleaned_data.get("payment_slip")
        if not payment_slip:
            raise forms.ValidationError("ກະລຸນາແນບສະລິບໂອນເງິນກ່ອນຢືນຢັນຄຳສັ່ງຊື້")
        return payment_slip


class ProductForm(forms.ModelForm):
    specs_raw = forms.CharField(
        label="คุณสมบัติ/สเปก (แยกด้วยขึ้นบรรทัดใหม่)",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "เช่น CPU: i9-14900K\nRAM: 32GB DDR5"}),
        required=False,
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "brand",
            "category",
            "subcategory",
            "price",
            "old_price",
            "stock",
            "is_preorder",
            "icon",
            "tag",
            "desc",
            "featured",
            "best_seller",
            "is_new",
            "source_link",
        ]
        labels = {
            "name": "ชื่อสินค้า",
            "brand": "แบรนด์",
            "category": "หมวดหมู่",
            "subcategory": "ໝວດຍ່ອຍ",
            "price": "ราคา (กีบ ₭)",
            "old_price": "ราคาเก่า/ราคาก่อนลด (กีบ ₭)",
            "stock": "จำนวนสินค้าคงเหลือ",
            "is_preorder": "ເປີດຂາຍແບບພຣີອໍເດີ້ (ສັ່ງໄດ້ເຖິງແມ່ນສິນຄ້າໝົດ)",
            "icon": "Emoji ไอคอน (เมื่อไม่มีรูปภาพ)",
            "tag": "ป้ายกำกับ (เช่น Hot, Sale)",
            "desc": "รายละเอียดสินค้า",
            "featured": "แนะนำบนหน้าแรก",
            "best_seller": "สินค้าขายดี",
            "is_new": "สินค้าใหม่",
            "source_link": "ລິ້ງແຫຼ່ງສິນຄ້າ (ບ່ອນສັ່ງເອົາມາຂາຍ) — ເຫັນສະເພາະໜ້າແອັດມິນ",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if isinstance(self.instance.specs, list):
                self.fields["specs_raw"].initial = "\n".join(self.instance.specs)
            else:
                self.fields["specs_raw"].initial = ""

    def clean_specs_raw(self):
        raw = self.cleaned_data.get("specs_raw", "")
        specs = [line.strip() for line in raw.splitlines() if line.strip()]
        return specs

    def save(self, commit=True):
        product = super().save(commit=False)
        product.specs = self.cleaned_data.get("specs_raw", [])
        if commit:
            product.save()
        return product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["slug", "name", "icon", "order"]
        labels = {
            "slug": "Slug ID (ภาษาอังกฤษสั้นๆ เช่น laptops)",
            "name": "ชื่อหมวดหมู่",
            "icon": "ไอคอน (จาก assets/icons.js)",
            "order": "ลำดับการแสดงผล",
        }


class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name", "order"]
        labels = {
            "category": "หมวดหมู่หลัก",
            "name": "ชื่อหมวดหมู่ย่อย",
            "order": "ลำดับการแสดงผล",
        }


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "categories"]
        widgets = {
            "categories": forms.CheckboxSelectMultiple,
        }
        labels = {
            "name": "ชื่อแบรนด์",
            "categories": "ใช้กับหมวดหมู่สินค้า",
        }


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ["image", "order"]
        labels = {
            "image": "รูปภาพแบนเนอร์",
            "order": "ลำดับการแสดงผล",
        }


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ["name", "sub", "account_name", "account_number", "branch", "qr", "order"]
        labels = {
            "name": "ชื่อธนาคาร (เช่น LDB Bank)",
            "sub": "ชื่อรอง (ภาษาลาວ)",
            "account_name": "ชื่อบัญชี",
            "account_number": "เลขบัญชี",
            "branch": "สาขา",
            "qr": "รูปภาพ QR Code (ถ้ามี)",
            "order": "ลำดับการแสดงผล",
        }


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "store_name",
            "logo",
            "logo_url",
            "contact_fb",
            "contact_wa",
            "admin_notify_email",
            "stats_enabled",
            "stat_metric_1",
            "stat_metric_2",
            "stat_metric_3",
            "stat_override_1",
            "stat_override_2",
            "stat_override_3",
            "sales_adjustment",
            "theme_primary",
            "theme_secondary",
            "theme_background",
            "theme_text",
            "theme_card_bg",
            "theme_button",
            "theme_border",
            "theme_header_bg",
            "theme_footer_bg",
            "theme_stat_icon",
            "theme_panel_deep",
            "theme_tabbar_bg",
            "theme_bg_image",
            "theme_bg_image_url",
            "theme_radius",
            "custom_css",
            "popup_ad_enabled",
            "popup_ad_image",
            "popup_ad_link",
            "carrier_anousith_logo",
            "carrier_rungaroon_logo",
            "payment_ldb_logo",
            "payment_bcel_logo",
        ]
        labels = {
            "store_name": "ชื่อร้านค้า",
            "logo": "โลโก้ร้านค้า",
            "logo_url": "หรือใส่ลิงก์รูปโลโก้แทน",
            "contact_fb": "ลิงก์ Facebook Page",
            "contact_wa": "เบอร์ WhatsApp (เช่น 85620XXXXXXXX)",
            "admin_notify_email": "ອີເມວຮັບແຈ້ງເຕືອນອໍເດີ້ໃໝ່",
            "stats_enabled": "เปิดแสดงตัวเลขสถิติ",
            "stat_metric_1": "สถิติช่องที่ 1",
            "stat_metric_2": "สถิติช่องที่ 2",
            "stat_metric_3": "สถิติช่องที่ 3",
            "stat_override_1": "ค่าจริงสถิติช่องที่ 1 (เว้นว่างเพื่อใช้ค่าจริง)",
            "stat_override_2": "ค่าจริงสถิติช่องที่ 2 (เว้นว่างเพื่อใช้ค่าจริง)",
            "stat_override_3": "ค่าจริงสถิติช่องที่ 3 (เว้นว่างเพื่อใช้ค่าจริง)",
            "sales_adjustment": "ປັບຍອດຂາຍລວມ (ບວກເພີ່ມ/ຫຼຸດ)",
            "theme_primary": "ສີຫຼັກ — badge, ໄອຄອນ mega menu, ຈຸດເນັ້ນຕ່າງໆ",
            "theme_secondary": "ສີຮອງ — hover ຂອງ link, ໄລ້ສີປຸ່ມ",
            "theme_background": "ສີພື້ນຫຼັງທັ້ງເວັບໄຊ",
            "theme_text": "ສີໂຕໜັງສືຫຼັກ (ຂໍ້ຄວາມທົ່ວໄປທັ້ງເວັບ)",
            "theme_card_bg": "ສີພື້ນຫຼັງກ່ອງສິນຄ້າ ແລະ ກ່ອງຕ່າງໆ",
            "theme_button": "ສີພື້ນປຸ່ມຫຼັກ (ເຊັ່ນ ປຸ່ມ 'ຊື້ເລີຍ')",
            "theme_border": "ສີເສັ້ນຂອບຈາງໆ ຮອບກ່ອງ/ອົງປະກອບຕ່າງໆ",
            "theme_header_bg": "ສີພື້ນຫຼັງແຖບເມນູເທິງສຸດ (Header)",
            "theme_footer_bg": "ສີພື້ນຫຼັງທ້າຍເວັບ (Footer) — ແຍກຕ່າງຫາກຈາກ Header",
            "theme_stat_icon": "ສີໄອຄອນກ່ອງສະຖິຕິໜ້າຫຼັກ (ໃຊ້ສີດຽວກັນທັ້ງ 3 ກ່ອງ)",
            "theme_panel_deep": "ສີພື້ນຫຼັງເມນູ mega menu / ລິ້ນຊັກມືຖື / ຮູບສິນຄ້າຫຼອກ",
            "theme_tabbar_bg": "ສີພື້ນຫຼັງແຖບເມນູລອຍລຸ່ມສຸດ (ມືຖື)",
            "theme_bg_image": "ຮູບພື້ນຫຼັງເວັບໄຊ (ອັບໂຫຼດໄຟລ໌)",
            "theme_bg_image_url": "ຫຼືໃສ່ລິ້ງຮູບພື້ນຫຼັງແທນ",
            "theme_radius": "ความโค้งของขอบการ์ด/ปุ่ม (เช่น 12px, 20px, 0px)",
            "custom_css": "โค้ด CSS เพิ่มเติมสำหรับตกแต่ง (Custom CSS Overrides)",
            "popup_ad_enabled": "ເປີດໃຊ້ປັອບອັບໂຄສະນາ",
            "popup_ad_image": "ຮູບໂຄສະນາປັອບອັບ",
            "popup_ad_link": "ລິ້ງເມື່ອກົດໃສ່ຮູບ (ເວັ້ນວ່າງໄດ້ຖ້າບໍ່ຕ້ອງການ)",
            "carrier_anousith_logo": "ໂລໂກ້ Anousith Logistics",
            "carrier_rungaroon_logo": "ໂລໂກ້ ຮຸ່ງອະລຸນ ຂົນສົ່ງ",
            "payment_ldb_logo": "ໂລໂກ້ LDB Bank",
            "payment_bcel_logo": "ໂລໂກ້ BCEL Bank",
        }


class CouponForm(forms.ModelForm):
    valid_until = forms.DateTimeField(
        label="วันหมดอายุของโค้ดส่วนลด",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "style": "color-scheme: dark;"}),
        required=False,
    )

    class Meta:
        model = Coupon
        fields = ["code", "label", "percent_off", "active", "valid_until", "max_uses"]
        labels = {
            "code": "รหัสโค้ดส่วนลด (ตัวพิมพ์ใหญ่ภาษาอังกฤษ เช่น SAVE10)",
            "label": "คำอธิบายส่วนลด (เช่น ลด 10%)",
            "percent_off": "เปอร์เซ็นต์ลดราคา (ป้อนตัวเลข 1 - 100)",
            "active": "เปิดใช้งานโค้ดนี้ทันที",
            "max_uses": "จำกัดสิทธิ์ใช้งานสูงสุดกี่ครั้ง (เว้นว่าง = ใช้ได้ไม่จำกัด)",
        }

