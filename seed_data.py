from app import create_app, db
from app.models import User, Doctor, Receptionist, Assistant, Patient, Medicine, Appointment, generate_patient_code
from datetime import datetime, timedelta, date

app = create_app()

with app.app_context():
    print("⏳ Đang dọn dẹp và tạo dữ liệu mẫu...")

    # 1. TẠO NHÂN SỰ (BÁC SĨ, LỄ TÂN, TRỢ LÝ)
    def create_staff(username, pwd, role, full_name, model_class, **kwargs):
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, role=role, is_active=True)
            user.set_password(pwd)
            db.session.add(user)
            db.session.flush() # Lưu tạm để lấy user.id
            staff = model_class(user_id=user.id, full_name=full_name, **kwargs)
            db.session.add(staff)
            return staff
        return getattr(user, role)

    # Khởi tạo các tài khoản demo (Trùng với nút Demo ngoài trang Login)
    doctor = create_staff('bsnguyenvan', 'bs123', 'doctor', 'BS. Nguyễn Văn A', Doctor, specialty='Nội khoa', phone='0912345678')
    receptionist = create_staff('letan01', 'lt123', 'receptionist', 'Trần Thị Lễ Tân', Receptionist, phone='0987654321', shift='morning')
    assistant = create_staff('troly01', 'tl123', 'assistant', 'Lê Văn Trợ Lý', Assistant, doctor_id=doctor.id, phone='0909090909')

    # 2. TẠO BỆNH NHÂN
    # Tạo 1 bệnh nhân CÓ TÀI KHOẢN ĐĂNG NHẬP
    bn_user = User.query.filter_by(username='benhnhan01').first()
    if not bn_user:
        bn_user = User(username='benhnhan01', role='patient', is_active=True)
        bn_user.set_password('bn123')
        db.session.add(bn_user)
        db.session.flush()

        bn1 = Patient(user_id=bn_user.id, patient_code=generate_patient_code(), full_name='Hoàng Văn Thành', dob=date(1990, 5, 20), gender='male', blood_type='O+', phone='0922334455', address='Hà Nội')
        db.session.add(bn1)
        db.session.commit() # Cần commit để hàm generate_patient_code() tăng số thứ tự chuẩn

    # Tạo thêm 2 bệnh nhân KHÔNG CÓ tài khoản (Do lễ tân tự tạo)
    if Patient.query.count() < 3:
        bn2 = Patient(patient_code=generate_patient_code(), full_name='Nguyễn Thủy Tiên', dob=date(1995, 8, 15), gender='female', blood_type='A+', phone='0933445566')
        db.session.add(bn2)
        db.session.commit()

        bn3 = Patient(patient_code=generate_patient_code(), full_name='Trần Đại Quang', dob=date(1985, 2, 10), gender='male', phone='0944556677')
        db.session.add(bn3)
        db.session.commit()

    # 3. TẠO KHO THUỐC
    if Medicine.query.count() == 0:
        m1 = Medicine(name='Panadol Extra 500mg', unit='Viên', price=5000, stock_quantity=1000, dosage_form='Viên nén', active_ingredient='Paracetamol, Caffeine')
        m2 = Medicine(name='Augmentin 1g', unit='Viên', price=18000, stock_quantity=500, dosage_form='Viên nén', active_ingredient='Amoxicillin')
        m3 = Medicine(name='Prospan', unit='Chai', price=85000, stock_quantity=50, min_stock_alert=100, dosage_form='Siro', active_ingredient='Cao lá thường xuân')
        db.session.add_all([m1, m2, m3])

    # 4. TẠO LỊCH HẸN CHO HÔM NAY
    if Appointment.query.count() == 0:
        patients_list = Patient.query.limit(3).all()
        today = datetime.now()
        
        # Bệnh nhân 1: Đang chờ khám
        appt1 = Appointment(patient_id=patients_list[0].id, doctor_id=doctor.id, receptionist_id=receptionist.id, scheduled_at=today.replace(hour=8, minute=30), status='confirmed', appt_type='first_visit', chief_complaint='Đau đầu, chóng mặt', queue_number=1)
        
        # Bệnh nhân 2: Đang khám
        appt2 = Appointment(patient_id=patients_list[1].id, doctor_id=doctor.id, receptionist_id=receptionist.id, scheduled_at=today.replace(hour=9, minute=0), status='in_progress', appt_type='first_visit', chief_complaint='Sốt cao, ho nhiều', queue_number=2)
        
        # Bệnh nhân 3: Mới đặt lịch trên web, chờ xác nhận
        appt3 = Appointment(patient_id=patients_list[2].id, doctor_id=doctor.id, scheduled_at=today.replace(hour=14, minute=0), status='pending', appt_type='revisit', chief_complaint='Tái khám lấy thuốc')

        db.session.add_all([appt1, appt2, appt3])

    db.session.commit()
    print("✅ Bơm dữ liệu thành công! Bạn có thể đăng nhập vào Web để test.")