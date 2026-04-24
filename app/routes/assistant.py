from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import Appointment, MedicalRecord, VitalSign, Medicine

assistant_bp = Blueprint('assistant', __name__)

def require_assistant(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('assistant', 'admin'):
            flash('Không có quyền truy cập.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@assistant_bp.route('/dashboard')
@login_required
@require_assistant
def dashboard():
    assistant = current_user.assistant
    today     = date.today()
    if assistant and assistant.doctor_id:
        appts = (Appointment.query
                 .filter_by(doctor_id=assistant.doctor_id)
                 .filter(db.func.date(Appointment.scheduled_at) == today)
                 .filter(Appointment.status.in_(['confirmed', 'in_progress', 'pending']))
                 .order_by(Appointment.queue_number).all())
    else:
        appts = (Appointment.query
                 .filter(db.func.date(Appointment.scheduled_at) == today)
                 .order_by(Appointment.queue_number).all())
    return render_template('assistant/dashboard.html', appts=appts, today=today)

@assistant_bp.route('/vitals/<int:appt_id>', methods=['GET', 'POST'])
@login_required
@require_assistant
def enter_vitals(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    record = MedicalRecord.query.filter_by(appointment_id=appt_id).first()
    if not record:
        record = MedicalRecord(
            patient_id     = appt.patient_id,
            doctor_id      = appt.doctor_id,
            appointment_id = appt.id,
        )
        db.session.add(record)
        db.session.flush()

    existing_vital = VitalSign.query.filter_by(medical_record_id=record.id).first()

    if request.method == 'POST':
        f = request.form
        asst = current_user.assistant
        if existing_vital:
            vital = existing_vital
        else:
            vital = VitalSign(
                medical_record_id = record.id,
                assistant_id      = asst.id if asst else None,
            )
            db.session.add(vital)

        vital.temperature      = float(f['temperature']) if f.get('temperature') else None
        vital.blood_pressure   = f.get('blood_pressure', '').strip()
        vital.heart_rate       = int(f['heart_rate']) if f.get('heart_rate') else None
        vital.respiratory_rate = int(f['respiratory_rate']) if f.get('respiratory_rate') else None
        vital.weight           = float(f['weight']) if f.get('weight') else None
        vital.height           = float(f['height']) if f.get('height') else None
        vital.spo2             = float(f['spo2']) if f.get('spo2') else None
        vital.notes            = f.get('notes', '').strip()
        vital.recorded_at      = datetime.utcnow()

        db.session.commit()
        flash('✅ Đã lưu sinh hiệu bệnh nhân.', 'success')
        return redirect(url_for('assistant.dashboard'))

    return render_template('assistant/enter_vitals.html',
                           appt=appt, vital=existing_vital)

@assistant_bp.route('/appointments/<int:appt_id>/scribe', methods=['GET', 'POST'])
@login_required
@require_assistant
def scribe_record(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    asst = current_user.assistant
    
    # Bảo mật: Trợ lý chỉ được gõ cho bác sĩ mình đang theo hỗ trợ
    if not asst or appt.doctor_id != asst.doctor_id:
        flash('Bạn không được phân công hỗ trợ bác sĩ này!', 'danger')
        return redirect(url_for('assistant.dashboard'))

    record = MedicalRecord.query.filter_by(appointment_id=appt_id).first()
    if not record:
        record = MedicalRecord(
            patient_id=appt.patient_id,
            doctor_id=appt.doctor_id,
            appointment_id=appt.id
        )
        db.session.add(record)
        db.session.flush()

    if request.method == 'POST':
        f = request.form
        # Trợ lý gõ nội dung (Bác sĩ đọc cho gõ)
        record.symptoms       = f.get('symptoms', '').strip()
        record.diagnosis      = f.get('diagnosis', '').strip()
        record.treatment_plan = f.get('treatment_plan', '').strip()
        
        # Ký tên trợ lý vào phần ghi chú
        old_notes = f.get('doctor_notes', '').strip()
        record.doctor_notes = f"{old_notes}\n[Gõ bởi Trợ lý: {asst.full_name}]"
        
        # Cập nhật trạng thái thành đang khám
        appt.status = 'in_progress'
        db.session.commit()
        
        flash('Đã lưu bệnh án nháp thành công! Bác sĩ có thể xem và in.', 'success')
        return redirect(url_for('assistant.dashboard'))
    
    # Trợ lý "mượn" luôn form giao diện của bác sĩ để gõ cho nhanh
    medicines = Medicine.query.filter_by(is_active=True).order_by(Medicine.name).all()
    history = MedicalRecord.query.filter_by(patient_id=appt.patient_id).order_by(MedicalRecord.created_at.desc()).limit(5).all()
    
    return render_template('doctor/create_record.html', 
                           appt=appt, patient=appt.patient, 
                           medicines=medicines, history=history, record=record)