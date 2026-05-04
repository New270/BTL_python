from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Appointment, MedicalRecord
from datetime import datetime
from app import db

patient_bp = Blueprint('patient', __name__)

def require_patient(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'patient':
            flash('Không có quyền truy cập.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@patient_bp.route('/dashboard')
@login_required
@require_patient
def dashboard():
    patient = current_user.patient
    appts   = (Appointment.query
               .filter_by(patient_id=patient.id)
               .order_by(Appointment.scheduled_at.desc())
               .limit(5).all())
    return render_template('patient/dashboard.html', patient=patient, appts=appts)

@patient_bp.route('/appointments')
@login_required
@require_patient
def appointments():
    patient = current_user.patient
    appts   = (Appointment.query
               .filter_by(patient_id=patient.id)
               .order_by(Appointment.scheduled_at.desc())
               .all())
    return render_template('patient/appointments.html', patient=patient, appts=appts)

@patient_bp.route('/records')
@login_required
@require_patient
def records():
    patient = current_user.patient
    records = (MedicalRecord.query
               .filter_by(patient_id=patient.id)
               .order_by(MedicalRecord.created_at.desc())
               .all())
    return render_template('patient/records.html', patient=patient, records=records)

@patient_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@require_patient
def new_appointment():
    patient = current_user.patient
    
    if request.method == 'POST':
        # Bệnh nhân chỉ cần nhập ngày và lý do
        desired_date_str = request.form.get('desired_date')
        reason = request.form.get('chief_complaint', '').strip()
        
        if not desired_date_str:
            flash('Vui lòng chọn ngày muốn khám.', 'danger')
            return redirect(url_for('patient.new_appointment'))
            
        # Lấy ngày được chọn (mặc định set giờ là 00:00:00)
        desired_date = datetime.strptime(desired_date_str, '%Y-%m-%d')
        
        appt = Appointment(
            patient_id=patient.id,
            scheduled_at=desired_date, 
            chief_complaint=reason,
            status='pending', # QUAN TRỌNG: Trạng thái là pending chờ duyệt
            appt_type='first_visit'
        )
        db.session.add(appt)
        db.session.commit()
        
        flash('Đã gửi yêu cầu đặt lịch hẹn! Lễ tân sẽ liên hệ hoặc sắp xếp giờ khám cho bạn.', 'success')
        return redirect(url_for('patient.appointments'))
        
    return render_template('patient/new_appointment.html', patient=patient)