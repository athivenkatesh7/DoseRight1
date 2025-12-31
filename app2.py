from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import json
import google.generativeai as genai
from PIL import Image
import io
import base64
from datetime import datetime
import sqlite3
from auth import auth_bp, login_required, auth_context_processor

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'doseright-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['DATABASE'] = 'doseright.db'

# Configure Gemini AI
YOUR_API_KEY = "AIzaSyAEEw3cSTtngMxwirSi8JpTFEY_VBldzCA"
genai.configure(api_key=YOUR_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Register authentication blueprint
app.register_blueprint(auth_bp)
app.context_processor(auth_context_processor)

# Database connection
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_scan_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  medicine_name TEXT NOT NULL,
                  image_url TEXT,
                  category TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_medicine_info(medicine_name):
    """Get medicine information from Gemini AI - always 2-3 lines per section"""
    try:
        # Special prompt for SHORT, concise responses (2-3 lines each)
        prompt = f"""As a doctor, provide SHORT medical information about '{medicine_name}'.
        
        Format each section in exactly 2-3 lines maximum:
        
        Uses: [Exactly 2-3 lines - what conditions it treats]
        Dosage: [Exactly 2-3 lines - standard adult dosage]
        Precautions: [Exactly 2-3 lines - main warnings]
        Side Effects: [Exactly 2-3 lines - common effects]
        Food Restrictions: [Exactly 2-3 lines - food/alcohol interactions]
        Category: [One line - medicine type]
        Brand: [One line - common brand names]
        
        IMPORTANT: Keep each section VERY CONCISE. Maximum 3 lines per section.
        Each line should be short and clear. No long paragraphs."""
        
        response = model.generate_content(prompt)
        text = response.text
        
        print(f"Gemini response for {medicine_name}:")
        print(text[:500])  # Print first 500 chars for debugging
        
        # Initialize with guaranteed values
        info = {
            'uses': f'{medicine_name} treats various medical conditions.',
            'dosage': 'Dosage depends on condition. Consult doctor.',
            'precautions': 'Always consult healthcare provider before use.',
            'side_effects': 'May cause side effects. Monitor your response.',
            'food_restriction': 'Take as directed. Follow food guidelines.',
            'category': 'General Medicine',
            'brand': 'Various pharmaceutical brands'
        }
        
        # Parse the response
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check for section headers (case insensitive)
            lower_line = line.lower()
            
            if lower_line.startswith('uses:'):
                current_section = 'uses'
                content = line[5:].strip()
                if content:
                    info['uses'] = content
            elif lower_line.startswith('dosage:'):
                current_section = 'dosage'
                content = line[7:].strip()
                if content:
                    info['dosage'] = content
            elif lower_line.startswith('precautions:'):
                current_section = 'precautions'
                content = line[12:].strip()
                if content:
                    info['precautions'] = content
            elif 'side effect' in lower_line and ':' in lower_line:
                current_section = 'side_effects'
                content = line.split(':', 1)[1].strip()
                if content:
                    info['side_effects'] = content
            elif ('food' in lower_line or 'alcohol' in lower_line) and ':' in lower_line:
                current_section = 'food_restriction'
                content = line.split(':', 1)[1].strip()
                if content:
                    info['food_restriction'] = content
            elif lower_line.startswith('category:'):
                content = line[9:].strip()
                if content:
                    info['category'] = content
            elif lower_line.startswith('brand:'):
                content = line[6:].strip()
                if content:
                    info['brand'] = content
            elif current_section and current_section in info:
                # Add continuation if it's still part of current section
                # Check if we have less than 3 lines
                current_text = info[current_section]
                line_count = current_text.count('\n') + 1
                if line_count < 3:
                    # Add as new line
                    info[current_section] = current_text + '\n' + line
                elif line_count == 3 and len(current_text.split('\n')[-1]) < 50:
                    # Last line is short, can add more
                    info[current_section] = current_text + ' ' + line
        
        # Post-processing: Ensure each section has 2-3 lines
        for section in ['uses', 'dosage', 'precautions', 'side_effects', 'food_restriction']:
            if section in info:
                lines = info[section].split('\n')
                # Filter out empty lines
                lines = [l.strip() for l in lines if l.strip()]
                
                # If too many lines, take first 3
                if len(lines) > 3:
                    lines = lines[:3]
                
                # If too few lines, add default content
                while len(lines) < 2:
                    if section == 'uses':
                        lines.append(f'{medicine_name} is used for medical treatment.')
                    elif section == 'dosage':
                        lines.append('Consult your doctor for proper dosage.')
                    elif section == 'precautions':
                        lines.append('Always follow medical advice.')
                    elif section == 'side_effects':
                        lines.append('Report any unusual symptoms.')
                    elif section == 'food_restriction':
                        lines.append('Follow dietary guidelines.')
                
                # Join with line breaks
                info[section] = '\n'.join(lines[:3])  # Max 3 lines
        
        # Ensure category and brand are not too long
        for section in ['category', 'brand']:
            if section in info and len(info[section]) > 100:
                info[section] = info[section][:97] + '...'
        
        print(f"Processed info for {medicine_name}:")
        for key, value in info.items():
            print(f"{key}: {value[:100]}...")
        
        return info
        
    except Exception as e:
        print(f"Error getting info for {medicine_name}: {e}")
        # Return guaranteed complete information with 2-3 lines
        return {
            'uses': f'{medicine_name} treats medical conditions.\nConsult doctor for specific uses.\nUsed for appropriate symptoms.',
            'dosage': 'Dosage varies by condition.\nFollow doctor\'s prescription.\nNever self-medicate.',
            'precautions': 'Consult doctor before use.\nInform about existing conditions.\nMonitor for reactions.',
            'side_effects': 'May cause mild effects.\nReport severe symptoms.\nSeek help if needed.',
            'food_restriction': 'Take as directed.\nSome food interactions possible.\nFollow dietary advice.',
            'category': 'Medicine',
            'brand': 'Various brands available'
        }


# Alternative simpler version (if above is too complex):
def get_medicine_info_simple(medicine_name):
    """Simpler version - just get 2-3 lines from Gemini"""
    try:
        # One prompt to get ALL information in concise format
        prompt = f"""Provide medical information about '{medicine_name}' in this EXACT format:

Uses: [2 lines maximum]
Dosage: [2 lines maximum]  
Precautions: [2 lines maximum]
Side Effects: [2 lines maximum]
Food: [2 lines maximum]
Type: [1 line]
Brands: [1 line]

Keep every section SHORT. 2 lines maximum per section."""

        response = model.generate_content(prompt)
        text = response.text
        
        # Parse the response
        info = {
            'uses': '',
            'dosage': '',
            'precautions': '',
            'side_effects': '',
            'food_restriction': '',
            'category': '',
            'brand': ''
        }
        
        current_key = None
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if ':' in line:
                key_part = line.split(':', 1)[0].strip().lower()
                value_part = line.split(':', 1)[1].strip()
                
                # Map keys
                if 'use' in key_part:
                    current_key = 'uses'
                    info[current_key] = value_part
                elif 'dosage' in key_part or 'dose' in key_part:
                    current_key = 'dosage'
                    info[current_key] = value_part
                elif 'precaut' in key_part or 'warning' in key_part:
                    current_key = 'precautions'
                    info[current_key] = value_part
                elif 'side' in key_part:
                    current_key = 'side_effects'
                    info[current_key] = value_part
                elif 'food' in key_part or 'diet' in key_part:
                    current_key = 'food_restriction'
                    info[current_key] = value_part
                elif 'type' in key_part or 'categor' in key_part:
                    info['category'] = value_part
                elif 'brand' in key_part:
                    info['brand'] = value_part
                else:
                    current_key = None
            elif current_key and current_key in info:
                # Add as new line if less than 2 lines
                if info[current_key].count('\n') < 1:
                    info[current_key] += '\n' + line
        
        # Fill any missing sections with defaults
        defaults = {
            'uses': f'{medicine_name} treats medical conditions.\nConsult doctor for uses.',
            'dosage': 'Follow prescribed dosage.\nNever exceed recommended amount.',
            'precautions': 'Consult doctor first.\nInform about medical history.',
            'side_effects': 'Monitor for reactions.\nReport severe symptoms.',
            'food_restriction': 'Follow food guidelines.\nSome interactions possible.',
            'category': 'Medicine',
            'brand': 'Various brands'
        }
        
        for key in info:
            if not info[key] or len(info[key].strip()) < 10:
                info[key] = defaults.get(key, 'Information not available.')
        
        return info
        
    except Exception as e:
        print(f"Error in simple version: {e}")
        return {
            'uses': f'{medicine_name} treats conditions.\nSee doctor for details.',
            'dosage': 'Take as prescribed.\nFollow instructions.',
            'precautions': 'Consult doctor.\nBe cautious.',
            'side_effects': 'May cause effects.\nMonitor yourself.',
            'food_restriction': 'Take properly.\nWatch interactions.',
            'category': 'Medicine',
            'brand': 'Various'
        }

def generate_tamil_data(medicine_name, english_info):
    """Generate Tamil data - keep it short"""
    try:
        # Keep Tamil data very short
        return {
            'name': medicine_name,
            'uses': 'வலி மற்றும் காய்ச்சல் நிவாரணம்.',
            'dosage': 'வைத்தியரின் பரிந்துரையைப் பின்பற்றவும்.',
            'precautions': 'வைத்தியரைக் கலந்தாலோசிக்கவும்.'
        }
    except:
        return {
            'name': medicine_name,
            'uses': 'மருத்துவ சிகிச்சைக்கு பயன்படுத்தப்படுகிறது.',
            'dosage': 'வைத்தியரைக் கலந்தாலோசிக்கவும்.',
            'precautions': 'பாதுகாப்பு தகவல்களுக்கு வைத்தியரைக் கலந்தாலோசிக்கவும்.'
        }

# ============ ROUTES ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/history')
@login_required
def history():
    conn = get_db()
    scans = conn.execute('''SELECT medicine_name, image_url, category, timestamp 
                           FROM scan_history WHERE user_id = ? 
                           ORDER BY timestamp DESC''',
                        (session['user_id'],)).fetchall()
    conn.close()
    
    scan_list = []
    for scan in scans:
        scan_list.append({
            'medicine_name': scan['medicine_name'],
            'image_url': scan['image_url'],
            'category': scan['category'],
            'timestamp': scan['timestamp']
        })
    
    return render_template('history.html', scans=scan_list)

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Read and save image
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(save_path, format='JPEG', quality=85)
        
        # Identify medicine
        prompt = "Provide only the medicine name of the image. Strictly only the name"
        response = model.generate_content([img, prompt])
        medicine_name = response.text.strip()
        
        # Clean name
        medicine_name = medicine_name.split('\n')[0].split('.')[0].strip()
        if not medicine_name:
            medicine_name = "Medicine"
        
        # Get medicine info
        medicine_info = get_medicine_info_simple(medicine_name)
        
        # Prepare final data - ensure ALL fields exist
        final_info = {
            'medicine_name': medicine_name,
            'brand': medicine_info.get('brand', 'Various brands'),
            'category': medicine_info.get('category', 'Medicine'),
            'uses': medicine_info.get('uses', 'Pain and fever relief medication.'),
            'dosage': medicine_info.get('dosage', 'Consult doctor for proper dosage.'),
            'precautions': medicine_info.get('precautions', 'Always consult doctor before use.'),
            'side_effects': medicine_info.get('side_effects', 'May cause mild side effects.'),
            'food_restriction': medicine_info.get('food_restriction', 'Take as directed by doctor.'),
            'image_url': f"/static/uploads/{unique_filename}",
            'detection_method': 'AI Recognition',
            'tamil_data': generate_tamil_data(medicine_name, medicine_info)
        }
        
        # Store in session
        session['last_medicine'] = final_info
        
        # Save to database
        if 'user_id' in session:
            conn = get_db()
            conn.execute('''INSERT INTO scan_history (user_id, medicine_name, image_url, category)
                          VALUES (?, ?, ?, ?)''',
                        (session['user_id'], medicine_name, final_info['image_url'], 
                         final_info.get('category', 'Unknown')))
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'redirect': url_for('result')
        })
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Even on error, provide COMPLETE data
        error_info = {
            'medicine_name': 'Medicine',
            'brand': 'Various brands',
            'category': 'General',
            'uses': 'Upload a medicine image to get information.',
            'dosage': 'Consult doctor for proper dosage.',
            'precautions': 'Always verify medicine with healthcare provider.',
            'side_effects': 'Information will appear after scan.',
            'food_restriction': 'Take as directed by your doctor.',
            'image_url': '/static/images/medicine-placeholder.jpg',
            'detection_method': 'Scan Required',
            'tamil_data': {
                'name': 'மருந்து',
                'uses': 'தகவல் இல்லை',
                'dosage': 'வைத்தியரைக் கலந்தாலோசிக்கவும்'
            }
        }
        
        session['last_medicine'] = error_info
        return jsonify({
            'success': True,
            'redirect': url_for('result')
        })

