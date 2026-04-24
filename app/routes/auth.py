from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(f'auth.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        expected_role = request.form.get('expected_role') # Lấy vai trò từ form

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # KIỂM TRA: Nếu có chọn vai trò cụ thể, tài khoản phải khớp vai trò đó
            if expected_role and user.role != expected_role:
                flash(f'Tài khoản này không có quyền đăng nhập với vai trò {expected_role}.', 'danger')
                return redirect(url_for('auth.login'))
            
            if not user.is_active:
                flash('Tài khoản đang chờ phê duyệt.', 'warning')
                return redirect(url_for('auth.login'))

            login_user(user)
            return redirect(url_for('auth.dashboard'))
        flash('Sai tài khoản hoặc mật khẩu.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role
    if role == 'doctor':
        return redirect(url_for('doctor.dashboard'))
    elif role == 'receptionist':
        return redirect(url_for('receptionist.dashboard'))
    elif role == 'assistant':
        return redirect(url_for('assistant.dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient.dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công.', 'success')
    return redirect(url_for('auth.login'))
from app.models import User, Patient, generate_patient_code # Đảm bảo đã import đủ

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')

        # Kiểm tra username tồn tại
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'danger')
            return redirect(url_for('auth.register'))

        # 1. Tạo tài khoản User
        new_user = User(username=username, role='patient', is_active=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush() # Để lấy được new_user.id

        # 2. Tạo hồ sơ Patient tương ứng
        new_patient = Patient(
            user_id=new_user.id,
            patient_code=generate_patient_code(),
            full_name=full_name,
            phone=phone
        )
        db.session.add(new_patient)
        db.session.commit()

        flash('Đăng ký thành công! Tài khoản của bạn đang chờ Admin phê duyệt.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')