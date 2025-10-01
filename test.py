from datetime import datetime

# ข้อมูลจากที่คุณให้มา
borrow_data = [
    {
        "ID": "001",
        "หนังสือ": "ran",
        "สมาชิก": "soda",
        "ID สมาชิก": "0003",
        "วันยืม": "2025-10-02",
        "สถานะ": "ยืมอยู่ (เหลือ 7 วัน)"
    }
]

# ฟังก์ชันสร้างตาราง Text Report
def create_text_report(data, filename="borrow_report.txt"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (+07:00)")
    
    with open(filename, "w", encoding="utf-8") as f:
        # Header
        f.write("Library Borrow System - Summary Report (Sample)\n")
        f.write(f"Generated At : {now}\n")
        f.write("App Version  : 1.0\n")
        f.write("Encoding     : UTF-8 (fixed-length)\n")
        f.write("\n")
        
        # Table Header
        f.write("+------+------------+----------+----------+------------+-------------------------+\n")
        f.write("| ID   | หนังสือ    | สมาชิก   | ID สมาชิก | วันยืม      | สถานะ                   |\n")
        f.write("+------+------------+----------+----------+------------+-------------------------+\n")
        
        # Data Rows
        for item in data:
            f.write(f"| {item['ID']:<4} | {item['หนังสือ']:<10} | {item['สมาชิก']:<8} | {item['ID สมาชิก']:<8} | {item['วันยืม']:<10} | {item['สถานะ']:<23} |\n")
        
        f.write("+------+------------+----------+----------+------------+-------------------------+\n")
        f.write("\n")
        
        # Summary
        f.write("Summary (ข้อมูลสรุป)\n")
        f.write(f"- Total Borrow Records : {len(data)}\n")
        f.write(f"- Currently Borrowed   : {len([d for d in data if 'ยืมอยู่' in d['สถานะ']])}\n")
        f.write(f"- Returned             : {len([d for d in data if 'คืนแล้ว' in d['สถานะ']])}\n")
        f.write("\n")
        
        # End of Report
        f.write("="*60 + "\n")
        f.write("End of Report\n")

    print(f"✅ สร้างรายงานเรียบร้อย -> {filename}")


# เรียกใช้งาน
create_text_report(borrow_data)
