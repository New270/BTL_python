from app import create_app, db
from app.models import User  # Import thêm bảng User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Tạo bảng nếu chưa có
        db.create_all()
        
        # Tự động tạo tài khoản Admin mặc định nếu database trống
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("=> Đã khởi tạo tài khoản Admin thành công!")
            
    app.run(debug=True, port=5000)