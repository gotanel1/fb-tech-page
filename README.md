# บอทโพสต์ข่าวเทคลงเพจ Facebook อัตโนมัติ

ดึงข่าวเทคจาก RSS → ให้ Gemini เขียนเป็นโพสต์ภาษาไทย → โพสต์ขึ้นเพจเอง
รันบน GitHub Actions ฟรี ไม่ต้องเปิดคอมทิ้งไว้

## เริ่มยังไง

อ่าน **[SETUP.md](SETUP.md)** ทำตามทีละขั้น ใช้เวลาราว 30-45 นาที ครั้งเดียวจบ

## โครงสร้างไฟล์

```
.
├── SETUP.md                    คู่มือติดตั้งทีละขั้น  ← เริ่มที่นี่
├── style.md                    บุคลิก/โทนของเพจ (แก้ไฟล์นี้เพื่อเปลี่ยนสไตล์โพสต์)
├── feeds.yaml                  แหล่งข่าว + คำที่กรอง + คำที่ดันคะแนน
├── .env.example                ตัวอย่างค่าตั้งต้น (ก๊อปเป็น .env ตอนรันบนเครื่อง)
├── requirements.txt
├── src/
│   ├── main.py                 ตัวหลัก ร้อยทุกขั้นเข้าด้วยกัน
│   ├── config.py               โหลด config
│   ├── news.py                 ดึง RSS + จัดอันดับข่าว
│   ├── writer.py               เรียก Gemini เขียนโพสต์
│   ├── facebook.py             โพสต์ผ่าน Graph API v26.0
│   └── state.py                กันโพสต์ซ้ำ
├── tools/get_token.py          ตัวช่วยแลก Page Token แบบถาวร
├── state/posted.json           ประวัติข่าวที่โพสต์ไปแล้ว (บอทเขียนเอง)
└── .github/workflows/post.yml  ตารางเวลารันอัตโนมัติ
```

## คำสั่งที่ใช้บ่อย

```bash
python src/main.py --dry-run          # ทดลองรัน ไม่โพสต์จริง
python src/main.py --dry-run --limit 3 # ดูตัวอย่างโพสต์ 3 ชิ้น
python src/main.py                     # โพสต์จริง
python tools/get_token.py              # ขอ Page Token ใหม่
```
