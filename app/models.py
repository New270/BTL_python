from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# ──────────────────────────────────────────────
#  ENUMS (dùng string thay vì Python Enum cho SQLite dễ dàng hơn)
# ──────────────────────────────────────────────
ROLES = ['admin', 'doctor', 'receptionist', 'assistant', 'patient']
APPT_STATUS = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled']
APPT_TYPE   = ['first_visit', 'revisit', 'emergency']
GENDER      = ['male', 'female', 'other']
BLOOD_TYPE  = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown']
PAY_METHOD  = ['cash', 'transfer', 'insurance']
INV_STATUS  = ['unpaid', 'paid', 'cancelled']
STOCK_TYPE  = ['import', 'export', 'adjust']


# ──────────────────────────────────────────────
#  USER
# ──────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(50), unique=True, nullable=False)
    password_hash= db.Column(db.String(256), nullable=False)
    role         = db.Column(db.String(20), nullable=False)   # ROLES
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    doctor       = db.relationship('Doctor',       back_populates='user', uselist=False)
    receptionist = db.relationship('Receptionist', back_populates='user', uselist=False)
    assistant    = db.relationship('Assistant',    back_populates='user', uselist=False)
    patient      = db.relationship('Patient', foreign_keys='Patient.user_id', back_populates='user', uselist=False)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_display_name(self):
        if self.doctor:      return self.doctor.full_name
        if self.receptionist:return self.receptionist.full_name
        if self.assistant:   return self.assistant.full_name
        if self.patient:     return self.patient.full_name
        return self.username

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ──────────────────────────────────────────────
#  STAFF PROFILES
# ──────────────────────────────────────────────
class Doctor(db.Model):
    __tablename__ = 'doctors'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    full_name      = db.Column(db.String(100), nullable=False)
    specialty      = db.Column(db.String(100))          # Chuyên khoa
    degree         = db.Column(db.String(50))           # BS, ThS, TS, PGS, GS
    license_number = db.Column(db.String(50), unique=True)
    phone          = db.Column(db.String(20))
    email          = db.Column(db.String(100))
    bio            = db.Column(db.Text)

    user           = db.relationship('User', back_populates='doctor')
    appointments   = db.relationship('Appointment', back_populates='doctor')
    medical_records= db.relationship('MedicalRecord', back_populates='doctor')
    prescriptions  = db.relationship('Prescription', back_populates='doctor')
    assistants     = db.relationship('Assistant', back_populates='doctor')

    def __repr__(self):
        return f'<Doctor {self.full_name}>'


class Receptionist(db.Model):
    __tablename__ = 'receptionists'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone     = db.Column(db.String(20))
    shift     = db.Column(db.String(20))   # morning / afternoon / full

    user      = db.relationship('User', back_populates='receptionist')
    appointments_handled = db.relationship('Appointment', back_populates='receptionist')
    invoices  = db.relationship('Invoice', back_populates='receptionist')


class Assistant(db.Model):
    __tablename__ = 'assistants'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    doctor_id  = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    full_name  = db.Column(db.String(100), nullable=False)
    phone      = db.Column(db.String(20))

    user       = db.relationship('User', back_populates='assistant')
    doctor     = db.relationship('Doctor', back_populates='assistants')
    vital_signs= db.relationship('VitalSign', back_populates='assistant')


