from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import Medicine, StockLog

medicine_bp = Blueprint('medicine', __name__)

def require_staff(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'doctor', 'assistant', 'receptionist'):
            flash('Không có quyền truy cập.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated

@medicine_bp.route('/')
@login_required
@require_staff
def index():
    q    = request.args.get('q', '').strip()
    show = request.args.get('show', 'all')
    query = Medicine.query.filter_by(is_active=True)
    if q:
        query = query.filter(db.or_(
            Medicine.name.ilike(f'%{q}%'),
            Medicine.active_ingredient.ilike(f'%{q}%'),
        ))
    medicines = query.order_by(Medicine.name).all()
    if show == 'low':
        medicines = [m for m in medicines if m.is_low_stock]
    elif show == 'expiring':
        medicines = [m for m in medicines if m.is_near_expiry or m.is_expired]

    low_count     = sum(1 for m in Medicine.query.all() if m.is_low_stock)
    expiring_count= sum(1 for m in Medicine.query.all() if m.is_near_expiry)
    return render_template('medicine/index.html',
                           medicines=medicines, q=q, show=show,
                           low_count=low_count, expiring_count=expiring_count)

@medicine_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_staff
def new_medicine():
    if request.method == 'POST':
        f = request.form
        med = Medicine(
            name              = f.get('name', '').strip(),
            active_ingredient = f.get('active_ingredient', '').strip(),
            dosage_form       = f.get('dosage_form', '').strip(),
            unit              = f.get('unit', '').strip(),
            price             = float(f.get('price', 0)),
            stock_quantity    = int(f.get('stock_quantity', 0)),
            min_stock_alert   = int(f.get('min_stock_alert', 10)),
            expiry_date       = datetime.strptime(f['expiry_date'], '%Y-%m-%d').date() if f.get('expiry_date') else None,
            manufacturer      = f.get('manufacturer', '').strip(),
            description       = f.get('description', '').strip(),
        )
        db.session.add(med)
        db.session.flush()
        if med.stock_quantity > 0:
            log = StockLog(
                medicine_id     = med.id,
                change_type     = 'import',
                quantity_change = med.stock_quantity,
                quantity_before = 0,
                quantity_after  = med.stock_quantity,
                note            = 'Nhập kho lần đầu',
                created_by      = current_user.id,
            )
            db.session.add(log)
        db.session.commit()
        flash(f'✅ Đã thêm thuốc: {med.name}', 'success')
        return redirect(url_for('medicine.index'))
    return render_template('medicine/new.html')

@medicine_bp.route('/<int:med_id>/stock', methods=['POST'])
@login_required
@require_staff
def update_stock(med_id):
    med    = Medicine.query.get_or_404(med_id)
    action = request.form.get('action')
    qty    = int(request.form.get('quantity', 0))
    note   = request.form.get('note', '')
    before = med.stock_quantity

    if action == 'import':
        med.stock_quantity += qty
    elif action == 'adjust':
        med.stock_quantity = qty

    log = StockLog(
        medicine_id     = med.id,
        change_type     = action,
        quantity_change = med.stock_quantity - before,
        quantity_before = before,
        quantity_after  = med.stock_quantity,
        note            = note,
        created_by      = current_user.id,
    )
    db.session.add(log)
    db.session.commit()
    flash('✅ Đã cập nhật tồn kho.', 'success')
    return redirect(url_for('medicine.index'))