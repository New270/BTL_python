from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import (Appointment, MedicalRecord, VitalSign, Prescription,
                         PrescriptionItem, Medicine, Invoice, InvoiceItem,
                         LabOrder, StockLog, Patient)

doctor_bp = Blueprint('doctor', __name__)

def require_doctor(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('doctor', 'admin'):
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@doctor_bp.route('/dashboard')
@login_required
@require_doctor
def dashboard():
    doctor = current_user.doctor
    today  = date.today()
    today_appts = (Appointment.query
                   .filter_by(doctor_id=doctor.id)
                   .filter(db.func.date(Appointment.scheduled_at) == today)
                   .order_by(Appointment.queue_number)
                   .all())
    waiting     = [a for a in today_appts if a.status in ('confirmed', 'pending')]
    completed   = [a for a in today_appts if a.status == 'completed']
    in_progress = [a for a in today_appts if a.status == 'in_progress']
    return render_template('doctor/dashboard.html',
                           doctor=doctor,
                           today_appts=today_appts,
                           waiting=waiting,
                           completed=completed,
                           in_progress=in_progress,
                           today=today)

@doctor_bp.route('/queue')
@login_required
@require_doctor
def queue():
    doctor = current_user.doctor
    today  = date.today()
    appts  = (Appointment.query
              .filter_by(doctor_id=doctor.id)
              .filter(db.func.date(Appointment.scheduled_at) == today)
              .filter(Appointment.status.in_(['confirmed', 'in_progress', 'pending']))
              .order_by(Appointment.queue_number)
              .all())
    return render_template('doctor/queue.html', appts=appts, today=today)

@doctor_bp.route('/appointments/<int:appt_id>/start', methods=['POST'])
@login_required
@require_doctor
def start_exam(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status    = 'in_progress'
    appt.called_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('doctor.create_record', appt_id=appt_id))

@doctor_bp.route('/appointments/<int:appt_id>/record/new', methods=['GET', 'POST'])
@login_required
@require_doctor
def create_record(appt_id):
    appt    = Appointment.query.get_or_404(appt_id)
    patient = appt.patient
    doctor  = current_user.doctor

    history = (MedicalRecord.query
               .filter_by(patient_id=patient.id)
               .order_by(MedicalRecord.created_at.desc())
               .limit(5).all())


    record = MedicalRecord.query.filter_by(appointment_id=appt.id).first()

    if request.method == 'POST':
        f = request.form
        
     
        if not record:
            record = MedicalRecord(
                patient_id     = patient.id,
                doctor_id      = doctor.id,
                appointment_id = appt.id
            )
            db.session.add(record)

        # Cập nhật thông tin khám
        record.symptoms       = f.get('symptoms', '').strip()
        record.diagnosis      = f.get('diagnosis', '').strip()
        record.icd10_code     = f.get('icd10_code', '').strip()
        record.treatment_plan = f.get('treatment_plan', '').strip()
        record.doctor_notes   = f.get('doctor_notes', '').strip()
        
        if f.get('follow_up_date'):
            record.follow_up_date = datetime.strptime(f['follow_up_date'], '%Y-%m-%d').date()
        
        appt.status = 'completed'
        db.session.flush()



        prescription = None
        medicine_ids = request.form.getlist('medicine_id[]')
        if medicine_ids and any(mid for mid in medicine_ids):
            prescription = Prescription(
                medical_record_id = record.id,
                doctor_id         = doctor.id,
                notes             = f.get('prescription_notes', '').strip(),
            )
            db.session.add(prescription)
            db.session.flush()

            quantities   = request.form.getlist('quantity[]')
            dosages      = request.form.getlist('dosage[]')
            frequencies  = request.form.getlist('frequency[]')
            durations    = request.form.getlist('duration_days[]')
            instructions = request.form.getlist('instructions[]')

            for i, mid in enumerate(medicine_ids):
                if not mid: continue
                med = Medicine.query.get(int(mid))
                qty = int(quantities[i]) if quantities[i] else 1
                item = PrescriptionItem(
                    prescription_id = prescription.id,
                    medicine_id     = int(mid),
                    quantity        = qty,
                    dosage          = dosages[i] if i < len(dosages) else '',
                    frequency       = frequencies[i] if i < len(frequencies) else '',
                    duration_days   = int(durations[i]) if i < len(durations) and durations[i] else None,
                    instructions    = instructions[i] if i < len(instructions) else '',
                )
                db.session.add(item)
                
                before = med.stock_quantity
                med.stock_quantity = max(0, med.stock_quantity - qty)
                log = StockLog(
                    medicine_id     = med.id,
                    change_type     = 'export',
                    quantity_change = -qty,
                    quantity_before = before,
                    quantity_after  = med.stock_quantity,
                    note            = f'Xuất theo đơn thuốc bệnh nhân {patient.patient_code}',
                    created_by      = current_user.id,
                )
                db.session.add(log)

        exam_fee   = float(f.get('exam_fee', 100000))
        med_fee    = prescription.total_cost if prescription else 0
        total      = exam_fee + med_fee

        inv_count  = Invoice.query.count()
        inv_code   = f'HD-{datetime.utcnow().strftime("%Y%m%d")}-{inv_count+1:05d}'
        invoice = Invoice(
            invoice_code   = inv_code,
            patient_id     = patient.id,
            appointment_id = appt.id,
            exam_fee       = exam_fee,
            medicine_fee   = med_fee,
            total_amount   = total,
            status         = 'unpaid',
        )
        db.session.add(invoice)
        db.session.commit()
        flash('✅ Đã lưu bệnh án và tạo hóa đơn.', 'success')
        return redirect(url_for('doctor.view_record', record_id=record.id))

    medicines = Medicine.query.filter_by(is_active=True).order_by(Medicine.name).all()
    return render_template('doctor/create_record.html',
                           appt=appt, patient=patient,
                           medicines=medicines, history=history, record=record)

@doctor_bp.route('/records/<int:record_id>')
@login_required
@require_doctor
def view_record(record_id):
    record = MedicalRecord.query.get_or_404(record_id)
    return render_template('doctor/view_record.html', record=record)

@doctor_bp.route('/patients/<int:patient_id>/history')
@login_required
@require_doctor
def patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = (MedicalRecord.query
               .filter_by(patient_id=patient_id)
               .order_by(MedicalRecord.created_at.desc())
               .all())
    return render_template('doctor/patient_history.html', patient=patient, records=records)