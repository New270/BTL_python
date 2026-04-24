from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models import Patient, Doctor, Appointment, Invoice, Medicine, User, Receptionist, Assistant

admin_bp = Blueprint('admin', __name__)

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Chỉ Admin mới có quyền truy cập.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@require_admin
def dashboard():
    total_patients  = Patient.query.count()
    total_doctors   = Doctor.query.count()
    total_appts     = Appointment.query.count()
    today_appts     = Appointment.query.filter(
        db.func.date(Appointment.scheduled_at) == date.today()).count()
    unpaid_invoices = Invoice.query.filter_by(status='unpaid').count()
    low_medicines   = [m for m in Medicine.query.all() if m.is_low_stock]
    return render_template('admin/dashboard.html',
                           total_patients=total_patients,
                           total_doctors=total_doctors,
                           total_appts=total_appts,
                           today_appts=today_appts,
                           unpaid_invoices=unpaid_invoices,
                           low_medicines=low_medicines)

@admin_bp.route('/users')
@login_required
@require_admin
def users():
    all_users = User.query.order_by(User.role, User.id).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@require_admin
def new_user():
    if request.method == 'POST':
        f    = request.form
        role = f.get('role')
        user = User(username=f['username'].strip(), role=role)
        user.set_password(f['password'])
        db.session.add(user)
        db.session.flush()

        if role == 'doctor':
            profile = Doctor(user_id=user.id, full_name=f.get('full_name','').strip(),
                             specialty=f.get('specialty',''), phone=f.get('phone',''),
                             license_number=f.get('license_number',''))
            db.session.add(profile)
        elif role == 'receptionist':
            profile = Receptionist(user_id=user.id, full_name=f.get('full_name','').strip(),
                                   phone=f.get('phone',''))
            db.session.add(profile)
        elif role == 'assistant':
            doctor_id = f.get('doctor_id')
            if not doctor_id:
                db.session.rollback() 
                flash('Lỗi: Bạn bắt buộc phải Phân công Bác sĩ cho Trợ lý này!', 'danger')
                return redirect(url_for('admin.new_user'))

            profile = Assistant(user_id=user.id, full_name=f.get('full_name','').strip(),
                                phone=f.get('phone',''), doctor_id=doctor_id)
            db.session.add(profile)

        db.session.commit()
        flash(f'✅ Đã tạo tài khoản {user.username} [{role}].', 'success')
        return redirect(url_for('admin.users'))

    doctors = Doctor.query.all()
    return render_template('admin/new_user.html', doctors=doctors)

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@require_admin
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True  # Đổi trạng thái từ Chờ duyệt sang Hoạt động
    db.session.commit()
    flash(f'✅ Đã phê duyệt tài khoản: {user.username}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Tự động lấy hồ sơ tương ứng
    profile = None
    if user.role == 'doctor': profile = user.doctor
    elif user.role == 'receptionist': profile = user.receptionist
    elif user.role == 'assistant': profile = user.assistant
    elif user.role == 'patient': profile = user.patient

    if request.method == 'POST':
        f = request.form
        # 1. Cập nhật tài khoản chính
        user.username = f.get('username', '').strip()
        if f.get('password'): 
            user.set_password(f['password'])
        
        # Quyền đăng nhập (Khóa/Mở khóa)
        user.is_active = 'is_active' in f 

        # 2. Cập nhật hồ sơ chi tiết
        if profile:
            profile.full_name = f.get('full_name', '').strip()
            profile.phone = f.get('phone', '').strip()
            
            if user.role == 'doctor':
                profile.specialty = f.get('specialty', '').strip()
                lic_num = f.get('license_number', '').strip()
                profile.license_number = lic_num or None
            elif user.role == 'assistant':
                profile.doctor_id = f.get('doctor_id') or None

        db.session.commit()
        flash(f'✅ Đã cập nhật thông tin cho {user.username}.', 'success')
        return redirect(url_for('admin.users'))

    doctors = Doctor.query.all() if user.role == 'assistant' else []
    return render_template('admin/edit_user.html', user=user, profile=profile, doctors=doctors)