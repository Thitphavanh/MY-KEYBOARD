import glob, os

reps = {
    'ตรวจสอบสถานะสินค้า': 'ກວດສອບສະຖານະສິນຄ້າ',
    'ตะกร้าสินค้า': 'ກະຕ່າສິນຄ້າ',
    'ที่อยู่จัดส่ง': 'ທີ່ຢູ່ຈັດສົ່ງ',
    'ชำระเงิน': 'ຊຳລະເງິນ',
    'ติดต่อเรา': 'ຕິດຕໍ່ພວກເຮົາ',
    'เข้าสู่ระบบ': 'ເຂົ້າສູ່ລະບົບ',
    'สมัครสมาชิก': 'ສະໝັກສະມາຊິກ',
    'โปรไฟล์ของฉัน': 'ໂປຣໄຟລ໌ຂອງຂ້ອຍ',
    'สินค้าที่ถูกใจ': 'ລາຍການທີ່ມັກ',
    'แดชบอร์ด': 'ແດັດບອດ',
    'จัดการสินค้า': 'ຈັດການສິນຄ້າ',
    'จัดการคำสั่งซื้อ': 'ຈັດການອໍເດີ',
    'คำสั่งซื้อ #': 'ອໍເດີ #',
    'จัดการหมวดหมู่': 'ຈັດການໝວດໝູ່',
    'จัดการแบรนด์': 'ຈັດການແບຣນ',
    'จัดการร้านค้า': 'ຈັດການຮ້ານຄ້າ',
}

files = glob.glob('store/templates/store/*.html') + glob.glob('templates/*.html')
for filepath in files:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content
        for k, v in reps.items():
            new_content = new_content.replace(k, v)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Updated:", filepath)
