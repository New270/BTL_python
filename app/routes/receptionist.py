from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import (Patient, Appointment, Doctor, Invoice, InvoiceItem, 
                        Notification, User, generate_patient_code)

receptionist_bp = Blueprint('receptionist', __name__)


def require_receptionist(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('receptionist', 'admin'):
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ──────────── DASHBOARD ────────────
@receptionist_bp.route('/dashboard')
@login_required
@require_receptionist
def dashboard():
    today = date.today()
    today_appts = (Appointment.query
                   .filter(db.func.date(Appointment.scheduled_at) == today)
                   .order_by(Appointment.queue_number)
                   .all())
    waiting     = [a for a in today_appts if a.status in ('confirmed', 'pending')]
    in_progress = [a for a in today_appts if a.status == 'in_progress']
    completed   = [a for a in today_appts if a.status == 'completed']
    total_patients = Patient.query.count()
    unpaid_invoices = Invoice.query.filter_by(status='unpaid').count()
    return render_template('receptionist/dashboard.html',
                           today_appts=today_appts,
                           waiting=waiting,
                           in_progress=in_progress,
                           completed=completed,
                           total_patients=total_patients,
                           unpaid_invoices=unpaid_invoices,
                           today=today)


# ──────────── PATIENT LIST ────────────
@receptionist_bp.route('/patients')
@login_required
@require_receptionist
def patients():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Patient.query
    if q:
        query = query.filter(
            db.or_(
                Patient.patient_code.ilike(f'%{q}%'),
                Patient.full_name.ilike(f'%{q}%'),
                Patient.phone.ilike(f'%{q}%'),
                Patient.national_id.ilike(f'%{q}%'),
                Patient.insurance_number.ilike(f'%{q}%'),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('receptionist/patients.html', patients=patients, q=q)


# ──────────── NEW PATIENT ────────────
@receptionist_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
@require_receptionist
def new_patient():
    if request.method == 'POST':
        f = request.form
        patient = Patient(
            patient_code=generate_patient_code(),
            full_name        = f.get('full_name', '').strip(),
            dob              = datetime.strptime(f['dob'], '%Y-%m-%d').date() if f.get('dob') else None,
            gender           = f.get('gender'),
            blood_type       = f.get('blood_type', 'unknown'),
            national_id      = f.get('national_id', '').strip(),
            insurance_number = f.get('insurance_number', '').strip(),
            phone            = f.get('phone', '').strip(),
            email            = f.get('email', '').strip(),
            address          = f.get('address', '').strip(),
            emergency_contact_name  = f.get('emergency_contact_name', '').strip(),
            emergency_contact_phone = f.get('emergency_contact_phone', '').strip(),
            emergency_contact_rel   = f.get('emergency_contact_rel', '').strip(),
            allergy_notes    = f.get('allergy_notes', '').strip(),
            chronic_diseases = f.get('chronic_diseases', '').strip(),
            created_by       = current_user.id,
        )
        
        # --- ĐOẠN CODE TẠO TÀI KHOẢN (ĐÃ ĐƯỢC CHUYỂN VỀ ĐÚNG CHỖ) ---
        username = f.get('username')
        password = f.get('password')
        
        if username and password:
            if not User.query.filter_by(username=username).first():
                new_user = User(username=username, role='patient', is_active=False) # Chờ admin duyệt
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.flush()
                patient.user_id = new_user.id # Gắn tài khoản vào hồ sơ BN
        # ------------------------------------------------------------
                
        db.session.add(patient)
        db.session.commit()
        flash(f'✅ Đã tạo bệnh nhân mới. Mã BN: <strong>{patient.patient_code}</strong>. Nếu có tạo tài khoản, hãy chờ Admin duyệt!', 'success')
        return redirect(url_for('receptionist.patient_detail', patient_id=patient.id))
    return render_template('receptionist/new_patient.html')

# ──────────── PATIENT DETAIL ────────────
@receptionist_bp.route('/patients/<int:patient_id>')
@login_required
@require_receptionist
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = (Appointment.query
                    .filter_by(patient_id=patient_id)
                    .order_by(Appointment.scheduled_at.desc())
                    .all())
    return render_template('receptionist/patient_detail.html',
                           patient=patient, appointments=appointments)


# ──────────── EDIT PATIENT ────────────
@receptionist_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@require_receptionist
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        f = request.form
        # Mã bệnh nhân KHÔNG BAO GIỜ thay đổi — chỉ cập nhật thông tin
        patient.full_name        = f.get('full_name', patient.full_name).strip()
        patient.dob              = datetime.strptime(f['dob'], '%Y-%m-%d').date() if f.get('dob') else patient.dob
        patient.gender           = f.get('gender', patient.gender)
        patient.blood_type       = f.get('blood_type', patient.blood_type)
        patient.national_id      = f.get('national_id', '').strip()
        patient.insurance_number = f.get('insurance_number', '').strip()
        patient.phone            = f.get('phone', '').strip()
        patient.email            = f.get('email', '').strip()
        patient.address          = f.get('address', '').strip()
        patient.emergency_contact_name  = f.get('emergency_contact_name', '').strip()
        patient.emergency_contact_phone = f.get('emergency_contact_phone', '').strip()
        patient.emergency_contact_rel   = f.get('emergency_contact_rel', '').strip()
        patient.allergy_notes    = f.get('allergy_notes', '').strip()
        patient.chronic_diseases = f.get('chronic_diseases', '').strip()
        db.session.commit()
        flash('✅ Đã cập nhật thông tin bệnh nhân.', 'success')
        return redirect(url_for('receptionist.patient_detail', patient_id=patient.id))
    return render_template('receptionist/edit_patient.html', patient=patient)


# ──────────── APPOINTMENTS ────────────
@receptionist_bp.route('/appointments')
@login_required
@require_receptionist
def appointments():
    date_str = request.args.get('date', date.today().isoformat())
    try:
        filter_date = date.fromisoformat(date_str)
    except ValueError:
        filter_date = date.today()

    appts = (Appointment.query
             .filter(db.func.date(Appointment.scheduled_at) == filter_date)
             .order_by(Appointment.queue_number, Appointment.scheduled_at)
             .all())
    doctors = Doctor.query.all()
    return render_template('receptionist/appointments.html',
                           appts=appts, doctors=doctors,
                           filter_date=filter_date)


@receptionist_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@require_receptionist
def new_appointment():
    if request.method == 'POST':
        f = request.form
        patient_id  = int(f['patient_id'])
        doctor_id   = int(f['doctor_id'])
        scheduled_at= datetime.strptime(f['scheduled_at'], '%Y-%m-%dT%H:%M')

        # Tự động gán số thứ tự trong ngày
        same_day_count = (Appointment.query
                          .filter(db.func.date(Appointment.scheduled_at) == scheduled_at.date())
                          .filter_by(doctor_id=doctor_id)
                          .count())
        rec_id = current_user.receptionist.id if current_user.receptionist else None

        appt = Appointment(
            patient_id       = patient_id,
            doctor_id        = doctor_id,
            receptionist_id  = rec_id,
            scheduled_at     = scheduled_at,
            appt_type        = f.get('appt_type', 'first_visit'),
            chief_complaint  = f.get('chief_complaint', '').strip(),
            queue_number     = same_day_count + 1,
            status           = 'confirmed',
            notes            = f.get('notes', '').strip(),
        )
        db.session.add(appt)
        db.session.commit()
        flash(f'✅ Đã đặt lịch hẹn. Số thứ tự: {appt.queue_number}', 'success')
        return redirect(url_for('receptionist.appointments'))

    patients = Patient.query.order_by(Patient.full_name).all()
    doctors  = Doctor.query.all()
    return render_template('receptionist/new_appointment.html',
                           patients=patients, doctors=doctors)



@receptionist_bp.route('/appointments/<int:appt_id>/checkin', methods=['POST'])
@login_required
@require_receptionist
def checkin(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'confirmed'
    appt.checked_in_at = datetime.utcnow()
    db.session.commit()
    flash('✅ Đã check-in bệnh nhân.', 'success')
    return redirect(url_for('receptionist.appointments'))


@receptionist_bp.route('/appointments/<int:appt_id>/cancel', methods=['POST'])
@login_required
@require_receptionist
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'cancelled'
    appt.cancel_reason = request.form.get('cancel_reason', '')
    db.session.commit()
    flash('Đã hủy lịch hẹn.', 'warning')
    return redirect(url_for('receptionist.appointments'))


# ──────────── INVOICES ────────────
@receptionist_bp.route('/invoices')
@login_required
@require_receptionist
def invoices():
    status = request.args.get('status', 'all')
    query = Invoice.query
    if status != 'all':
        query = query.filter_by(status=status)
    invoices = query.order_by(Invoice.created_at.desc()).limit(50).all()
    return render_template('receptionist/invoices.html', invoices=invoices, status=status)


@receptionist_bp.route('/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
@require_receptionist
def pay_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    inv.status         = 'paid'
    inv.payment_method = request.form.get('payment_method', 'cash')
    inv.paid_at        = datetime.utcnow()
    db.session.commit()
    flash('✅ Đã xác nhận thanh toán.', 'success')
    return redirect(url_for('receptionist.invoices'))


# ──────────── API: search patient (AJAX) ────────────
@receptionist_bp.route('/api/patients/search')
@login_required
def api_search_patients():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Patient.query.filter(
        db.or_(
            Patient.patient_code.ilike(f'%{q}%'),
            Patient.full_name.ilike(f'%{q}%'),
            Patient.phone.ilike(f'%{q}%'),
        )
    ).limit(10).all()
    return jsonify([{
        'id': p.id,
        'patient_code': p.patient_code,
        'full_name': p.full_name,
        'phone': p.phone or '',
        'dob': p.dob.strftime('%d/%m/%Y') if p.dob else '',
    } for p in results])


@receptionist_bp.route('/appointments/<int:appt_id>/approve', methods=['GET', 'POST'])
@login_required
@require_receptionist
def approve_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    
    if request.method == 'POST':
        # Lấy giờ và bác sĩ do Lễ tân chọn
        scheduled_time_str = request.form.get('scheduled_time') # Dạng HH:MM
        doctor_id = request.form.get('doctor_id')
        
        if scheduled_time_str and doctor_id:
            # Ghép ngày cũ (do bệnh nhân chọn) với giờ mới (do lễ tân chọn)
            date_part = appt.scheduled_at.date()
            time_part = datetime.strptime(scheduled_time_str, '%H:%M').time()
            new_datetime = datetime.combine(date_part, time_part)
            
            # Cập nhật thông tin và xếp số thứ tự
            appt.scheduled_at = new_datetime
            appt.doctor_id = int(doctor_id)
            appt.receptionist_id = current_user.receptionist.id
            appt.status = 'confirmed'
            
            same_day_count = Appointment.query.filter(
                db.func.date(Appointment.scheduled_at) == date_part,
                Appointment.doctor_id == appt.doctor_id
            ).count()
            appt.queue_number = same_day_count + 1
            
            db.session.commit()
            flash('Đã duyệt và sắp xếp lịch khám thành công!', 'success')
            return redirect(url_for('receptionist.appointments'))
            
    doctors = Doctor.query.all()
    return render_template('receptionist/approve_appointment.html', appt=appt, doctors=doctors)