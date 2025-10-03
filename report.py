import struct
import os
import datetime
from typing import Optional, List, Tuple
from collections import Counter


class LibrarySystem:
    """ระบบห้องสมุด - Binary File, Fixed-Length Records"""
    
    def __init__(self):
        # กำหนด format สำหรับบันทึกข้อมูล
        # BookID(4) + ISBN(13) + Title(50) + Author(30) + Year(4) + Category(20) + Status(1) + Borrowed(1) + Deleted(1)
        self.book_format = '<I13s50s30s4s20sccc'
        
        # คำนวณขนาด record
        self.book_size = struct.calcsize(self.book_format)
        
        # ชื่อไฟล์
        self.books_file = 'books.dat'
        self.report_file = 'library_report.txt'
        
        self._init_files()
    
    def _init_files(self):
        """สร้างไฟล์เปล่าถ้ายังไม่มี"""
        if not os.path.exists(self.books_file):
            open(self.books_file, 'wb').close()
    
    def _encode(self, text: str, length: int) -> bytes:
        """แปลง string -> bytes ความยาวคงที่"""
        return text.encode('utf-8')[:length].ljust(length, b'\x00')
    
    def _decode(self, data: bytes) -> str:
        """แปลง bytes -> string"""
        return data.decode('utf-8').rstrip('\x00')
    
    def add_sample_data(self):
        """เพิ่มข้อมูลตัวอย่าง"""
        sample_books = [
            (1001, "978-0-123456", "Python Programming", "John Smith", "2021", "Programming", b'1', b'0', b'0'),
            (1002, "978-0-234567", "Data Structures", "Jane Doe", "2020", "Computer Science", b'1', b'1', b'0'),
            (1003, "978-0-345678", "Harry Potter", "J.K. Rowling", "1997", "Fiction", b'1', b'0', b'0'),
            (1004, "978-0-456789", "The Hobbit", "J.R.R. Tolkien", "1937", "Fiction", b'1', b'0', b'0'),
            (1005, "978-0-567890", "Clean Code", "Robert Martin", "2008", "Programming", b'1', b'1', b'0'),
            (1006, "978-0-678901", "Database Systems", "Ramez Elmasri", "2015", "Computer Science", b'1', b'1', b'0'),
            (1007, "978-0-789012", "Algorithms", "Thomas Cormen", "2009", "Computer Science", b'1', b'0', b'0'),
            (1008, "978-0-890123", "1984", "George Orwell", "1949", "Fiction", b'1', b'0', b'0'),
            (1009, "978-0-901234", "Design Patterns", "Gang of Four", "1994", "Programming", b'1', b'0', b'0'),
            (1010, "978-0-012345", "Old Book", "Unknown", "1990", "Reference", b'0', b'0', b'1'),
        ]
        
        with open(self.books_file, 'wb') as f:
            for book in sample_books:
                data = struct.pack(
                    self.book_format,
                    book[0],
                    self._encode(book[1], 13),
                    self._encode(book[2], 50),
                    self._encode(book[3], 30),
                    self._encode(book[4], 4),
                    self._encode(book[5], 20),
                    book[6],
                    book[7],
                    book[8]
                )
                f.write(data)
        
        print("เพิ่มข้อมูลตัวอย่างสำเร็จ!")
    
    def generate_summary_report(self):
        """สร้าง Summary Report และบันทึกเป็นไฟล์ .txt"""
        if not os.path.exists(self.books_file) or os.path.getsize(self.books_file) == 0:
            print("ไม่มีข้อมูลในระบบ")
            return
        
        # อ่านข้อมูลทั้งหมด
        books = []
        with open(self.books_file, 'rb') as f:
            while True:
                data = f.read(self.book_size)
                if not data or len(data) != self.book_size:
                    break
                try:
                    book = struct.unpack(self.book_format, data)
                    books.append(book)
                except struct.error:
                    break
        
        # คำนวณสถิติ
        total_books = len(books)
        active_books = [b for b in books if b[8] == b'0']
        deleted_books = [b for b in books if b[8] == b'1']
        borrowed_books = [b for b in active_books if b[7] == b'1']
        available_books = [b for b in active_books if b[7] == b'0']
        
        # นับจำนวนหนังสือตามหมวดหมู่ (เฉพาะ Active)
        categories = Counter([self._decode(b[5]) for b in active_books])
        
        # เปิดไฟล์เพื่อเขียน Report
        with open(self.report_file, 'w', encoding='utf-8') as report:
            # พิมพ์ Header
            now = datetime.datetime.now()
            report.write("Library Management System - Summary Report (Sample)\n")
            report.write(f"Generated At : {now.strftime('%Y-%m-%d %H:%M:%S')} (+07:00)\n")
            report.write("App Version  : 1.0\n")
            report.write("Endianness   : Little-Endian\n")
            report.write("Encoding     : UTF-8 (fixed-length)\n")
            report.write("\n")
            
            # พิมพ์ตารางรายการหนังสือ
            report.write("+" + "-"*8 + "+" + "-"*15 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*18 + "+" + "-"*10 + "+" + "-"*10 + "+\n")
            report.write(f"| {'BookID':<6} | {'ISBN':<13} | {'Title':<33} | {'Author':<23} | {'Year':<4} | {'Category':<16} | {'Status':<8} | {'Borrowed':<8} |\n")
            report.write("+" + "-"*8 + "+" + "-"*15 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*18 + "+" + "-"*10 + "+" + "-"*10 + "+\n")
            
            for book in books:
                book_id = book[0]
                isbn = self._decode(book[1])
                title = self._decode(book[2])[:31]
                author = self._decode(book[3])[:21]
                year = self._decode(book[4])
                category = self._decode(book[5])[:14]
                status = "Active" if book[6] == b'1' else "Inactive"
                borrowed = "Yes" if book[7] == b'1' else "No"
                deleted = book[8]
                
                # ถ้าถูกลบให้แสดง Deleted
                if deleted == b'1':
                    status = "Deleted"
                
                report.write(f"| {book_id:<6} | {isbn:<13} | {title:<33} | {author:<23} | {year:<4} | {category:<16} | {status:<8} | {borrowed:<8} |\n")
            
            report.write("+" + "-"*8 + "+" + "-"*15 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*18 + "+" + "-"*10 + "+" + "-"*10 + "+\n")
            report.write("\n")
            
            # สรุปสถิติ
            report.write(f"Summary (นับเฉพาะหนังสือที่ Active)\n")
            report.write(f"- Total Books (records) : {total_books}\n")
            report.write(f"- Active Books          : {len(active_books)}\n")
            report.write(f"- Deleted Books         : {len(deleted_books)}\n")
            report.write(f"- Currently Borrowed    : {len(borrowed_books)}\n")
            report.write(f"- Available Now         : {len(available_books)}\n")
            report.write("\n")
            
            report.write(f"Books by Category (Active only)\n")
            for category, count in sorted(categories.items()):
                report.write(f"- {category:<20} : {count}\n")
            report.write("\n")
        
        print(f"สร้าง Report สำเร็จ! บันทึกที่: {self.report_file}")
        print(f"สามารถเปิดไฟล์ {self.report_file} เพื่อดูรายงานได้")
    
    def run(self):
        """รันโปรแกรม"""
        while True:
            print("\n" + "=" * 50)
            print("ระบบห้องสมุด - Library Management System")
            print("=" * 50)
            print("1. เพิ่มข้อมูลตัวอย่าง")
            print("2. สร้าง Summary Report (บันทึกเป็นไฟล์ .txt)")
            print("0. ออก")
            print("-" * 50)
            
            choice = input("เลือก: ").strip()
            
            if choice == '1':
                self.add_sample_data()
                input("\nกด Enter...")
            elif choice == '2':
                self.generate_summary_report()
                input("\nกด Enter...")
            elif choice == '0':
                print("\nขอบคุณที่ใช้บริการ!")
                break
            else:
                print("กรุณาเลือก 0-2 เท่านั้น")


if __name__ == "__main__":
    system = LibrarySystem()
    system.run()