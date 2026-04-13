import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- 1. ตั้งค่า Database ให้รองรับ Render (PostgreSQL) ---
uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///local_comments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. สร้าง Model (ตารางคอมเมนต์) ---
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.String(50), nullable=False)

# สร้างตารางอัตโนมัติ
with app.app_context():
    db.create_all()

def get_location(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5).json()
        if response.get('status') == 'success':
            return response.get('country'), response.get('city')
    except:
        pass
    return "Unknown", "Unknown"

# --- 3. Routes (ปรับให้ใช้ SQLAlchemy) ---

@app.route('/api/comments', methods=['GET'])
def get_comments():
    profile = request.args.get('profile_name')
    # ดึงข้อมูลจาก DB แบบง่ายๆ ไม่ต้องเขียน SQL เอง
    rows = Comment.query.filter_by(profile_name=profile).order_by(Comment.id.desc()).all()
    
    comments = [
        {
            "author": r.author, 
            "content": r.content, 
            "date": r.created_at, 
            "country": r.country, 
            "city": r.city
        } for r in rows
    ]
    return jsonify(comments)

@app.route('/api/comments', methods=['POST'])
def add_comment():
    data = request.json
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in user_ip: user_ip = user_ip.split(',')[0].strip()
    
    country, city = get_location(user_ip)
    
    # บันทึกข้อมูลแบบ SQLAlchemy
    new_comment = Comment(
        profile_name=data.get('profile_name'),
        author=data.get('author'),
        email=data.get('email'),
        content=data.get('content'),
        country=country,
        city=city,
        ip_address=user_ip,
        created_at=datetime.now().strftime("%B %d, %Y")
    )
    
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({"status": "Success", "detected_location": f"{city}, {country}"}), 201

if __name__ == '__main__':
    app.run(debug=True)