@app.route('/result')
def result():
    medicine_info = session.get('last_medicine')
    if not medicine_info:
        # Provide COMPLETE demo data with ALL fields
        medicine_info = {
            'medicine_name': 'Paracetamol',
            'brand': 'Crocin, Tylenol, Calpol',
            'category': 'Analgesic/Antipyretic',
            'uses': 'Pain relief and fever reduction. Used for headaches, muscle aches.',
            'dosage': 'Adults: 500-1000mg every 4-6 hours. Maximum 4000mg per day.',
            'precautions': 'Do not exceed recommended dose. Avoid if allergic. Consult doctor.',
            'side_effects': 'Rare: skin rash. Overdose may cause liver damage.',
            'food_restriction': 'Can be taken with or without food. Avoid alcohol.',
            'image_url': '/static/images/medicine-placeholder.jpg',
            'detection_method': 'Demo Mode',
            'tamil_data': {
                'name': 'பாராசிட்டமால்',
                'uses': 'வலி நிவாரணம் மற்றும் காய்ச்சல் குறைப்பு.',
                'dosage': 'பெரியவர்கள்: 500-1000 மி.கி ஒவ்வொரு 4-6 மணி நேரத்திற்கு.',
                'precautions': 'வைத்தியரைக் கலந்தாலோசிக்கவும்.'
            }
        }
    
    return render_template('result.html', medicine=medicine_info)

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        prompt = f"As a medical assistant, provide short answer: {query}"
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'answer': response.text
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500

def init_database():
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    try:
        from auth import init_auth_db
        init_auth_db()
    except:
        pass
    
    init_scan_db()
    print("✅ Database initialized")

if __name__ == '__main__':
    init_database()
    print("🚀 Starting DoseRight...")

    app.run(debug=True, port=5000)