# ──────────────────────────────────────────────
#  PATIENT — MÃ BỆNH NHÂN VĨNH VIỄN
# ──────────────────────────────────────────────
class Patient(db.Model):
    """
    Mã bệnh nhân (patient_code) được cấp 1 lần duy nhất, không bao giờ thay đổi.
    Format: BN-YYYYMMDD-XXXXX  (VD: BN-20240315-00001)
    Dù bệnh nhân khám bao nhiêu lần, đổi địa chỉ, số điện thoại... mã này giữ nguyên.
    """
    __tablename__ = 'patients'

    id               = db.Column(db.Integer, primary_key=True)
    patient_code     = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)

    # Thông tin cơ bản
    full_name        = db.Column(db.String(100), nullable=False)
    dob              = db.Column(db.Date)
    gender           = db.Column(db.String(10))        # GENDER
    blood_type       = db.Column(db.String(20), default='unknown')  # BLOOD_TYPE
    national_id      = db.Column(db.String(20))        # CMND/CCCD
    insurance_number = db.Column(db.String(20))        # Số BHYT

    # Liên hệ
    phone            = db.Column(db.String(20))
    email            = db.Column(db.String(100))
    address          = db.Column(db.Text)

    # Khẩn cấp
    emergency_contact_name  = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_rel   = db.Column(db.String(50))  # Quan hệ: cha/mẹ/vợ...

    # Tiền sử
    allergy_notes    = db.Column(db.Text)   # Dị ứng thuốc/thức ăn
    chronic_diseases = db.Column(db.Text)   # Bệnh mãn tính

    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'))

    user             = db.relationship('User', foreign_keys=[user_id], back_populates='patient')
    appointments     = db.relationship('Appointment', back_populates='patient')
    medical_records  = db.relationship('MedicalRecord', back_populates='patient')
    invoices         = db.relationship('Invoice', back_populates='patient')

    @property
    def age(self):
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
        return None

    @property
    def gender_display(self):
        return {'male': 'Nam', 'female': 'Nữ', 'other': 'Khác'}.get(self.gender, '')

    @property
    def total_visits(self):
        return len([a for a in self.appointments if a.status == 'completed'])

    def __repr__(self):
        return f'<Patient {self.patient_code} - {self.full_name}>'


def generate_patient_code():
    from datetime import datetime
    # Đếm số bệnh nhân hiện có để tăng mã lên
    count = Patient.query.count()
    # Sẽ tự động sinh ra mã chuẩn 17 ký tự, ví dụ: BN-20240422-00001
    return f"BN-{datetime.today().strftime('%Y%m%d')}-{count + 1:05d}"

# ──────────────────────────────────────────────
#  APPOINTMENT & QUEUE
# ──────────────────────────────────────────────
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id               = db.Column(db.Integer, primary_key=True)
    patient_id       = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    receptionist_id  = db.Column(db.Integer, db.ForeignKey('receptionists.id'))
    scheduled_at     = db.Column(db.DateTime, nullable=False)
    status           = db.Column(db.String(20), default='pending')   # APPT_STATUS
    appt_type        = db.Column(db.String(20), default='first_visit') # APPT_TYPE
    chief_complaint  = db.Column(db.Text)    # Lý do đến khám
    cancel_reason    = db.Column(db.Text)
    queue_number     = db.Column(db.Integer) # Số thứ tự trong ngày
    checked_in_at    = db.Column(db.DateTime)
    called_at        = db.Column(db.DateTime)
    notes            = db.Column(db.Text)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    patient          = db.relationship('Patient', back_populates='appointments')
    doctor           = db.relationship('Doctor', back_populates='appointments')
    receptionist     = db.relationship('Receptionist', back_populates='appointments_handled')
    medical_record   = db.relationship('MedicalRecord', back_populates='appointment', uselist=False)
    invoice          = db.relationship('Invoice', back_populates='appointment', uselist=False)

    @property
    def status_display(self):
        return {
            'pending':     '⏳ Chờ xác nhận',
            'confirmed':   '✅ Đã xác nhận',
            'in_progress': '🩺 Đang khám',
            'completed':   '✔️ Hoàn thành',
            'cancelled':   '❌ Đã hủy',
        }.get(self.status, self.status)

    @property
    def type_display(self):
        return {
            'first_visit': 'Khám lần đầu',
            'revisit':     'Tái khám',
            'emergency':   'Cấp cứu',
        }.get(self.appt_type, self.appt_type)


# ──────────────────────────────────────────────
#  MEDICAL RECORD & VITAL SIGNS
# ──────────────────────────────────────────────
class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'

    id              = db.Column(db.Integer, primary_key=True)
    patient_id      = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id       = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id  = db.Column(db.Integer, db.ForeignKey('appointments.id'), unique=True)

    symptoms        = db.Column(db.Text)         # Triệu chứng
    diagnosis       = db.Column(db.Text)         # Chẩn đoán
    icd10_code      = db.Column(db.String(10))   # Mã ICD-10
    treatment_plan  = db.Column(db.Text)         # Phác đồ điều trị
    doctor_notes    = db.Column(db.Text)         # Ghi chú bác sĩ
    follow_up_date  = db.Column(db.Date)         # Ngày tái khám
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient         = db.relationship('Patient', back_populates='medical_records')
    doctor          = db.relationship('Doctor', back_populates='medical_records')
    appointment     = db.relationship('Appointment', back_populates='medical_record')
    vital_sign      = db.relationship('VitalSign', back_populates='medical_record', uselist=False)
    prescription    = db.relationship('Prescription', back_populates='medical_record', uselist=False)
    lab_orders      = db.relationship('LabOrder', back_populates='medical_record')


