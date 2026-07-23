Viewed profile.html:1-42

วิธีเข้าโฟลเดอร์โปรเจกต์นี้และ Activate สภาพแวดล้อมจำลอง (Virtual Environment) เพื่อรันระบบ สามารถทำตามขั้นตอนต่อไปนี้ได้เลยครับ:

---

### สำหรับ PowerShell (ค่าเริ่มต้นใน Windows Terminal / VS Code)

1. **เข้าโฟลเดอร์โปรเจกต์:**

   ```powershell
   cd "C:\Users\gno35\OneDrive\MY KEYBOARD"
   ```
2. **เปิดใช้งาน Virtual Environment (.venv):**

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   *(หากเกิดข้อผิดพลาดเกี่ยวกับการตั้งค่าความปลอดภัยของ Windows ให้รันคำสั่ง `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` ก่อนเปิดใช้งานสภาพแวดล้อมครับ)*
3. **รันเซิร์ฟเวอร์ Django:**

   ```powershell
   python manage.py runserver
   ```

---

### สำหรับ Command Prompt (CMD)

1. **เข้าโฟลเดอร์โปรเจกต์:**

   ```cmd
   cd /d "C:\Users\gno35\OneDrive\MY KEYBOARD"
   ```
2. **เปิดใช้งาน Virtual Environment (.venv):**

   ```cmd
   .venv\Scripts\activate.bat
   ```
3. **รันเซิร์ฟเวอร์ Django:**

   ```cmd
   python manage.py runserver
   ```

---

> [!TIP]
> เมื่อคุณเปิดใช้งาน venv สำเร็จ จะเห็นสัญลักษณ์ **`(.venv)`** ปรากฏอยู่ด้านหน้าสุดของบรรทัดป้อนคำสั่งใน Terminal เสมอครับ

---

### วิธีสร้างบัญชีผู้ดูแลระบบใหม่ (Create Superuser)

หากต้องการสร้างบัญชี Admin ใหม่เพื่อเข้าหน้าหลังบ้าน (Django Admin) ให้ใช้คำสั่งนี้:

1. **รันคำสั่งสร้าง Superuser:**
   ```powershell
   python manage.py createsuperuser
   ```
2. **ระบุรายละเอียดผู้ใช้:**
   * **Username**: ชื่อเข้าใช้งาน (ถ้าขึ้นเตือนว่าซ้ำ ให้เลือกใช้ชื่ออื่น)
   * **Email address**: อีเมล (จะใส่หรือไม่ใส่ก็ได้)
   * **Password**: รหัสผ่านใหม่ (ขณะพิมพ์ตัวอักษรจะไม่แสดงขึ้นหน้าจอเพื่อความปลอดภัย ให้พิมพ์เสร็จแล้วกด Enter ได้เลย)
   * **Password (again)**: ยืนยันรหัสผ่านใหม่อีกครั้ง

---

### วิธีเปลี่ยนหรือแก้ไขรหัสผ่านผู้ใช้งาน (Change Password)

หากจำรหัสผ่านผู้ใช้ไม่ได้ หรือต้องการเปลี่ยนรหัสผ่านใหม่:

1. **รันคำสั่งเปลี่ยนรหัสผ่าน:**

   ```powershell
   python manage.py changepassword <ชื่อผู้ใช้งาน>
   ```
   *ตัวอย่างการเปลี่ยนรหัสผ่านของบัญชี `admin`:*
   ```powershell
   python manage.py changepassword admin
   ```
2. **ระบุรหัสผ่านใหม่:**

   * กรอกรหัสผ่านใหม่ 2 ครั้ง (ตัวอักษรจะไม่แสดงขึ้นหน้าจอเช่นกัน)
   * รหัสผ่านจะต้องมีความยาวและไม่เดาง่ายจนเกินไป เช่น ไม่ตรงกับชื่อผู้ใช้ เป็นต้น
