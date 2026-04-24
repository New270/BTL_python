from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Appointment, MedicalRecord

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