class VitalSign(db.Model):
    """Sinh hiệu — do Trợ lý bác sĩ nhập trước khi bác sĩ khám"""
    __tablename__ = 'vital_signs'

    id              = db.Column(db.Integer, primary_key=True)
    medical_record_id= db.Column(db.Integer, db.ForeignKey('medical_records.id'), unique=True)
    assistant_id    = db.Column(db.Integer, db.ForeignKey('assistants.id'))

    temperature     = db.Column(db.Float)         # Nhiệt độ (°C)
    blood_pressure  = db.Column(db.String(20))    # Huyết áp (VD: 120/80)
    heart_rate      = db.Column(db.Integer)       # Nhịp tim (lần/phút)
    respiratory_rate= db.Column(db.Integer)       # Nhịp thở
    weight          = db.Column(db.Float)         # Cân nặng (kg)
    height          = db.Column(db.Float)         # Chiều cao (cm)
    spo2            = db.Column(db.Float)         # SpO2 (%)
    notes           = db.Column(db.Text)
    recorded_at     = db.Column(db.DateTime, default=datetime.utcnow)

    medical_record  = db.relationship('MedicalRecord', back_populates='vital_sign')
    assistant       = db.relationship('Assistant', back_populates='vital_signs')

    @property
    def bmi(self):
        if self.weight and self.height and self.height > 0:
            h_m = self.height / 100
            return round(self.weight / (h_m * h_m), 1)
        return None


class LabOrder(db.Model):
    """Chỉ định xét nghiệm / cận lâm sàng"""
    __tablename__ = 'lab_orders'

    id               = db.Column(db.Integer, primary_key=True)
    medical_record_id= db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    test_name        = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text)
    result_note      = db.Column(db.Text)
    result_file_url  = db.Column(db.String(300))
    status           = db.Column(db.String(20), default='ordered')  # ordered/resulted
    ordered_at       = db.Column(db.DateTime, default=datetime.utcnow)
    resulted_at      = db.Column(db.DateTime)

    medical_record   = db.relationship('MedicalRecord', back_populates='lab_orders')


