import struct
import os
import datetime
from typing import Optional, List, Tuple


class SimpleLibrary:
    """ระบบจัดการห้องสมุดแบบง่าย"""
    
    def __init__(self):
        # โครงสร้างข้อมูล
        self.book_format = '<4s100s50s4s1s1s'  # ID, Title, Author, Year, Status, Deleted
        self.member_format = '<4s50s15s10s1s1s'  # ID, Name, Phone, JoinDate, Status, Deleted
        self.borrow_format = '<4s4s4s10s10s1s1s'  # ID, BookID, MemberID, BorrowDate, ReturnDate, Status, Deleted
        
        self.book_size = struct.calcsize(self.book_format)
        self.member_size = struct.calcsize(self.member_format)
        self.borrow_size = struct.calcsize(self.borrow_format)
        
        # ชื่อไฟล์
        self.books_file = 'books.dat'
        self.members_file = 'members.dat'
        self.borrows_file = 'borrows.dat'
        
        self._init_files()
    
    def _init_files(self):
        """สร้างไฟล์ถ้ายังไม่มี"""
        for f in [self.books_file, self.members_file, self.borrows_file]:
            if not os.path.exists(f):
                open(f, 'wb').close()
    
    def _encode(self, text: str, length: int) -> bytes:
        """แปลงข้อความเป็น bytes"""
        return text.encode('utf-8')[:length].ljust(length, b'\x00')
    
    def _decode(self, data: bytes) -> str:
        """แปลง bytes เป็นข้อความ"""
        return data.decode('utf-8').rstrip('\x00')
    
    def _get_next_id(self, filename: str, size: int) -> str:
        """สร้าง ID ใหม่"""
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return "0001"
        
        with open(filename, 'rb') as f:
            f.seek(-size, 2)
            data = f.read(4)
            last_id = int(self._decode(data))
            return f"{last_id + 1:04d}"
    
    # ==================== หนังสือ ====================
    
    def add_book(self):
        """เพิ่มหนังสือ"""
        print("\n=== เพิ่มหนังสือ ===")
        title = input("ชื่อหนังสือ: ").strip()
        author = input("ผู้แต่ง: ").strip()
        year = input("ปีที่พิมพ์: ").strip()
        
        if not title or not author or not year:
            print("❌ กรุณากรอกข้อมูลให้ครบ")
            return
        
        book_id = self._get_next_id(self.books_file, self.book_size)
        
        data = struct.pack(
            self.book_format,
            self._encode(book_id, 4),
            self._encode(title, 100),
            self._encode(author, 50),
            self._encode(year, 4),
            b'A',  # Available
            b'0'   # Not deleted
        )
        
        with open(self.books_file, 'ab') as f:
            f.write(data)
        
        print(f"✅ เพิ่มหนังสือสำเร็จ! ID: {book_id}")
    
    def list_books(self):
        """แสดงรายการหนังสือทั้งหมด"""
        print("\n=== รายการหนังสือ ===")
        
        if not os.path.exists(self.books_file) or os.path.getsize(self.books_file) == 0:
            print("ยังไม่มีหนังสือในระบบ")
            return
        
        print(f"{'ID':<6} {'ชื่อ':<35} {'ผู้แต่ง':<20} {'ปี':<6} {'สถานะ':<10}")
        print("-" * 85)
        
        with open(self.books_file, 'rb') as f:
            while True:
                data = f.read(self.book_size)
                if not data:
                    break
                
                if len(data) != self.book_size:
                    break
                
                try:
                    book = struct.unpack(self.book_format, data)
                    if book[5] == b'0':
                        book_id = self._decode(book[0])
                        title = self._decode(book[1])[:33]
                        author = self._decode(book[2])[:18]
                        year = self._decode(book[3])
                        status = "ว่าง" if book[4] == b'A' else "ถูกยืม"
                        
                        print(f"{book_id:<6} {title:<35} {author:<20} {year:<6} {status:<10}")
                except struct.error as e:
                    break
    
    def search_book(self):
        """ค้นหาหนังสือ"""
        print("\n=== ค้นหาหนังสือ ===")
        keyword = input("ค้นหาจากชื่อหรือผู้แต่ง: ").strip().lower()
        
        found = False
        print(f"\n{'ID':<6} {'ชื่อ':<35} {'ผู้แต่ง':<20} {'สถานะ':<10}")
        print("-" * 75)
        
        with open(self.books_file, 'rb') as f:
            while True:
                data = f.read(self.book_size)
                if not data or len(data) != self.book_size:
                    break
                
                try:
                    book = struct.unpack(self.book_format, data)
                    if book[5] == b'0':
                        title = self._decode(book[1]).lower()
                        author = self._decode(book[2]).lower()
                        
                        if keyword in title or keyword in author:
                            book_id = self._decode(book[0])
                            display_title = self._decode(book[1])[:33]
                            display_author = self._decode(book[2])[:18]
                            status = "ว่าง" if book[4] == b'A' else "ถูกยืม"
                            
                            print(f"{book_id:<6} {display_title:<35} {display_author:<20} {status:<10}")
                            found = True
                except struct.error:
                    break
        
        if not found:
            print("ไม่พบหนังสือที่ค้นหา")
    
    def update_book(self):
        """แก้ไขหนังสือ"""
        print("\n=== แก้ไขหนังสือ ===")
        book_id = input("ID หนังสือที่ต้องการแก้ไข: ").strip()
        
        book_index = self._find_book_index(book_id)
        if book_index == -1:
            print("❌ ไม่พบหนังสือ")
            return
        
        book = self._get_book_at_index(book_index)
        if not book:
            return
        
        print("\n--- ข้อมูลปัจจุบัน ---")
        print(f"ชื่อ: {self._decode(book[1])}")
        print(f"ผู้แต่ง: {self._decode(book[2])}")
        print(f"ปี: {self._decode(book[3])}")
        
        print("\n--- กรอกข้อมูลใหม่ (Enter = ไม่เปลี่ยน) ---")
        title = input("ชื่อหนังสือ: ").strip()
        author = input("ผู้แต่ง: ").strip()
        year = input("ปีที่พิมพ์: ").strip()
        
        if not title:
            title = self._decode(book[1])
        if not author:
            author = self._decode(book[2])
        if not year:
            year = self._decode(book[3])
        
        updated_book = struct.pack(
            self.book_format,
            book[0],
            self._encode(title, 100),
            self._encode(author, 50),
            self._encode(year, 4),
            book[4],
            book[5]
        )
        
        with open(self.books_file, 'r+b') as f:
            f.seek(book_index * self.book_size)
            f.write(updated_book)
        
        print("\n✅ แก้ไขหนังสือสำเร็จ!")
    
    def delete_book(self):
        """ลบหนังสือ"""
        print("\n=== ลบหนังสือ ===")
        book_id = input("ID หนังสือที่ต้องการลบ: ").strip()
        
        book_index = self._find_book_index(book_id)
        if book_index == -1:
            print("❌ ไม่พบหนังสือ")
            return
        
        book = self._get_book_at_index(book_index)
        if not book:
            return
        
        if book[4] == b'B':
            print("❌ หนังสือถูกยืมอยู่ ไม่สามารถลบได้")
            return
        
        print("\n--- หนังสือที่จะลบ ---")
        print(f"ชื่อ: {self._decode(book[1])}")
        print(f"ผู้แต่ง: {self._decode(book[2])}")
        
        confirm = input("\nยืนยันการลบ? (y/n): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิกการลบ")
            return
        
        deleted_book = struct.pack(
            self.book_format,
            book[0], book[1], book[2], book[3], book[4],
            b'1'
        )
        
        with open(self.books_file, 'r+b') as f:
            f.seek(book_index * self.book_size)
            f.write(deleted_book)
        
        print("\n✅ ลบหนังสือสำเร็จ!")
    
    def _find_book_index(self, book_id: str) -> int:
        """หา index ของหนังสือ"""
        if not os.path.exists(self.books_file):
            return -1
        
        with open(self.books_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.book_size)
                if not data or len(data) != self.book_size:
                    break
                
                try:
                    book = struct.unpack(self.book_format, data)
                    if self._decode(book[0]) == book_id and book[5] == b'0':
                        return index
                    index += 1
                except struct.error:
                    break
        
        return -1
    
    def _get_book_at_index(self, index: int) -> Optional[Tuple]:
        """ดึงข้อมูลหนังสือจาก index"""
        if not os.path.exists(self.books_file):
            return None
        
        with open(self.books_file, 'rb') as f:
            f.seek(index * self.book_size)
            data = f.read(self.book_size)
            
            if not data or len(data) != self.book_size:
                return None
            
            try:
                return struct.unpack(self.book_format, data)
            except struct.error:
                return None
    
    # ==================== สมาชิก ====================
    
    def add_member(self):
        """เพิ่มสมาชิก"""
        print("\n=== เพิ่มสมาชิก ===")
        name = input("ชื่อ-สกุล: ").strip()
        phone = input("เบอร์โทร: ").strip()
        
        if not name:
            print("❌ กรุณากรอกชื่อ")
            return
        
        member_id = self._get_next_id(self.members_file, self.member_size)
        join_date = datetime.date.today().strftime("%Y-%m-%d")
        
        data = struct.pack(
            self.member_format,
            self._encode(member_id, 4),
            self._encode(name, 50),
            self._encode(phone, 15),
            self._encode(join_date, 10),
            b'A',
            b'0'
        )
        
        with open(self.members_file, 'ab') as f:
            f.write(data)
        
        print(f"✅ เพิ่มสมาชิกสำเร็จ! ID: {member_id}")
    
    def list_members(self):
        """แสดงรายการสมาชิก"""
        print("\n=== รายการสมาชิก ===")
        
        if not os.path.exists(self.members_file) or os.path.getsize(self.members_file) == 0:
            print("ยังไม่มีสมาชิกในระบบ")
            return
        
        print(f"{'ID':<6} {'ชื่อ':<30} {'เบอร์โทร':<15} {'สถานะ':<10}")
        print("-" * 65)
        
        with open(self.members_file, 'rb') as f:
            while True:
                data = f.read(self.member_size)
                if not data or len(data) != self.member_size:
                    break
                
                try:
                    member = struct.unpack(self.member_format, data)
                    if member[5] == b'0':
                        member_id = self._decode(member[0])
                        name = self._decode(member[1])[:28]
                        phone = self._decode(member[2])
                        status = "ใช้งาน" if member[4] == b'A' else "ถูกแบน"
                        
                        print(f"{member_id:<6} {name:<30} {phone:<15} {status:<10}")
                except struct.error:
                    break
    
    def delete_member(self):
        """ลบสมาชิก"""
        print("\n=== ลบสมาชิก ===")
        member_id = input("ID สมาชิกที่ต้องการลบ: ").strip()
        
        member_index = self._find_member_index(member_id)
        if member_index == -1:
            print("ไม่พบสมาชิก")
            return
        
        member = self._get_member_at_index(member_index)
        if not member:
            return
        
        if self._has_active_borrow_by_member(member_id):
            print("สมาชิกคนนี้กำลังยืมหนังสืออยู่ ไม่สามารถลบได้")
            print("กรุณาให้สมาชิกคืนหนังสือก่อน")
            return
        
        print("\n--- สมาชิกที่จะลบ ---")
        print(f"ชื่อ: {self._decode(member[1])}")
        print(f"เบอร์โทร: {self._decode(member[2])}")
        print(f"วันที่สมัคร: {self._decode(member[3])}")
        
        confirm = input("\nยืนยันการลบ? (y/n): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิกการลบ")
            return
        
        deleted_member = struct.pack(
            self.member_format,
            member[0], member[1], member[2], member[3], member[4],
            b'1'
        )
        
        with open(self.members_file, 'r+b') as f:
            f.seek(member_index * self.member_size)
            f.write(deleted_member)
        
        print("\nลบสมาชิกสำเร็จ!")
    
    def _find_member_index(self, member_id: str) -> int:
        """หา index ของสมาชิก"""
        if not os.path.exists(self.members_file):
            return -1
        
        with open(self.members_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.member_size)
                if not data or len(data) != self.member_size:
                    break
                
                try:
                    member = struct.unpack(self.member_format, data)
                    if self._decode(member[0]) == member_id and member[5] == b'0':
                        return index
                    index += 1
                except struct.error:
                    break
        
        return -1
    
    def _get_member_at_index(self, index: int) -> Optional[Tuple]:
        """ดึงข้อมูลสมาชิกจาก index"""
        if not os.path.exists(self.members_file):
            return None
        
        with open(self.members_file, 'rb') as f:
            f.seek(index * self.member_size)
            data = f.read(self.member_size)
            
            if not data or len(data) != self.member_size:
                return None
            
            try:
                return struct.unpack(self.member_format, data)
            except struct.error:
                return None
    
    def _has_active_borrow_by_member(self, member_id: str) -> bool:
        """ตรวจสอบว่าสมาชิกมีหนังสือยืมอยู่หรือไม่"""
        if not os.path.exists(self.borrows_file):
            return False
        
        with open(self.borrows_file, 'rb') as f:
            while True:
                data = f.read(self.borrow_size)
                if not data or len(data) != self.borrow_size:
                    break
                
                try:
                    borrow = struct.unpack(self.borrow_format, data)
                    if (self._decode(borrow[2]) == member_id and 
                        borrow[5] == b'B' and borrow[6] == b'0'):
                        return True
                except struct.error:
                    break
        
        return False
    
    # ==================== ยืม-คืน ====================
    
    def borrow_book(self):
        """ยืมหนังสือ"""
        print("\n=== ยืมหนังสือ ===")
        member_id = input("ID สมาชิก: ").strip()
        book_id = input("ID หนังสือ: ").strip()
        
        member = self._find_member(member_id)
        if not member:
            print("❌ ไม่พบสมาชิก")
            return
        
        if member[4] != b'A':
            print("❌ สมาชิกถูกระงับ ไม่สามารถยืมได้")
            return
        
        book = self._find_book(book_id)
        if not book:
            print("❌ ไม่พบหนังสือ")
            return
        
        if book[4] != b'A':
            print("❌ หนังสือถูกยืมแล้ว")
            return
        
        borrow_id = self._get_next_id(self.borrows_file, self.borrow_size)
        borrow_date = datetime.date.today().strftime("%Y-%m-%d")
        
        data = struct.pack(
            self.borrow_format,
            self._encode(borrow_id, 4),
            self._encode(book_id, 4),
            self._encode(member_id, 4),
            self._encode(borrow_date, 10),
            self._encode("", 10),
            b'B',
            b'0'
        )
        
        with open(self.borrows_file, 'ab') as f:
            f.write(data)
        
        self._update_book_status(book_id, b'B')
        
        due_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"✅ ยืมสำเร็จ!")
        print(f"📚 หนังสือ: {self._decode(book[1])}")
        print(f"👤 ผู้ยืม: {self._decode(member[1])}")
        print(f"📅 กำหนดคืน: {due_date}")
    
    def return_book(self):
        """คืนหนังสือ"""
        print("\n=== คืนหนังสือ ===")
        book_id = input("ID หนังสือ: ").strip()
        
        borrow_record = self._find_active_borrow(book_id)
        if not borrow_record:
            print("❌ ไม่พบรายการยืม หรือคืนแล้ว")
            return
        
        index, borrow = borrow_record
        return_date = datetime.date.today().strftime("%Y-%m-%d")
        
        updated = struct.pack(
            self.borrow_format,
            borrow[0], borrow[1], borrow[2], borrow[3],
            self._encode(return_date, 10),
            b'R',
            borrow[6]
        )
        
        with open(self.borrows_file, 'r+b') as f:
            f.seek(index * self.borrow_size)
            f.write(updated)
        
        self._update_book_status(book_id, b'A')
        
        borrow_date = datetime.datetime.strptime(self._decode(borrow[3]), "%Y-%m-%d").date()
        due_date = borrow_date + datetime.timedelta(days=7)
        days_late = (datetime.date.today() - due_date).days
        
        print("✅ คืนหนังสือสำเร็จ!")
        
        if days_late > 0:
            fine = days_late * 10
            print(f"⚠️  เกินกำหนด {days_late} วัน")
            print(f"💰 ค่าปรับ: {fine} บาท")
        else:
            print("✨ คืนตรงเวลา")
    
    def list_borrows(self):
        """แสดงรายการยืมที่ยังไม่คืน"""
        print("\n=== รายการยืมปัจจุบัน ===")
        
        if not os.path.exists(self.borrows_file) or os.path.getsize(self.borrows_file) == 0:
            print("ไม่มีรายการยืม")
            return
        
        print(f"{'หนังสือ':<35} {'ผู้ยืม':<25} {'วันยืม':<12} {'กำหนดคืน':<12}")
        print("-" * 90)
        
        found = False
        with open(self.borrows_file, 'rb') as f:
            while True:
                data = f.read(self.borrow_size)
                if not data or len(data) != self.borrow_size:
                    break
                
                try:
                    borrow = struct.unpack(self.borrow_format, data)
                    if borrow[5] == b'B' and borrow[6] == b'0':
                        book_id = self._decode(borrow[1])
                        member_id = self._decode(borrow[2])
                        
                        book = self._find_book(book_id)
                        member = self._find_member(member_id)
                        
                        if book and member:
                            book_title = self._decode(book[1])[:33]
                            member_name = self._decode(member[1])[:23]
                            borrow_date = self._decode(borrow[3])
                            
                            borrow_dt = datetime.datetime.strptime(borrow_date, "%Y-%m-%d").date()
                            due_date = (borrow_dt + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                            
                            print(f"{book_title:<35} {member_name:<25} {borrow_date:<12} {due_date:<12}")
                            found = True
                except struct.error:
                    break
        
        if not found:
            print("ไม่มีรายการยืมปัจจุบัน")
    
    # ==================== รายงานสรุป ====================
    
    def generate_summary_report(self):
        """สร้างรายงานสรุปแบบครบถ้วน"""
        now = datetime.datetime.now()
        tz_offset = "+07:00"
        
        print("\n" + "="*90)
        print("Library System - Summary Report")
        print(f"Generated At : {now.strftime('%Y-%m-%d %H:%M:%S')} ({tz_offset})")
        print(f"App Version  : 1.0")
        print(f"Endianness   : Little-Endian")
        print(f"Encoding     : UTF-8 (fixed-length)")
        print("="*90)
        print()
        
        # ตารางหนังสือทั้งหมด
        books_data = []
        if os.path.exists(self.books_file):
            with open(self.books_file, 'rb') as f:
                while True:
                    data = f.read(self.book_size)
                    if not data or len(data) != self.book_size:
                        break
                    try:
                        book = struct.unpack(self.book_format, data)
                        books_data.append(book)
                    except struct.error:
                        break
        
        # แสดงตารางหนังสือ
        print("+" + "-"*8 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*10 + "+" + "-"*10 + "+")
        print(f"| {'BookID':<6} | {'Title':<33} | {'Author':<23} | {'Year':<4} | {'Status':<8} | {'Borrowed':<8} |")
        print("+" + "-"*8 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*10 + "+" + "-"*10 + "+")
        
        for book in books_data:
            book_id = self._decode(book[0])
            title = self._decode(book[1])[:31]
            author = self._decode(book[2])[:21]
            year = self._decode(book[3])
            status = "Active" if book[5] == b'0' else "Deleted"
            borrowed = "Yes" if book[4] == b'B' else "No"
            
            print(f"| {book_id:<6} | {title:<33} | {author:<23} | {year:<4} | {status:<8} | {borrowed:<8} |")
        
        print("+" + "-"*8 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*6 + "+" + "-"*10 + "+" + "-"*10 + "+")
        print()
        
        # สรุปสถิติ (เฉพาะที่ Active)
        total_books = sum(1 for b in books_data if b[5] == b'0')
        active_books = sum(1 for b in books_data if b[5] == b'0')
        deleted_books = sum(1 for b in books_data if b[5] == b'1')
        borrowed_books = sum(1 for b in books_data if b[5] == b'0' and b[4] == b'B')
        available_books = sum(1 for b in books_data if b[5] == b'0' and b[4] == b'A')
        
        print("Summary (นับเฉพาะรายการ Active)")
        print(f"- Total Books (records) : {len(books_data)}")
        print(f"- Active Books          : {active_books}")
        print(f"- Deleted Books         : {deleted_books}")
        print(f"- Currently Borrowed    : {borrowed_books}")
        print(f"- Available Now         : {available_books}")
        print()
        
        # สมาชิกทั้งหมด
        members_data = []
        if os.path.exists(self.members_file):
            with open(self.members_file, 'rb') as f:
                while True:
                    data = f.read(self.member_size)
                    if not data or len(data) != self.member_size:
                        break
                    try:
                        member = struct.unpack(self.member_format, data)
                        members_data.append(member)
                    except struct.error:
                        break
        
        # แสดงตารางสมาชิก
        print("Members List")
        print("+" + "-"*10 + "+" + "-"*35 + "+" + "-"*18 + "+" + "-"*12 + "+" + "-"*10 + "+")
        print(f"| {'MemberID':<8} | {'Name':<33} | {'Phone':<16} | {'JoinDate':<10} | {'Status':<8} |")
        print("+" + "-"*10 + "+" + "-"*35 + "+" + "-"*18 + "+" + "-"*12 + "+" + "-"*10 + "+")
        
        for member in members_data:
            if member[5] == b'0':  # แสดงเฉพาะที่ยังไม่ลบ
                member_id = self._decode(member[0])
                name = self._decode(member[1])[:31]
                phone = self._decode(member[2])[:14]
                join_date = self._decode(member[3])
                status = "Active" if member[4] == b'A' else "Banned"
                
                print(f"| {member_id:<8} | {name:<33} | {phone:<16} | {join_date:<10} | {status:<8} |")
        
        print("+" + "-"*10 + "+" + "-"*35 + "+" + "-"*18 + "+" + "-"*12 + "+" + "-"*10 + "+")
        print()
        
        # สถิติสมาชิก
        active_members = sum(1 for m in members_data if m[5] == b'0' and m[4] == b'A')
        banned_members = sum(1 for m in members_data if m[5] == b'0' and m[4] == b'B')
        
        print("Member Summary")
        print(f"- Total Members (Active) : {active_members}")
        print(f"- Banned Members         : {banned_members}")
        print()
        
        # รายการยืม-คืน
        borrows_data = []
        if os.path.exists(self.borrows_file):
            with open(self.borrows_file, 'rb') as f:
                while True:
                    data = f.read(self.borrow_size)
                    if not data or len(data) != self.borrow_size:
                        break
                    try:
                        borrow = struct.unpack(self.borrow_format, data)
                        if borrow[6] == b'0':  # ไม่ถูกลบ
                            borrows_data.append(borrow)
                    except struct.error:
                        break
        
        # แสดงรายการยืมที่ยังไม่คืน
        print("Current Borrowing Records (Not Yet Returned)")
        print("+" + "-"*12 + "+" + "-"*10 + "+" + "-"*10 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*12 + "+")
        print(f"| {'BorrowID':<10} | {'BookID':<8} | {'MemberID':<8} | {'BookTitle':<33} | {'MemberName':<23} | {'BorrowDate':<10} |")
        print("+" + "-"*12 + "+" + "-"*10 + "+" + "-"*10 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*12 + "+")
        
        currently_borrowed = 0
        for borrow in borrows_data:
            if borrow[5] == b'B':  # สถานะยืมอยู่
                borrow_id = self._decode(borrow[0])
                book_id = self._decode(borrow[1])
                member_id = self._decode(borrow[2])
                borrow_date = self._decode(borrow[3])
                
                # หาข้อมูลหนังสือและสมาชิก
                book = self._find_book(book_id)
                member = self._find_member(member_id)
                
                book_title = self._decode(book[1])[:31] if book else "N/A"
                member_name = self._decode(member[1])[:21] if member else "N/A"
                
                print(f"| {borrow_id:<10} | {book_id:<8} | {member_id:<8} | {book_title:<33} | {member_name:<23} | {borrow_date:<10} |")
                currently_borrowed += 1
        
        print("+" + "-"*12 + "+" + "-"*10 + "+" + "-"*10 + "+" + "-"*35 + "+" + "-"*25 + "+" + "-"*12 + "+")
        print()
        
        # สถิติการยืม
        total_borrows = len(borrows_data)
        returned_borrows = sum(1 for b in borrows_data if b[5] == b'R')
        
        print("Borrowing Summary")
        print(f"- Total Borrow Records  : {total_borrows}")
        print(f"- Currently Borrowed    : {currently_borrowed}")
        print(f"- Returned              : {returned_borrows}")
        print()
        
        # สถิติเพิ่มเติม - หนังสือที่ถูกยืมบ่อย
        print("Most Borrowed Books (Top 5)")
        borrow_count = {}
        for borrow in borrows_data:
            book_id = self._decode(borrow[1])
            borrow_count[book_id] = borrow_count.get(book_id, 0) + 1
        
        sorted_books = sorted(borrow_count.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (book_id, count) in enumerate(sorted_books, 1):
            book = self._find_book(book_id)
            if book:
                title = self._decode(book[1])[:40]
                print(f"{i}. {title} (ยืม {count} ครั้ง)")
        
        if not sorted_books:
            print("ยังไม่มีข้อมูลการยืม")
        
        print()
        print("="*90)
    
    # ==================== ฟังก์ชันช่วย ====================
    
    def _find_book(self, book_id: str) -> Optional[Tuple]:
        """หาหนังสือจาก ID"""
        if not os.path.exists(self.books_file):
            return None
        
        with open(self.books_file, 'rb') as f:
            while True:
                data = f.read(self.book_size)
                if not data:
                    break
                book = struct.unpack(self.book_format, data)
                if self._decode(book[0]) == book_id and book[5] == b'0':
                    return book
        return None
    
    def _find_member(self, member_id: str) -> Optional[Tuple]:
        """หาสมาชิกจาก ID"""
        if not os.path.exists(self.members_file):
            return None
        
        with open(self.members_file, 'rb') as f:
            while True:
                data = f.read(self.member_size)
                if not data:
                    break
                member = struct.unpack(self.member_format, data)
                if self._decode(member[0]) == member_id and member[5] == b'0':
                    return member
        return None
    
    def _find_active_borrow(self, book_id: str) -> Optional[Tuple[int, Tuple]]:
        """หารายการยืมที่ยังไม่คืน"""
        if not os.path.exists(self.borrows_file):
            return None
        
        with open(self.borrows_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.borrow_size)
                if not data:
                    break
                borrow = struct.unpack(self.borrow_format, data)
                if self._decode(borrow[1]) == book_id and borrow[5] == b'B' and borrow[6] == b'0':
                    return (index, borrow)
                index += 1
        return None
    
    def _update_book_status(self, book_id: str, status: bytes):
        """อัปเดตสถานะหนังสือ"""
        if not os.path.exists(self.books_file):
            return
        
        with open(self.books_file, 'r+b') as f:
            index = 0
            while True:
                data = f.read(self.book_size)
                if not data:
                    break
                
                book = struct.unpack(self.book_format, data)
                if self._decode(book[0]) == book_id and book[5] == b'0':
                    updated = struct.pack(
                        self.book_format,
                        book[0], book[1], book[2], book[3],
                        status,
                        book[5]
                    )
                    f.seek(index * self.book_size)
                    f.write(updated)
                    break
                index += 1
    
    def show_stats(self):
        """แสดงสถิติสรุป"""
        print("\n=== สถิติระบบ ===")
        
        # นับหนังสือ
        total_books = 0
        available_books = 0
        
        if os.path.exists(self.books_file):
            with open(self.books_file, 'rb') as f:
                while True:
                    data = f.read(self.book_size)
                    if not data:
                        break
                    book = struct.unpack(self.book_format, data)
                    if book[5] == b'0':
                        total_books += 1
                        if book[4] == b'A':
                            available_books += 1
        
        # นับสมาชิก
        total_members = 0
        if os.path.exists(self.members_file):
            with open(self.members_file, 'rb') as f:
                while True:
                    data = f.read(self.member_size)
                    if not data:
                        break
                    member = struct.unpack(self.member_format, data)
                    if member[5] == b'0' and member[4] == b'A':
                        total_members += 1
        
        # นับรายการยืม
        active_borrows = 0
        if os.path.exists(self.borrows_file):
            with open(self.borrows_file, 'rb') as f:
                while True:
                    data = f.read(self.borrow_size)
                    if not data:
                        break
                    borrow = struct.unpack(self.borrow_format, data)
                    if borrow[5] == b'B' and borrow[6] == b'0':
                        active_borrows += 1
        
        print(f"📚 หนังสือทั้งหมด: {total_books} เล่ม")
        print(f"   - ว่าง: {available_books} เล่ม")
        print(f"   - ถูกยืม: {total_books - available_books} เล่ม")
        print(f"\n👥 สมาชิก: {total_members} คน")
        print(f"\n📋 กำลังยืม: {active_borrows} รายการ")
    
    # ==================== เมนู ====================
    
    def run(self):
        """เรียกใช้งานระบบ"""
        while True:
            print("\n" + "=" * 50)
            print("📚 ระบบห้องสมุด")
            print("=" * 50)
            print("1. จัดการหนังสือ")
            print("2. จัดการสมาชิก")
            print("3. ยืม-คืนหนังสือ")
            print("4. ดูสถิติ")
            print("5. สร้างรายงานสรุป (Summary Report)")
            print("0. ออก")
            print("-" * 50)
            
            choice = input("เลือก: ").strip()
            
            if choice == '1':
                self._book_menu()
            elif choice == '2':
                self._member_menu()
            elif choice == '3':
                self._borrow_menu()
            elif choice == '4':
                self.show_stats()
                input("\nกด Enter...")
            elif choice == '5':
                self.generate_summary_report()
                input("\nกด Enter...")
            elif choice == '0':
                print("\n👋 ขอบคุณที่ใช้บริการ!")
                break
    
    def _book_menu(self):
        """เมนูหนังสือ"""
        while True:
            print("\n" + "=" * 40)
            print("📚 จัดการหนังสือ")
            print("=" * 40)
            print("1. เพิ่มหนังสือ")
            print("2. ดูรายการหนังสือ")
            print("3. ค้นหาหนังสือ")
            print("4. แก้ไขหนังสือ")
            print("5. ลบหนังสือ")
            print("0. กลับ")
            print("-" * 40)
            
            choice = input("เลือกเมนู (0-5): ").strip()
            
            if choice == '1':
                self.add_book()
                input("\n✓ กด Enter เพื่อดำเนินการต่อ...")
            elif choice == '2':
                self.list_books()
                input("\n✓ กด Enter เพื่อกลับเมนู...")
            elif choice == '3':
                self.search_book()
                input("\n✓ กด Enter เพื่อกลับเมนู...")
            elif choice == '4':
                self.update_book()
                input("\n✓ กด Enter เพื่อดำเนินการต่อ...")
            elif choice == '5':
                self.delete_book()
                input("\n✓ กด Enter เพื่อดำเนินการต่อ...")
            elif choice == '0':
                break
            else:
                print("❌ กรุณาเลือก 0-5 เท่านั้น")
                input("\nกด Enter...")

    
    def _member_menu(self):
        """เมนูสมาชิก"""
        while True:
            print("\n" + "=" * 40)
            print("👥 จัดการสมาชิก")
            print("=" * 40)
            print("1. เพิ่มสมาชิก")
            print("2. ดูรายการสมาชิก")
            print("3. ลบสมาชิก")
            print("0. กลับ")
            print("-" * 40)
            
            choice = input("เลือกเมนู (0-3): ").strip()
            
            if choice == '1':
                self.add_member()
                input("\n✓ กด Enter เพื่อดำเนินการต่อ...")
            elif choice == '2':
                self.list_members()
                input("\n✓ กด Enter เพื่อกลับเมนู...")
            elif choice == '3':
                self.delete_member()
                input("\n✓ กด Enter เพื่อดำเนินการต่อ...")
            elif choice == '0':
                break
            else:
                print("❌ กรุณาเลือก 0-3 เท่านั้น")
                input("\nกด Enter...")
    
    def _borrow_menu(self):
        """เมนูยืม-คืน"""
        while True:
            print("\n--- ยืม-คืนหนังสือ ---")
            print("1. ยืมหนังสือ")
            print("2. คืนหนังสือ")
            print("3. ดูรายการยืม")
            print("0. กลับ")
            
            choice = input("เลือก: ").strip()
            
            if choice == '1':
                self.borrow_book()
            elif choice == '2':
                self.return_book()
            elif choice == '3':
                self.list_borrows()
                input("\nกด Enter...")
            elif choice == '0':
                break


if __name__ == "__main__":
    lib = SimpleLibrary()
    lib.run()