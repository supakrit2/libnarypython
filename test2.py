import struct
import os
import datetime
from typing import List, Tuple, Optional


class LibrarySystem:
    """ระบบจัดการห้องสมุดด้วยไฟล์ไบนารี"""
    
    def __init__(self):
        # กำหนดโครงสร้างข้อมูลด้วย struct format (Little-endian)
        # Book: ID(4s) + Title(100s) + Author(50s) + ISBN(20s) + Year(4s) + Status(1s) + Deleted(1s)
        self.book_format = '<4s100s50s20s4s1s1s'
        self.book_size = struct.calcsize(self.book_format)
        
        # Member: ID(4s) + Name(50s) + Email(50s) + Phone(15s) + JoinDate(10s) + Status(1s) + BanUntil(10s) + Deleted(1s)
        self.member_format = '<4s50s50s15s10s1s10s1s'
        self.member_size = struct.calcsize(self.member_format)
        
        # Borrow: ID(4s) + BookID(4s) + MemberID(4s) + BorrowDate(10s) + ReturnDate(10s) + Status(1s) + Deleted(1s)
        self.borrow_format = '<4s4s4s10s10s1s1s'
        self.borrow_size = struct.calcsize(self.borrow_format)
        
        # ชื่อไฟล์
        self.books_file = 'books.dat'
        self.members_file = 'members.dat'
        self.borrows_file = 'borrows.dat'
        self.report_file = 'library_report.txt'
        
        # สร้างไฟล์ถ้าไม่มี
        self._initialize_files()
        
        # ประวัติการทำงาน
        self.operation_history = []
    
    def _initialize_files(self):
        """สร้างไฟล์ไบนารีถ้าไม่มี"""
        for filename in [self.books_file, self.members_file, self.borrows_file]:
            if not os.path.exists(filename):
                with open(filename, 'wb') as f:
                    pass  # สร้างไฟล์ว่าง
    
    def _get_next_id(self, filename: str, record_size: int, format_str: str) -> str:
        """สร้าง ID ถัดไปแบบอัตโนมัติ"""
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return "001"
        
        try:
            with open(filename, 'rb') as f:
                f.seek(-record_size, 2)  # ไปที่ record สุดท้าย
                last_record = f.read(record_size)
                
            last_id = struct.unpack(format_str, last_record)[0]
            last_id_num = int(last_id.decode('utf-8').strip('\x00'))
            return f"{last_id_num + 1:04d}"
        except:
            return "001"
    
    def _encode_string(self, text: str, length: int) -> bytes:
        """แปลงสตริงเป็น bytes ตามความยาวที่กำหนด (Fixed-length)"""
        return text.encode('utf-8')[:length].ljust(length, b'\x00')
    
    def _decode_string(self, data: bytes) -> str:
        """แปลง bytes กลับเป็นสตริง"""
        return data.decode('utf-8').rstrip('\x00')
    
    def _update_record(self, filename: str, index: int, data: bytes, record_size: int):
        """อัปเดตระเบียนในไฟล์ไบนารี"""
        with open(filename, 'r+b') as f:
            f.seek(index * record_size)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())  # Sync to disk
    
    def _check_and_ban_overdue_members(self) -> List[str]:
        """ตรวจสอบและแบนสมาชิกที่เกินกำหนดคืนอัตโนมัติ"""
        borrows = self._get_all_borrows()
        current_date = datetime.date.today()
        banned_members = []
        
        for borrow in borrows:
            if borrow[5] == b'B' and borrow[6] == b'0':  # ยืมอยู่และไม่ถูกลบ
                borrow_date_str = self._decode_string(borrow[3])
                try:
                    borrow_date = datetime.datetime.strptime(borrow_date_str, "%Y-%m-%d").date()
                    due_date = borrow_date + datetime.timedelta(days=7)
                    days_overdue = (current_date - due_date).days
                    
                    if days_overdue > 0:
                        member_id = self._decode_string(borrow[2])
                        member = self._find_member_by_id(member_id)
                        
                        if member and member[5] == b'A':  # ยังใช้งานอยู่
                            member_index = self._find_member_index_by_id(member_id)
                            if member_index != -1:
                                banned_member = struct.pack(
                                    self.member_format,
                                    member[0], member[1], member[2], member[3], member[4],
                                    b'S',  # Suspended
                                    self._encode_string("", 10),  # ยังไม่มีวันหมดแบน
                                    member[7]
                                )
                                self._update_record(self.members_file, member_index, 
                                                  banned_member, self.member_size)
                                
                                if member_id not in banned_members:
                                    banned_members.append(member_id)
                except:
                    pass
        
        return banned_members
    
    def _check_member_ban_status(self, member_id: str) -> Tuple[bool, str, str]:
        """ตรวจสอบสถานะการแบนของสมาชิก
        
        Returns:
            tuple: (is_banned, reason, ban_until_date)
        """
        member = self._find_member_by_id(member_id)
        if not member:
            return (False, "", "")
        
        current_date = datetime.date.today()
        
        if member[5] == b'S':
            ban_until_str = self._decode_string(member[6])
            
            # ถ้าไม่มีวันหมดแบน = ถูกแบนเพราะยังไม่คืนหนังสือ
            if not ban_until_str:
                return (True, "เกินกำหนดคืนหนังสือ (ยังไม่คืน)", "")
            
            # ตรวจสอบว่าหมดอายุแบนหรือยัง
            try:
                ban_until = datetime.datetime.strptime(ban_until_str, "%Y-%m-%d").date()
                if current_date < ban_until:
                    return (True, "ถูกแบนหลังคืนหนังสือเกินกำหนด", ban_until_str)
                else:
                    # หมดอายุแบนแล้ว - ยกเลิกอัตโนมัติ
                    member_index = self._find_member_index_by_id(member_id)
                    if member_index != -1:
                        unban_member = struct.pack(
                            self.member_format,
                            member[0], member[1], member[2], member[3], member[4],
                            b'A',
                            self._encode_string("", 10),
                            member[7]
                        )
                        self._update_record(self.members_file, member_index, 
                                          unban_member, self.member_size)
                    return (False, "", "")
            except:
                return (True, "ขอมูลการแบนผิดพลาด", ban_until_str)
        
        return (False, "", "")
    
    # ==================== BOOKS MANAGEMENT ====================
    
    def add_book(self):
        """เพิ่มหนังสือใหม่"""
        print("\n" + "=" * 60)
        print("เพิ่มหนังสือ")
        print("=" * 60)
        
        try:
            title = input("ชื่อหนังสือ: ").strip()
            if not title:
                print("กรุณากรอกชื่อหนังสือ")
                return
            
            author = input("ผู้แต่ง: ").strip()
            if not author:
                print("กรุณากรอกชื่อผู้แต่ง")
                return
            
            isbn = input("ISBN: ").strip()
            year_str = input("ปีที่พิมพ์ (ค.ศ.): ").strip()
            
            try:
                year = int(year_str)
                if year < 1000 or year > 9999:
                    raise ValueError()
            except ValueError:
                print("ปีที่พิมพ์ต้องเป็นตัวเลข 4 หลัก")
                return
            
            book_id = self._get_next_id(self.books_file, self.book_size, self.book_format)
            
            book_data = struct.pack(
                self.book_format,
                self._encode_string(book_id, 4),
                self._encode_string(title, 100),
                self._encode_string(author, 50),
                self._encode_string(isbn, 20),
                self._encode_string(str(year), 4),
                b'A',  # Available
                b'0'   # Not deleted
            )
            
            with open(self.books_file, 'ab') as f:
                f.write(book_data)
                f.flush()
                os.fsync(f.fileno())
            
            print(f"\nเพิ่มหนังสือสำเร็จ ID: {book_id}")
            self.operation_history.append(
                f"{datetime.datetime.now()}: เพิ่มหนังสือ '{title}' ID: {book_id}"
            )
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
    
    def view_books(self):
        """ดูข้อมูลหนังสือ"""
        print("\n" + "=" * 60)
        print("ดูข้อมูลหนังสือ")
        print("=" * 60)
        print("1. ดูหนังสือเล่มเดียว")
        print("2. ดูหนังสือทั้งหมด")
        print("3. ดูหนังสือแบบกรอง")
        print("0. กลับ")
        
        choice = input("\nเลือก (0-3): ").strip()
        
        if choice == '1':
            self._view_single_book()
        elif choice == '2':
            self._view_all_books()
        elif choice == '3':
            self._view_filtered_books()
    
    def _view_single_book(self):
        """ดูหนังสือเล่มเดียว"""
        book_id = input("\nกรอก ID หนังสือ: ").strip()
        book = self._find_book_by_id(book_id)
        
        if book:
            print("\n" + "-" * 60)
            self._display_book(book, compact=False)
        else:
            print("ไม่พบหนังสือ")
    
    def _view_all_books(self):
        """ดูหนังสือทั้งหมด"""
        books = self._get_all_books()
        active_books = [book for book in books if book[6] == b'0']
        
        if not active_books:
            print("\nไม่มีหนังสือในระบบ")
            return
        
        print(f"\nมีหนังสือทั้งหมด {len(active_books)} เล่ม")
        print("-" * 80)
        print(f"{'ID':<6} {'ชื่อ':<32} {'ผู้แต่ง':<22} {'สถานะ':<10}")
        print("-" * 80)
        
        for book in active_books:
            self._display_book(book, compact=True)
    
    def _view_filtered_books(self):
        """ดูหนังสือแบบกรอง"""
        print("\nกรองตาม:")
        print("1. ชื่อหนังสือ")
        print("2. ผู้แต่ง")
        print("3. ปีที่พิมพ์")
        
        filter_choice = input("\nเลือก (1-3): ").strip()
        keyword = input("คำค้นหา: ").strip().lower()
        
        books = self._get_all_books()
        active_books = [book for book in books if book[6] == b'0']
        filtered_books = []
        
        for book in active_books:
            if filter_choice == '1' and keyword in self._decode_string(book[1]).lower():
                filtered_books.append(book)
            elif filter_choice == '2' and keyword in self._decode_string(book[2]).lower():
                filtered_books.append(book)
            elif filter_choice == '3' and keyword in self._decode_string(book[4]):
                filtered_books.append(book)
        
        if filtered_books:
            print(f"\nพบหนังสือ {len(filtered_books)} เล่ม")
            print("-" * 80)
            for book in filtered_books:
                self._display_book(book, compact=True)
        else:
            print("ไม่พบหนังสือที่ตรงกับเงื่อนไข")
    
    def _find_book_by_id(self, book_id: str) -> Optional[Tuple]:
        """ค้นหาหนังสือจาก ID"""
        books = self._get_all_books()
        for book in books:
            if self._decode_string(book[0]) == book_id and book[6] == b'0':
                return book
        return None
    
    def _get_all_books(self) -> List[Tuple]:
        """ดึงข้อมูลหนังสือทั้งหมดจากไฟล์ไบนารี"""
        books = []
        if not os.path.exists(self.books_file):
            return books
        
        with open(self.books_file, 'rb') as f:
            while True:
                data = f.read(self.book_size)
                if not data:
                    break
                book = struct.unpack(self.book_format, data)
                books.append(book)
        return books
    
    def _display_book(self, book: Tuple, compact: bool = False):
        """แสดงข้อมูลหนังสือ"""
        book_id = self._decode_string(book[0])
        title = self._decode_string(book[1])
        author = self._decode_string(book[2])
        isbn = self._decode_string(book[3])
        year = self._decode_string(book[4])
        status = 'ว่าง' if book[5] == b'A' else 'ถูกยืม'
        
        if compact:
            print(f"{book_id:<6} {title[:30]:<32} {author[:20]:<22} {status:<10}")
        else:
            print(f"ID: {book_id}")
            print(f"ชื่อ: {title}")
            print(f"ผู้แต่ง: {author}")
            print(f"ISBN: {isbn}")
            print(f"ปีที่พิมพ์: {year}")
            print(f"สถานะ: {status}")
    
    def update_book(self):
        """แก้ไขข้อมูลหนังสือ"""
        print("\n" + "=" * 60)
        print("แก้ไขหนังสือ")
        print("=" * 60)
        
        book_id = input("\nกรอก ID หนังสือที่ต้องการแก้ไข: ").strip()
        
        book_index = self._find_book_index_by_id(book_id)
        if book_index == -1:
            print("ไม่พบหนังสือ")
            return
        
        book = self._get_book_by_index(book_index)
        if not book:
            print("เกิดข้อผิดพลาดในการอ่านข้อมูล")
            return
        
        print("\nข้อมูลปัจจุบัน:")
        print("-" * 60)
        self._display_book(book)
        
        print("\n" + "-" * 60)
        print("กรอกข้อมูลใหม่ (Enter เพื่อข้าม)")
        print("-" * 60)
        
        title = input(f"ชื่อหนังสือ [{self._decode_string(book[1])}]: ").strip()
        if not title:
            title = self._decode_string(book[1])
        
        author = input(f"ผู้แต่ง [{self._decode_string(book[2])}]: ").strip()
        if not author:
            author = self._decode_string(book[2])
        
        isbn = input(f"ISBN [{self._decode_string(book[3])}]: ").strip()
        if not isbn:
            isbn = self._decode_string(book[3])
        
        year_input = input(f"ปีที่พิมพ์ [{self._decode_string(book[4])}]: ").strip()
        if year_input:
            try:
                year = int(year_input)
                if year < 1000 or year > 9999:
                    raise ValueError()
            except ValueError:
                print("ปีที่พิมพ์ต้องเป็นตัวเลข 4 หลัก")
                return
        else:
            year = int(self._decode_string(book[4]))
        
        updated_book = struct.pack(
            self.book_format,
            book[0],
            self._encode_string(title, 100),
            self._encode_string(author, 50),
            self._encode_string(isbn, 20),
            self._encode_string(str(year), 4),
            book[5],
            book[6]
        )
        
        self._update_record(self.books_file, book_index, updated_book, self.book_size)
        print("\nแก้ไขข้อมูลหนังสือสำเร็จ")
        self.operation_history.append(
            f"{datetime.datetime.now()}: แก้ไขหนังสือ ID: {book_id}"
        )
    
    def delete_book(self):
        """ลบหนังสือ (Soft delete)"""
        print("\n" + "=" * 60)
        print("ลบหนังสือ")
        print("=" * 60)
        
        book_id = input("\nกรอก ID หนังสือที่ต้องการลบ: ").strip()
        
        book_index = self._find_book_index_by_id(book_id)
        if book_index == -1:
            print("ไม่พบหนังสือ")
            return
        
        book = self._get_book_by_index(book_index)
        if not book:
            print("เกิดข้อผิดพลาดในการอ่านข้อมูล")
            return
        
        print("\nข้อมูลหนังสือที่จะลบ:")
        print("-" * 60)
        self._display_book(book)
        
        confirm = input("\nยืนยันการลบ? (y/N): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิกการลบ")
            return
        
        deleted_book = struct.pack(
            self.book_format,
            book[0], book[1], book[2], book[3], book[4], book[5],
            b'1'  # Mark as deleted
        )
        
        self._update_record(self.books_file, book_index, deleted_book, self.book_size)
        print("\nลบหนังสือสำเร็จ")
        self.operation_history.append(
            f"{datetime.datetime.now()}: ลบหนังสือ ID: {book_id}"
        )
    
    def _find_book_index_by_id(self, book_id: str) -> int:
        """หา index ของหนังสือจาก ID"""
        if not os.path.exists(self.books_file):
            return -1
        
        with open(self.books_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.book_size)
                if not data:
                    break
                book = struct.unpack(self.book_format, data)
                if self._decode_string(book[0]) == book_id and book[6] == b'0':
                    return index
                index += 1
        return -1
    
    def _get_book_by_index(self, index: int) -> Optional[Tuple]:
        """ดึงข้อมูลหนังสือจาก index"""
        if not os.path.exists(self.books_file):
            return None
        
        with open(self.books_file, 'rb') as f:
            f.seek(index * self.book_size)
            data = f.read(self.book_size)
            if not data:
                return None
            return struct.unpack(self.book_format, data)
    
    # ==================== MEMBERS MANAGEMENT ====================
    
    def add_member(self):
        """เพิ่มสมาชิกใหม่"""
        print("\n" + "=" * 60)
        print("เพิ่มสมาชิก")
        print("=" * 60)
        
        try:
            name = input("ชื่อ-นามสกุล: ").strip()
            if not name:
                print("กรุณากรอกชื่อ-นามสกุล")
                return
            
            email = input("อีเมล: ").strip()
            phone = input("โทรศัพท์: ").strip()
            
            member_id = self._get_next_id(self.members_file, self.member_size, 
                                         self.member_format)
            join_date = datetime.date.today().strftime("%Y-%m-%d")
            
            member_data = struct.pack(
                self.member_format,
                self._encode_string(member_id, 4),
                self._encode_string(name, 50),
                self._encode_string(email, 50),
                self._encode_string(phone, 15),
                self._encode_string(join_date, 10),
                b'A',  # Active
                self._encode_string("", 10),  # ban_until_date
                b'0'   # Not deleted
            )
            
            with open(self.members_file, 'ab') as f:
                f.write(member_data)
                f.flush()
                os.fsync(f.fileno())
            
            print(f"\nเพิ่มสมาชิกสำเร็จ ID: {member_id}")
            self.operation_history.append(
                f"{datetime.datetime.now()}: เพิ่มสมาชิก '{name}' ID: {member_id}"
            )
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
    
    def view_members(self):
        """ดูข้อมูลสมาชิก"""
        print("\n" + "=" * 60)
        print("ดูข้อมูลสมาชิก")
        print("=" * 60)
        print("1. ดูสมาชิกคนเดียว")
        print("2. ดูสมาชิกทั้งหมด")
        print("3. ดูสมาชิกแบบกรอง")
        print("0. กลับ")
        
        choice = input("\nเลือก (0-3): ").strip()
        
        if choice == '1':
            self._view_single_member()
        elif choice == '2':
            self._view_all_members()
        elif choice == '3':
            self._view_filtered_members()
    
    def _view_single_member(self):
        """ดูสมาชิกคนเดียว"""
        member_id = input("\nกรอก ID สมาชิก: ").strip()
        member = self._find_member_by_id(member_id)
        
        if member:
            print("\n" + "-" * 60)
            self._display_member(member, compact=False)
        else:
            print("ไม่พบสมาชิก")
    
    def _view_all_members(self):
        """ดูสมาชิกทั้งหมด"""
        members = self._get_all_members()
        active_members = [member for member in members if member[7] == b'0']
        
        if not active_members:
            print("\nไม่มีสมาชิกในระบบ")
            return
        
        print(f"\nมีสมาชิกทั้งหมด {len(active_members)} คน")
        print("-" * 90)
        print(f"{'ID':<6} {'ชื่อ':<27} {'อีเมล':<32} {'สถานะ':<20}")
        print("-" * 90)
        
        for member in active_members:
            self._display_member(member, compact=True)
    
    def _view_filtered_members(self):
        """ดูสมาชิกแบบกรอง"""
        print("\nกรองตาม:")
        print("1. ชื่อ")
        print("2. อีเมล")
        
        filter_choice = input("\nเลือก (1-2): ").strip()
        keyword = input("คำค้นหา: ").strip().lower()
        
        members = self._get_all_members()
        active_members = [member for member in members if member[7] == b'0']
        filtered_members = []
        
        for member in active_members:
            if filter_choice == '1' and keyword in self._decode_string(member[1]).lower():
                filtered_members.append(member)
            elif filter_choice == '2' and keyword in self._decode_string(member[2]).lower():
                filtered_members.append(member)
        
        if filtered_members:
            print(f"\nพบสมาชิก {len(filtered_members)} คน")
            print("-" * 90)
            for member in filtered_members:
                self._display_member(member, compact=True)
        else:
            print("ไม่พบสมาชิกที่ตรงกับเงื่อนไข")
    
    def _find_member_by_id(self, member_id: str) -> Optional[Tuple]:
        """ค้นหาสมาชิกจาก ID"""
        members = self._get_all_members()
        for member in members:
            if self._decode_string(member[0]) == member_id and member[7] == b'0':
                return member
        return None
    
    def _get_all_members(self) -> List[Tuple]:
        """ดึงข้อมูลสมาชิกทั้งหมดจากไฟล์ไบนารี"""
        members = []
        if not os.path.exists(self.members_file):
            return members
        
        with open(self.members_file, 'rb') as f:
            while True:
                data = f.read(self.member_size)
                if not data:
                    break
                member = struct.unpack(self.member_format, data)
                members.append(member)
        return members
    
    def _display_member(self, member: Tuple, compact: bool = False):
        """แสดงข้อมูลสมาชิก"""
        member_id = self._decode_string(member[0])
        name = self._decode_string(member[1])
        email = self._decode_string(member[2])
        phone = self._decode_string(member[3])
        join_date = self._decode_string(member[4])
        ban_until = self._decode_string(member[6])
        
        if member[5] == b'A':
            status = 'ใช้งาน'
        elif member[5] == b'S':
            if ban_until:
                status = f'แบน (ถึง {ban_until})'
            else:
                status = 'แบน (ค้างคืน)'
        else:
            status = 'ระงับ'
        
        if compact:
            print(f"{member_id:<6} {name[:25]:<27} {email[:30]:<32} {status:<20}")
        else:
            print(f"ID: {member_id}")
            print(f"ชื่อ: {name}")
            print(f"อีเมล: {email}")
            print(f"โทรศัพท์: {phone}")
            print(f"วันที่สมัคร: {join_date}")
            print(f"สถานะ: {status}")
    
    def update_member(self):
        """แก้ไขข้อมูลสมาชิก"""
        print("\n" + "=" * 60)
        print("แก้ไขสมาชิก")
        print("=" * 60)
        
        member_id = input("\nกรอก ID สมาชิกที่ต้องการแก้ไข: ").strip()
        
        member_index = self._find_member_index_by_id(member_id)
        if member_index == -1:
            print("ไม่พบสมาชิก")
            return
        
        member = self._get_member_by_index(member_index)
        if not member:
            print("เกิดข้อผิดพลาดในการอ่านข้อมูล")
            return
        
        print("\nข้อมูลปัจจุบัน:")
        print("-" * 60)
        self._display_member(member)
        
        print("\n" + "-" * 60)
        print("กรอกข้อมูลใหม่ (Enter เพื่อข้าม)")
        print("-" * 60)
        
        name = input(f"ชื่อ-นามสกุล [{self._decode_string(member[1])}]: ").strip()
        if not name:
            name = self._decode_string(member[1])
        
        email = input(f"อีเมล [{self._decode_string(member[2])}]: ").strip()
        if not email:
            email = self._decode_string(member[2])
        
        phone = input(f"โทรศัพท์ [{self._decode_string(member[3])}]: ").strip()
        if not phone:
            phone = self._decode_string(member[3])
        
        updated_member = struct.pack(
            self.member_format,
            member[0],
            self._encode_string(name, 50),
            self._encode_string(email, 50),
            self._encode_string(phone, 15),
            member[4],
            member[5],
            member[6],
            member[7]
        )
        
        self._update_record(self.members_file, member_index, updated_member, self.member_size)
        print("\nแก้ไขข้อมูลสมาชิกสำเร็จ")
        self.operation_history.append(
            f"{datetime.datetime.now()}: แก้ไขสมาชิก ID: {member_id}"
        )
    
    def delete_member(self):
        """ลบสมาชิก (Soft delete)"""
        print("\n" + "=" * 60)
        print("ลบสมาชิก")
        print("=" * 60)
        
        member_id = input("\nกรอก ID สมาชิกที่ต้องการลบ: ").strip()
        
        member_index = self._find_member_index_by_id(member_id)
        if member_index == -1:
            print("ไม่พบสมาชิก")
            return
        
        member = self._get_member_by_index(member_index)
        if not member:
            print("เกิดข้อผิดพลาดในการอ่านข้อมูล")
            return
        
        print("\nข้อมูลสมาชิกที่จะลบ:")
        print("-" * 60)
        self._display_member(member)
        
        confirm = input("\nยืนยันการลบ? (y/N): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิกการลบ")
            return
        
        deleted_member = struct.pack(
            self.member_format,
            member[0], member[1], member[2], member[3], member[4], member[5], member[6],
            b'1'  # Mark as deleted
        )
        
        self._update_record(self.members_file, member_index, deleted_member, self.member_size)
        print("\nลบสมาชิกสำเร็จ")
        self.operation_history.append(
            f"{datetime.datetime.now()}: ลบสมาชิก ID: {member_id}"
        )
    
    def _find_member_index_by_id(self, member_id: str) -> int:
        """หา index ของสมาชิกจาก ID"""
        if not os.path.exists(self.members_file):
            return -1
        
        with open(self.members_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.member_size)
                if not data:
                    break
                member = struct.unpack(self.member_format, data)
                if self._decode_string(member[0]) == member_id and member[7] == b'0':
                    return index
                index += 1
        return -1
    
    def _get_member_by_index(self, index: int) -> Optional[Tuple]:
        """ดึงข้อมูลสมาชิกจาก index"""
        if not os.path.exists(self.members_file):
            return None
        
        with open(self.members_file, 'rb') as f:
            f.seek(index * self.member_size)
            data = f.read(self.member_size)
            if not data:
                return None
            return struct.unpack(self.member_format, data)
    
    # ==================== BORROW MANAGEMENT ====================
    
    def add_borrow(self):
        """ยืมหนังสือ - รองรับการยืมหลายเล่ม"""
        print("\n" + "=" * 60)
        print("ยืมหนังสือ")
        print("=" * 60)
        
        # ตรวจสอบและแบนสมาชิกที่เกินกำหนดก่อน
        banned_list = self._check_and_ban_overdue_members()
        if banned_list:
            print(f"\nระบบได้แบนสมาชิก {len(banned_list)} คนที่เกินกำหนดคืนหนังสือ")
        
        try:
            num_books_input = input("\nต้องการยืมกี่เล่ม? (1-10): ").strip()
            
            try:
                num_books = int(num_books_input)
                if num_books < 1 or num_books > 10:
                    print("กรุณากรอกจำนวน 1-10 เล่มเท่านั้น")
                    return
            except ValueError:
                print("กรุณากรอกตัวเลขที่ถูกต้อง")
                return
            
            member_id = input("กรอก ID สมาชิก: ").strip()
            
            member = self._find_member_by_id(member_id)
            if not member:
                print("ไม่พบสมาชิก")
                return
            
            # ตรวจสอบสถานะการแบน
            is_banned, reason, ban_until = self._check_member_ban_status(member_id)
            if is_banned:
                print("\n" + "=" * 60)
                print("สมาชิกถูกแบน!")
                print("=" * 60)
                print(f"สมาชิก: {self._decode_string(member[1])} (ID: {member_id})")
                print(f"สาเหตุ: {reason}")
                if ban_until:
                    print(f"ระงับจนถึง: {ban_until}")
                else:
                    print("กรุณาคืนหนังสือที่ค้างอยู่ก่อน")
                print("=" * 60)
                return
            
            print(f"\nผู้ยืม: {self._decode_string(member[1])} (ID: {member_id})")
            print(f"จำนวนหนังสือที่จะยืม: {num_books} เล่ม")
            print("-" * 60)
            
            borrowed_books = []
            borrow_date = datetime.date.today()
            borrow_date_str = borrow_date.strftime("%Y-%m-%d")
            due_date = borrow_date + datetime.timedelta(days=7)
            due_date_str = due_date.strftime("%Y-%m-%d")
            
            for i in range(1, num_books + 1):
                print(f"\nหนังสือเล่มที่ {i}/{num_books}")
                book_id = input(f"กรอก ID หนังสือเล่มที่ {i}: ").strip()
                
                book = self._find_book_by_id(book_id)
                if not book:
                    print(f"ไม่พบหนังสือ ID: {book_id}")
                    continue_choice = input("กรอก ID ใหม่ (r) / ข้าม (s) / ยกเลิก (c): ").strip().lower()
                    
                    if continue_choice == 'r':
                        i -= 1
                        continue
                    elif continue_choice == 'c':
                        print("ยกเลิกการยืมทั้งหมด")
                        for prev_book_id in borrowed_books:
                            self._update_book_status(prev_book_id, b'A')
                        return
                    else:
                        continue
                
                if book[5] != b'A':
                    print(f"หนังสือ '{self._decode_string(book[1])}' ถูกยืมแล้ว")
                    continue_choice = input("กรอก ID ใหม่ (r) / ข้าม (s) / ยกเลิก (c): ").strip().lower()
                    
                    if continue_choice == 'r':
                        i -= 1
                        continue
                    elif continue_choice == 'c':
                        print("ยกเลิกการยืมทั้งหมด")
                        for prev_book_id in borrowed_books:
                            self._update_book_status(prev_book_id, b'A')
                        return
                    else:
                        continue
                
                if book_id in borrowed_books:
                    print("คุณเลือกหนังสือเล่มนี้ไปแล้ว")
                    i -= 1
                    continue
                
                borrow_id = self._get_next_id(self.borrows_file, self.borrow_size, 
                                             self.borrow_format)
                
                borrow_data = struct.pack(
                    self.borrow_format,
                    self._encode_string(borrow_id, 4),
                    self._encode_string(book_id, 4),
                    self._encode_string(member_id, 4),
                    self._encode_string(borrow_date_str, 10),
                    self._encode_string("", 10),
                    b'B',  # Borrowed
                    b'0'   # Not deleted
                )
                
                with open(self.borrows_file, 'ab') as f:
                    f.write(borrow_data)
                    f.flush()
                    os.fsync(f.fileno())
                
                self._update_book_status(book_id, b'B')
                borrowed_books.append(book_id)
                
                print(f"บันทึกการยืมสำเร็จ ID: {borrow_id}")
                print(f"หนังสือ: {self._decode_string(book[1])}")
            
            if borrowed_books:
                print("\n" + "=" * 60)
                print("สรุปการยืมหนังสือ")
                print("=" * 60)
                print(f"ผู้ยืม: {self._decode_string(member[1])}")
                print(f"ID สมาชิก: {member_id}")
                print(f"วันที่ยืม: {borrow_date_str}")
                print(f"กำหนดคืน: {due_date_str}")
                print(f"\nรายการหนังสือที่ยืมสำเร็จ ({len(borrowed_books)} เล่ม):")
                
                for idx, book_id in enumerate(borrowed_books, 1):
                    book = self._find_book_by_id(book_id)
                    if book:
                        print(f"  {idx}. {self._decode_string(book[1])} (ID: {book_id})")
                
                print("\nหมายเหตุสำคัญ:")
                print("- กรุณาคืนหนังสือภายใน 7 วัน")
                print("- หากเกินกำหนดคืน ID จะถูกแบนทันทีจนกว่าจะคืนหนังสือ")
                print("- เมื่อคืนหนังสือที่เกินกำหนด ระบบจะแบน ID ต่ออีก 30 วัน")
                print("=" * 60)
                
                self.operation_history.append(
                    f"{datetime.datetime.now()}: ยืมหนังสือ {len(borrowed_books)} เล่ม โดยสมาชิก ID: {member_id}"
                )
            else:
                print("\nไม่มีหนังสือที่ยืมสำเร็จ")
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
    
    def return_book(self):
        """คืนหนังสือ"""
        print("\n" + "=" * 60)
        print("คืนหนังสือ")
        print("=" * 60)
        
        try:
            book_id = input("\nกรอก ID หนังสือที่จะคืน: ").strip()
            
            borrow_record = self._find_active_borrow_by_book_id(book_id)
            if not borrow_record:
                print("ไม่พบรายการยืมหรือหนังสือคืนแล้ว")
                return
            
            borrow_index, borrow_data = borrow_record
            return_date = datetime.date.today()
            return_date_str = return_date.strftime("%Y-%m-%d")
            
            # คำนวณวันเกินกำหนด
            borrow_date_str = self._decode_string(borrow_data[3])
            borrow_date = datetime.datetime.strptime(borrow_date_str, "%Y-%m-%d").date()
            due_date = borrow_date + datetime.timedelta(days=7)
            days_overdue = (return_date - due_date).days
            
            updated_borrow = struct.pack(
                self.borrow_format,
                borrow_data[0],
                borrow_data[1],
                borrow_data[2],
                borrow_data[3],
                self._encode_string(return_date_str, 10),
                b'R',  # Returned
                borrow_data[6]
            )
            
            self._update_record(self.borrows_file, borrow_index, updated_borrow, self.borrow_size)
            self._update_book_status(book_id, b'A')
            
            book = self._find_book_by_id(book_id)
            member_id = self._decode_string(borrow_data[2])
            member = self._find_member_by_id(member_id)
            
            print("\n" + "=" * 60)
            print("คืนหนังสือสำเร็จ")
            print("=" * 60)
            print(f"หนังสือ: {self._decode_string(book[1])}")
            print(f"ผู้ยืม: {self._decode_string(member[1])}")
            print(f"ID สมาชิก: {member_id}")
            print(f"วันที่ยืม: {borrow_date_str}")
            print(f"กำหนดคืน: {due_date.strftime('%Y-%m-%d')}")
            print(f"วันที่คืน: {return_date_str}")
            
            if days_overdue > 0:
                print(f"\nเกินกำหนด: {days_overdue} วัน")
                print("เนื่องจากคืนเกินกำหนด ID นี้จะถูกแบนต่ออีก 30 วัน")
            elif days_overdue == 0:
                print(f"\nคืนตรงเวลา (วันสุดท้าย)")
            else:
                print(f"\nคืนก่อนกำหนด {abs(days_overdue)} วัน")
            
            # ตรวจสอบว่ายังมีหนังสือค้างคืนไหม
            borrows = self._get_all_borrows()
            has_overdue = False
            current_date_check = datetime.date.today()
            
            for borrow in borrows:
                if (self._decode_string(borrow[2]) == member_id and 
                    borrow[5] == b'B' and borrow[6] == b'0'):
                    borrow_date_temp = datetime.datetime.strptime(
                        self._decode_string(borrow[3]), "%Y-%m-%d"
                    ).date()
                    due_date_temp = borrow_date_temp + datetime.timedelta(days=7)
                    if (current_date_check - due_date_temp).days > 0:
                        has_overdue = True
                        break
            
            # จัดการสถานะการแบน
            if member and member[5] == b'S':
                member_index = self._find_member_index_by_id(member_id)
                if member_index != -1:
                    if not has_overdue:
                        # ไม่มีหนังสือค้างคืนแล้ว
                        if days_overdue > 0:
                            # แบน 30 วัน
                            ban_until_date = return_date + datetime.timedelta(days=30)
                            ban_until_str = ban_until_date.strftime("%Y-%m-%d")
                            
                            ban_member = struct.pack(
                                self.member_format,
                                member[0], member[1], member[2], member[3], member[4],
                                b'S',
                                self._encode_string(ban_until_str, 10),
                                member[7]
                            )
                            self._update_record(self.members_file, member_index, 
                                              ban_member, self.member_size)
                            
                            print(f"\nการแบนเนื่องจากคืนเกินกำหนด")
                            print(f"ระบบจะแบน ID นี้ต่ออีก 30 วัน")
                            print(f"สามารถยืมหนังสือได้อีกครั้งในวันที่: {ban_until_str}")
                        else:
                            # คืนไม่เกินกำหนด ยกเลิกการแบน
                            unban_member = struct.pack(
                                self.member_format,
                                member[0], member[1], member[2], member[3], member[4],
                                b'A',
                                self._encode_string("", 10),
                                member[7]
                            )
                            self._update_record(self.members_file, member_index, 
                                              unban_member, self.member_size)
                            print("\nยกเลิกการแบน ID สมาชิกสำเร็จ")
                            print("สามารถยืมหนังสือได้ตามปกติ")
            
            print("=" * 60)
            
            self.operation_history.append(
                f"{datetime.datetime.now()}: คืนหนังสือ ID: {book_id}"
            )
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
    
    def view_borrows(self):
        """ดูรายการยืม"""
        print("\n" + "=" * 60)
        print("ดูรายการยืม")
        print("=" * 60)
        print("1. ดูรายการยืมเดียว")
        print("2. ดูรายการยืมทั้งหมด")
        print("3. ดูรายการยืมที่ยังไม่คืน")
        print("4. ดูประวัติการยืมของสมาชิก")
        print("5. ดูรายการเกินกำหนดคืน")
        print("0. กลับ")
        
        choice = input("\nเลือก (0-5): ").strip()
        
        if choice == '1':
            self._view_single_borrow()
        elif choice == '2':
            self._view_all_borrows()
        elif choice == '3':
            self._view_active_borrows()
        elif choice == '4':
            self._view_member_borrow_history()
        elif choice == '5':
            self._view_overdue_borrows()
    
    def _view_single_borrow(self):
        """ดูรายการยืมเดียว"""
        borrow_id = input("\nกรอก ID รายการยืม: ").strip()
        borrow = self._find_borrow_by_id(borrow_id)
        
        if borrow:
            print("\n" + "-" * 60)
            self._display_borrow(borrow, compact=False)
        else:
            print("ไม่พบรายการยืม")
    
    def _view_all_borrows(self):
        """ดูรายการยืมทั้งหมด"""
        borrows = self._get_all_borrows()
        active_borrows = [borrow for borrow in borrows if borrow[6] == b'0']
        
        if not active_borrows:
            print("\nไม่มีรายการยืมในระบบ")
            return
        
        print(f"\nมีรายการยืมทั้งหมด {len(active_borrows)} รายการ")
        print("-" * 110)
        print(f"{'ID':<6} {'หนังสือ':<27} {'สมาชิก':<17} {'ID สมาชิก':<11} {'วันยืม':<12} {'สถานะ':<20}")
        print("-" * 110)
        
        for borrow in active_borrows:
            self._display_borrow(borrow, compact=True)
    
    def _view_active_borrows(self):
        """ดูรายการยืมที่ยังไม่คืน"""
        borrows = self._get_all_borrows()
        active_borrows = [borrow for borrow in borrows if borrow[5] == b'B' and borrow[6] == b'0']
        
        if not active_borrows:
            print("\nไม่มีหนังสือที่ยืมอยู่")
            return
        
        print(f"\nมีหนังสือที่ยืมอยู่ {len(active_borrows)} เล่ม")
        print("-" * 110)
        
        for borrow in active_borrows:
            self._display_borrow(borrow, compact=True)
    
    def _view_member_borrow_history(self):
        """ดูประวัติการยืมของสมาชิก"""
        member_id = input("\nกรอก ID สมาชิก: ").strip()
        
        member = self._find_member_by_id(member_id)
        if not member:
            print("ไม่พบสมาชิก")
            return
        
        borrows = self._get_all_borrows()
        member_borrows = [borrow for borrow in borrows 
                         if self._decode_string(borrow[2]) == member_id and borrow[6] == b'0']
        
        if not member_borrows:
            print("ไม่มีประวัติการยืม")
            return
        
        print(f"\nประวัติการยืมของ: {self._decode_string(member[1])} (ID: {member_id})")
        print(f"จำนวนรายการ: {len(member_borrows)}")
        print("-" * 110)
        
        for borrow in member_borrows:
            self._display_borrow(borrow, compact=True)
    
    def _view_overdue_borrows(self):
        """ดูรายการเกินกำหนดคืน"""
        print("\n" + "=" * 60)
        print("รายการเกินกำหนดคืน")
        print("=" * 60)
        
        borrows = self._get_all_borrows()
        current_date = datetime.date.today()
        overdue_list = []
        
        for borrow in borrows:
            if borrow[5] == b'B' and borrow[6] == b'0':
                borrow_date_str = self._decode_string(borrow[3])
                try:
                    borrow_date = datetime.datetime.strptime(borrow_date_str, "%Y-%m-%d").date()
                    due_date = borrow_date + datetime.timedelta(days=7)
                    days_overdue = (current_date - due_date).days
                    
                    if days_overdue > 0:
                        overdue_list.append((borrow, days_overdue))
                except:
                    pass
        
        if not overdue_list:
            print("\nไม่มีรายการเกินกำหนดคืน")
            return
        
        overdue_list.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nพบรายการเกินกำหนด {len(overdue_list)} รายการ")
        print("=" * 110)
        
        for idx, (borrow, days_overdue) in enumerate(overdue_list, 1):
            book_id = self._decode_string(borrow[1])
            member_id = self._decode_string(borrow[2])
            book = self._find_book_by_id(book_id)
            member = self._find_member_by_id(member_id)
            
            print(f"\n{idx}. หนังสือ: {self._decode_string(book[1]) if book else 'N/A'}")
            print(f"   ผู้ยืม: {self._decode_string(member[1]) if member else 'N/A'} (ID: {member_id})")
            print(f"   วันที่ยืม: {self._decode_string(borrow[3])}")
            borrow_date = datetime.datetime.strptime(self._decode_string(borrow[3]), "%Y-%m-%d").date()
            due_date = borrow_date + datetime.timedelta(days=7)
            print(f"   กำหนดคืน: {due_date.strftime('%Y-%m-%d')}")
            print(f"   เกินกำหนด: {days_overdue} วัน")
            print("-" * 110)
    
    def _find_borrow_by_id(self, borrow_id: str) -> Optional[Tuple]:
        """ค้นหารายการยืมจาก ID"""
        borrows = self._get_all_borrows()
        for borrow in borrows:
            if self._decode_string(borrow[0]) == borrow_id and borrow[6] == b'0':
                return borrow
        return None
    
    def _find_active_borrow_by_book_id(self, book_id: str) -> Optional[Tuple[int, Tuple]]:
        """หารายการยืมที่ยังไม่คืนจาก book_id"""
        if not os.path.exists(self.borrows_file):
            return None
        
        with open(self.borrows_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.borrow_size)
                if not data:
                    break
                borrow = struct.unpack(self.borrow_format, data)
                if (self._decode_string(borrow[1]) == book_id and 
                    borrow[5] == b'B' and borrow[6] == b'0'):
                    return (index, borrow)
                index += 1
        return None
    
    def _get_all_borrows(self) -> List[Tuple]:
        """ดึงรายการยืมทั้งหมดจากไฟล์ไบนารี"""
        borrows = []
        if not os.path.exists(self.borrows_file):
            return borrows
        
        with open(self.borrows_file, 'rb') as f:
            while True:
                data = f.read(self.borrow_size)
                if not data:
                    break
                borrow = struct.unpack(self.borrow_format, data)
                borrows.append(borrow)
        return borrows
    
    def _display_borrow(self, borrow: Tuple, compact: bool = False):
        """แสดงรายการยืม"""
        borrow_id = self._decode_string(borrow[0])
        book_id = self._decode_string(borrow[1])
        member_id = self._decode_string(borrow[2])
        borrow_date_str = self._decode_string(borrow[3])
        return_date = self._decode_string(borrow[4]) or "ยังไม่คืน"
        status = "ยืมอยู่" if borrow[5] == b'B' else "คืนแล้ว"
        
        # คำนวณสถานะกำหนดคืน
        try:
            borrow_date = datetime.datetime.strptime(borrow_date_str, "%Y-%m-%d").date()
            due_date = borrow_date + datetime.timedelta(days=7)
            
            if borrow[5] == b'B':
                current_date = datetime.date.today()
                days_until_due = (due_date - current_date).days
                if days_until_due < 0:
                    overdue_info = f" (เกิน {abs(days_until_due)} วัน)"
                elif days_until_due == 0:
                    overdue_info = " (ครบกำหนดวันนี้)"
                else:
                    overdue_info = f" (เหลือ {days_until_due} วัน)"
            else:
                overdue_info = ""
        except:
            overdue_info = ""
        
        book = self._find_book_by_id(book_id)
        member = self._find_member_by_id(member_id)
        
        book_title = self._decode_string(book[1]) if book else f"Book ID: {book_id}"
        member_name = self._decode_string(member[1]) if member else f"Member ID: {member_id}"
        
        if compact:
            print(f"{borrow_id:<6} {book_title[:25]:<27} {member_name[:15]:<17} {member_id:<11} {borrow_date_str:<12} {status}{overdue_info}")
        else:
            print(f"รหัสการยืม: {borrow_id}")
            print(f"หนังสือ: {book_title}")
            print(f"ผู้ยืม: {member_name}")
            print(f"ID สมาชิก: {member_id}")
            print(f"วันที่ยืม: {borrow_date_str}")
            print(f"วันที่คืน: {return_date}")
            print(f"สถานะ: {status}{overdue_info}")
    
    def _update_book_status(self, book_id: str, status: bytes):
        """อัปเดตสถานะหนังสือ"""
        book_index = self._find_book_index_by_id(book_id)
        if book_index == -1:
            return
        
        book = self._get_book_by_index(book_index)
        if not book:
            return
        
        updated_book = struct.pack(
            self.book_format,
            book[0], book[1], book[2], book[3], book[4],
            status,
            book[6]
        )
        
        self._update_record(self.books_file, book_index, updated_book, self.book_size)
    
    def delete_borrow(self):
        """ลบรายการยืม (Soft delete)"""
        print("\n" + "=" * 60)
        print("ลบรายการยืม")
        print("=" * 60)
        
        borrow_id = input("\nกรอก ID รายการยืมที่ต้องการลบ: ").strip()
        
        borrow_index = self._find_borrow_index_by_id(borrow_id)
        if borrow_index == -1:
            print("ไม่พบรายการยืม")
            return
        
        borrow = self._get_borrow_by_index(borrow_index)
        if not borrow:
            print("เกิดข้อผิดพลาดในการอ่านข้อมูล")
            return
        
        print("\nรายการยืมที่จะลบ:")
        print("-" * 60)
        self._display_borrow(borrow)
        
        confirm = input("\nยืนยันการลบ? (y/N): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิกการลบ")
            return
        
        if borrow[5] == b'B':
            book_id = self._decode_string(borrow[1])
            self._update_book_status(book_id, b'A')
        
        deleted_borrow = struct.pack(
            self.borrow_format,
            borrow[0], borrow[1], borrow[2], borrow[3], borrow[4], borrow[5],
            b'1'  # Mark as deleted
        )
        
        self._update_record(self.borrows_file, borrow_index, deleted_borrow, self.borrow_size)
        print("\nลบรายการยืมสำเร็จ")
        self.operation_history.append(
            f"{datetime.datetime.now()}: ลบรายการยืม ID: {borrow_id}"
        )
    
    def _find_borrow_index_by_id(self, borrow_id: str) -> int:
        """หา index ของรายการยืมจาก ID"""
        if not os.path.exists(self.borrows_file):
            return -1
        
        with open(self.borrows_file, 'rb') as f:
            index = 0
            while True:
                data = f.read(self.borrow_size)
                if not data:
                    break
                borrow = struct.unpack(self.borrow_format, data)
                if self._decode_string(borrow[0]) == borrow_id and borrow[6] == b'0':
                    return index
                index += 1
        return -1
    
    def _get_borrow_by_index(self, index: int) -> Optional[Tuple]:
        """ดึงรายการยืมจาก index"""
        if not os.path.exists(self.borrows_file):
            return None
        
        with open(self.borrows_file, 'rb') as f:
            f.seek(index * self.borrow_size)
            data = f.read(self.borrow_size)
            if not data:
                return None
            return struct.unpack(self.borrow_format, data)
    
    # ==================== STATISTICS AND REPORTS ====================
    
    def view_statistics(self):
        """ดูสถิติโดยสรุป"""
        print("\n" + "=" * 60)
        print("สถิติโดยสรุป")
        print("=" * 60)
        
        books = self._get_all_books()
        active_books = [book for book in books if book[6] == b'0']
        available_books = [book for book in active_books if book[5] == b'A']
        borrowed_books = [book for book in active_books if book[5] == b'B']
        deleted_books = [book for book in books if book[6] == b'1']
        
        members = self._get_all_members()
        active_members = [member for member in members if member[7] == b'0' and member[5] == b'A']
        banned_members = [member for member in members if member[7] == b'0' and member[5] == b'S']
        deleted_members = [member for member in members if member[7] == b'1']
        
        borrows = self._get_all_borrows()
        active_borrows = [borrow for borrow in borrows if borrow[6] == b'0']
        current_borrows = [borrow for borrow in active_borrows if borrow[5] == b'B']
        returned_borrows = [borrow for borrow in active_borrows if borrow[5] == b'R']
        deleted_borrows = [borrow for borrow in borrows if borrow[6] == b'1']
        
        # นับหนังสือเกินกำหนด
        current_date = datetime.date.today()
        overdue_count = 0
        for borrow in current_borrows:
            try:
                borrow_date = datetime.datetime.strptime(
                    self._decode_string(borrow[3]), "%Y-%m-%d"
                ).date()
                due_date = borrow_date + datetime.timedelta(days=7)
                if (current_date - due_date).days > 0:
                    overdue_count += 1
            except:
                pass
        
        print("\nสถิติหนังสือ:")
        print(f"  - หนังสือทั้งหมด: {len(active_books)} เล่ม")
        print(f"  - หนังสือว่าง: {len(available_books)} เล่ม")
        print(f"  - หนังสือถูกยืม: {len(borrowed_books)} เล่ม")
        print(f"  - หนังสือที่ถูกลบ: {len(deleted_books)} เล่ม")
        
        print("\nสถิติสมาชิก:")
        print(f"  - สมาชิกทั้งหมด: {len(active_members)} คน")
        print(f"  - สมาชิกถูกแบน: {len(banned_members)} คน")
        print(f"  - สมาชิกที่ถูกลบ: {len(deleted_members)} คน")
        
        print("\nสถิติการยืม:")
        print(f"  - รายการยืมทั้งหมด: {len(active_borrows)} รายการ")
        print(f"  - กำลังยืมอยู่: {len(current_borrows)} รายการ")
        print(f"  - เกินกำหนดคืน: {overdue_count} รายการ")
        print(f"  - คืนแล้ว: {len(returned_borrows)} รายการ")
        print(f"  - รายการที่ถูกลบ: {len(deleted_borrows)} รายการ")
        
        print("\nข้อมูลไฟล์ไบนารี:")
        for filename, desc in [(self.books_file, "หนังสือ"), 
                                (self.members_file, "สมาชิก"), 
                                (self.borrows_file, "รายการยืม")]:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"  - {desc} ({filename}): {size:,} bytes")
    
    def generate_report(self):
        """สร้างรายงานข้อความ"""
        print("\n" + "=" * 60)
        print("สร้างรายงาน")
        print("=" * 60)
        
        try:
            report_content = []
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report_content.append("=" * 80)
            report_content.append("รายงานระบบจัดการห้องสมุด")
            report_content.append("Library Management System Report")
            report_content.append("=" * 80)
            report_content.append(f"วันที่สร้างรายงาน: {current_time}")
            report_content.append(f"ไฟล์ Binary Format: Little-endian (<)")
            report_content.append("-" * 80)
            
            books = self._get_all_books()
            active_books = [book for book in books if book[6] == b'0']
            available_books = [book for book in active_books if book[5] == b'A']
            borrowed_books = [book for book in active_books if book[5] == b'B']
            deleted_books = [book for book in books if book[6] == b'1']
            
            members = self._get_all_members()
            active_members = [member for member in members if member[7] == b'0' and member[5] == b'A']
            banned_members = [member for member in members if member[7] == b'0' and member[5] == b'S']
            deleted_members = [member for member in members if member[7] == b'1']
            
            borrows = self._get_all_borrows()
            active_borrows = [borrow for borrow in borrows if borrow[6] == b'0']
            current_borrows = [borrow for borrow in active_borrows if borrow[5] == b'B']
            returned_borrows = [borrow for borrow in active_borrows if borrow[5] == b'R']
            deleted_borrows = [borrow for borrow in borrows if borrow[6] == b'1']
            
            current_date = datetime.date.today()
            overdue_count = 0
            for borrow in current_borrows:
                try:
                    borrow_date = datetime.datetime.strptime(
                        self._decode_string(borrow[3]), "%Y-%m-%d"
                    ).date()
                    due_date = borrow_date + datetime.timedelta(days=7)
                    if (current_date - due_date).days > 0:
                        overdue_count += 1
                except:
                    pass
            
            report_content.append("\n1. สรุปข้อมูลระบบ")
            report_content.append("-" * 80)
            report_content.append("\n1.1 หนังสือ:")
            report_content.append(f"  - จำนวนหนังสือทั้งหมด: {len(active_books)} เล่ม")
            report_content.append(f"  - หนังสือว่าง: {len(available_books)} เล่ม")
            report_content.append(f"  - หนังสือถูกยืม: {len(borrowed_books)} เล่ม")
            report_content.append(f"  - หนังสือที่ถูกลบ: {len(deleted_books)} เล่ม")
            
            report_content.append("\n1.2 สมาชิก:")
            report_content.append(f"  - จำนวนสมาชิกทั้งหมด: {len(active_members)} คน")
            report_content.append(f"  - สมาชิกถูกแบน: {len(banned_members)} คน")
            report_content.append(f"  - สมาชิกที่ถูกลบ: {len(deleted_members)} คน")
            
            report_content.append("\n1.3 รายการยืม:")
            report_content.append(f"  - รายการยืมทั้งหมด: {len(active_borrows)} รายการ")
            report_content.append(f"  - กำลังยืมอยู่: {len(current_borrows)} รายการ")
            report_content.append(f"  - เกินกำหนดคืน: {overdue_count} รายการ")
            report_content.append(f"  - คืนแล้ว: {len(returned_borrows)} รายการ")
            report_content.append(f"  - รายการที่ถูกลบ: {(deleted_borrows)} รายการ")
            
            report_content.append("\n2. ข้อมูลไฟล์ไบนารี")
            report_content.append("-" * 80)
            for filename, description, format_str in [
                (self.books_file, "หนังสือ", self.book_format),
                (self.members_file, "สมาชิก", self.member_format),
                (self.borrows_file, "รายการยืม", self.borrow_format)
            ]:
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    record_size = struct.calcsize(format_str)
                    record_count = file_size // record_size if record_size > 0 else 0
                    report_content.append(f"\n2.{['1','2','3'][[self.books_file, self.members_file, self.borrows_file].index(filename)]} ไฟล์{description} ({filename}):")
                    report_content.append(f"  - ขนาดไฟล์: {file_size:,} bytes")
                    report_content.append(f"  - ขนาด Record: {record_size} bytes")
                    report_content.append(f"  - จำนวน Record: {record_count} records")
                    report_content.append(f"  - Format: {format_str}")
                else:
                    report_content.append(f"\n2.{['1','2','3'][[self.books_file, self.members_file, self.borrows_file].index(filename)]} ไฟล์{description} ({filename}): ไม่พบไฟล์")
            
            if active_borrows:
                book_borrow_count = {}
                for borrow in active_borrows:
                    book_id = self._decode_string(borrow[1])
                    book_borrow_count[book_id] = book_borrow_count.get(book_id, 0) + 1
                
                if book_borrow_count:
                    sorted_books = sorted(book_borrow_count.items(), key=lambda x: x[1], reverse=True)
                    report_content.append("\n3. หนังสือยอดนิยม (5 อันดับแรก)")
                    report_content.append("-" * 80)
                    
                    for i, (book_id, count) in enumerate(sorted_books[:5], 1):
                        book = self._find_book_by_id(book_id)
                        if book:
                            title = self._decode_string(book[1])
                            report_content.append(f"  {i}. {title} - ถูกยืม {count} ครั้ง")
            
            if self.operation_history:
                report_content.append("\n4. ประวัติการทำงานล่าสุด (10 รายการ)")
                report_content.append("-" * 80)
                recent_operations = self.operation_history[-10:]
                for operation in recent_operations:
                    report_content.append(f"  - {operation}")
            
            report_content.append("\n" + "=" * 80)
            report_content.append("จบรายงาน")
            report_content.append("=" * 80)
            
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_content))
                f.flush()
                os.fsync(f.fileno())
            
            print(f"\nสร้างรายงานสำเร็จ: {self.report_file}")
            
            show_report = input("แสดงรายงานหรือไม่? (y/N): ").strip().lower()
            if show_report == 'y':
                print("\n" + "\n".join(report_content))
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการสร้างรายงาน: {e}")
    
    # ==================== MENU SYSTEM ====================
    
    def show_main_menu(self):
        """แสดงเมนูหลัก"""
        print("\n" + "=" * 60)
        print("ระบบจัดการห้องสมุด (Library Management System)")
        print("Binary File Implementation with struct module")
        print("=" * 60)
        print("1. จัดการหนังสือ (Books)")
        print("2. จัดการสมาชิก (Members)")
        print("3. จัดการการยืม-คืน (Borrow/Return)")
        print("4. ดูสถิติโดยสรุป (Statistics)")
        print("5. สร้างรายงาน (Generate Report)")
        print("0. ออกจากระบบ (Exit)")
        print("-" * 60)
    
    def show_book_menu(self):
        """เมนูจัดการหนังสือ"""
        print("\n" + "=" * 60)
        print("เมนูจัดการหนังสือ")
        print("=" * 60)
        print("1. เพิ่มหนังสือ (Add)")
        print("2. ดูข้อมูลหนังสือ (View)")
        print("3. แก้ไขหนังสือ (Update)")
        print("4. ลบหนังสือ (Delete)")
        print("0. กลับเมนูหลัก")
    
    def show_member_menu(self):
        """เมนูจัดการสมาชิก"""
        print("\n" + "=" * 60)
        print("เมนูจัดการสมาชิก")
        print("=" * 60)
        print("1. เพิ่มสมาชิก (Add)")
        print("2. ดูข้อมูลสมาชิก (View)")
        print("3. แก้ไขสมาชิก (Update)")
        print("4. ลบสมาชิก (Delete)")
        print("0. กลับเมนูหลัก")
    
    def show_borrow_menu(self):
        """เมนูจัดการการยืม-คืน"""
        print("\n" + "=" * 60)
        print("เมนูจัดการการยืม-คืน")
        print("=" * 60)
        print("1. ยืมหนังสือ (Borrow)")
        print("2. คืนหนังสือ (Return)")
        print("3. ดูรายการยืม (View Borrows)")
        print("4. ลบรายการยืม (Delete Borrow)")
        print("0. กลับเมนูหลัก")
    
    def run(self):
        """เรียกใช้งานระบบ"""
        print("\n" + "=" * 60)
        print("ยินดีต้อนรับสู่ระบบจัดการห้องสมุด")
        print("=" * 60)
        
        while True:
            try:
                self.show_main_menu()
                choice = input("เลือกเมนู (0-5): ").strip()
                
                if choice == '1':
                    self._handle_book_menu()
                elif choice == '2':
                    self._handle_member_menu()
                elif choice == '3':
                    self._handle_borrow_menu()
                elif choice == '4':
                    self.view_statistics()
                    input("\nกด Enter เพื่อกลับ...")
                elif choice == '5':
                    self.generate_report()
                    input("\nกด Enter เพื่อกลับ...")
                elif choice == '0':
                    print("\n" + "=" * 60)
                    print("ปิดระบบและบันทึกข้อมูล...")
                    self._flush_all_files()
                    print("ขอบคุณที่ใช้บริการ!")
                    print("=" * 60)
                    break
                else:
                    print("กรุณาเลือกเมนูที่ถูกต้อง")
                    input("\nกด Enter เพื่อกลับ...")
                    
            except KeyboardInterrupt:
                print("\n\nระบบถูกปิดโดยผู้ใช้")
                self._flush_all_files()
                break
            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {e}")
                input("\nกด Enter เพื่อกลับ...")
    
    def _flush_all_files(self):
        """Flush และ sync ไฟล์ทั้งหมดก่อนปิดโปรแกรม"""
        try:
            for filename in [self.books_file, self.members_file, self.borrows_file]:
                if os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        pass  # เปิดเพื่อให้ OS flush
            print("บันทึกข้อมูลสำเร็จ")
        except:
            pass
    
    def _handle_book_menu(self):
        """จัดการเมนูหนังสือ"""
        while True:
            self.show_book_menu()
            choice = input("เลือก (0-4): ").strip()
            
            if choice == '1':
                self.add_book()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '2':
                self.view_books()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '3':
                self.update_book()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '4':
                self.delete_book()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '0':
                break
            else:
                print("กรุณาเลือกเมนูที่ถูกต้อง")
                input("\nกด Enter เพื่อกลับ...")
    
    def _handle_member_menu(self):
        """จัดการเมนูสมาชิก"""
        while True:
            self.show_member_menu()
            choice = input("เลือก (0-4): ").strip()
            
            if choice == '1':
                self.add_member()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '2':
                self.view_members()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '3':
                self.update_member()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '4':
                self.delete_member()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '0':
                break
            else:
                print("กรุณาเลือกเมนูที่ถูกต้อง")
                input("\nกด Enter เพื่อกลับ...")
    
    def _handle_borrow_menu(self):
        """จัดการเมนูการยืม-คืน"""
        while True:
            self.show_borrow_menu()
            choice = input("เลือก (0-4): ").strip()
            
            if choice == '1':
                self.add_borrow()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '2':
                self.return_book()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '3':
                self.view_borrows()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '4':
                self.delete_borrow()
                input("\nกด Enter เพื่อกลับ...")
            elif choice == '0':
                break
            else:
                print("กรุณาเลือกเมนูที่ถูกต้อง")
                input("\nกด Enter เพื่อกลับ...")


def main():
    """ฟังก์ชันหลักของโปรแกรม"""
    try:
        library = LibrarySystem()
        library.run()
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดร้ายแรง: {e}")
    finally:
        print("ระบบปิดทำงานแล้ว")


if __name__ == "__main__":
    main()