# ──────────────────────────────────────────────
#  MEDICINE & PRESCRIPTION
# ──────────────────────────────────────────────
class Medicine(db.Model):
    __tablename__ = 'medicines'

    id                = db.Column(db.Integer, primary_key=True)
    name              = db.Column(db.String(200), nullable=False)
    active_ingredient = db.Column(db.String(200))   # Hoạt chất
    dosage_form       = db.Column(db.String(50))    # Dạng bào chế (viên, gói, chai...)
    unit              = db.Column(db.String(20))    # Đơn vị (viên, ml, gói...)
    price             = db.Column(db.Float, default=0)
    stock_quantity    = db.Column(db.Integer, default=0)
    min_stock_alert   = db.Column(db.Integer, default=10)  # Cảnh báo khi dưới mức này
    expiry_date       = db.Column(db.Date)
    manufacturer      = db.Column(db.String(200))
    description       = db.Column(db.Text)
    is_active         = db.Column(db.Boolean, default=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    prescription_items= db.relationship('PrescriptionItem', back_populates='medicine')
    stock_logs        = db.relationship('StockLog', back_populates='medicine')

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_alert

    @property
    def is_near_expiry(self):
        if self.expiry_date:
            delta = (self.expiry_date - date.today()).days
            return 0 <= delta <= 30
        return False

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False


class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id               = db.Column(db.Integer, primary_key=True)
    medical_record_id= db.Column(db.Integer, db.ForeignKey('medical_records.id'), unique=True)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    notes            = db.Column(db.Text)   # Lời dặn bác sĩ
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    medical_record   = db.relationship('MedicalRecord', back_populates='prescription')
    doctor           = db.relationship('Doctor', back_populates='prescriptions')
    items            = db.relationship('PrescriptionItem', back_populates='prescription',
                                       cascade='all, delete-orphan')

    @property
    def total_cost(self):
        return sum(item.subtotal for item in self.items)


class PrescriptionItem(db.Model):
    __tablename__ = 'prescription_items'

    id              = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_id     = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    quantity        = db.Column(db.Integer, nullable=False)
    dosage          = db.Column(db.String(100))    # Liều dùng (VD: 1 viên)
    frequency       = db.Column(db.String(100))    # Tần suất (VD: 2 lần/ngày)
    duration_days   = db.Column(db.Integer)        # Số ngày uống
    instructions    = db.Column(db.Text)           # Hướng dẫn (uống trước/sau ăn...)

    prescription    = db.relationship('Prescription', back_populates='items')
    medicine        = db.relationship('Medicine', back_populates='prescription_items')

    @property
    def subtotal(self):
        return (self.medicine.price or 0) * (self.quantity or 0)


class StockLog(db.Model):
    """Lịch sử nhập/xuất kho thuốc"""
    __tablename__ = 'stock_logs'

    id              = db.Column(db.Integer, primary_key=True)
    medicine_id     = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    change_type     = db.Column(db.String(20))   # import / export / adjust
    quantity_change = db.Column(db.Integer)      # + nhập, - xuất
    quantity_before = db.Column(db.Integer)
    quantity_after  = db.Column(db.Integer)
    note            = db.Column(db.Text)
    created_by      = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    medicine        = db.relationship('Medicine', back_populates='stock_logs')
    creator         = db.relationship('User', foreign_keys=[created_by])


# ──────────────────────────────────────────────
#  INVOICE
# ──────────────────────────────────────────────
class Invoice(db.Model):
    __tablename__ = 'invoices'

    id               = db.Column(db.Integer, primary_key=True)
    invoice_code     = db.Column(db.String(20), unique=True, nullable=False)
    patient_id       = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    appointment_id   = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    receptionist_id  = db.Column(db.Integer, db.ForeignKey('receptionists.id'))

    exam_fee         = db.Column(db.Float, default=0)       # Phí khám
    medicine_fee     = db.Column(db.Float, default=0)       # Tiền thuốc
    lab_fee          = db.Column(db.Float, default=0)       # Phí xét nghiệm
    discount         = db.Column(db.Float, default=0)       # Giảm giá
    insurance_covered= db.Column(db.Float, default=0)       # BHYT chi trả
    total_amount     = db.Column(db.Float, default=0)       # Tổng thanh toán

    payment_method   = db.Column(db.String(20), default='cash')  # PAY_METHOD
    status           = db.Column(db.String(20), default='unpaid') # INV_STATUS
    notes            = db.Column(db.Text)
    paid_at          = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    patient          = db.relationship('Patient', back_populates='invoices')
    appointment      = db.relationship('Appointment', back_populates='invoice')
    receptionist     = db.relationship('Receptionist', back_populates='invoices')
    items            = db.relationship('InvoiceItem', back_populates='invoice',
                                       cascade='all, delete-orphan')

    @property
    def status_display(self):
        return {
            'unpaid':    '⏳ Chưa thanh toán',
            'paid':      '✅ Đã thanh toán',
            'cancelled': '❌ Đã hủy',
        }.get(self.status, self.status)


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'

    id          = db.Column(db.Integer, primary_key=True)
    invoice_id  = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(200))
    quantity    = db.Column(db.Integer, default=1)
    unit_price  = db.Column(db.Float, default=0)
    amount      = db.Column(db.Float, default=0)

    invoice     = db.relationship('Invoice', back_populates='items')


# ──────────────────────────────────────────────
#  NOTIFICATION
# ──────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(200))
    message    = db.Column(db.Text)
    notif_type = db.Column(db.String(30), default='info')  # info/warning/success/danger
    is_read    = db.Column(db.Boolean, default=False)
    link       = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user       = db.relationship('User', foreign_keys=[user_id])
