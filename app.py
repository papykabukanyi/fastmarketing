from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Template
from gevent import monkey, sleep
from gevent.pool import Pool
from dotenv import load_dotenv

monkey.patch_all()

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Define the templates file globally
TEMPLATES_FILE = 'templates.json'

# SMTP Configuration (loaded from .env file)
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

def send_email(subject, recipient_email, first_name, last_name, template_content, attachments=[]):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Personalize the template
        personalized_content = template_content.replace("{first name}", first_name).replace("{last name}", last_name)
        msg.attach(MIMEText(personalized_content, 'html'))

        # Attach each file if provided
        for attachment in attachments:
            if attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{attachment.filename}"')
                msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, msg.as_string())

        return {'status': 'success'}
    except Exception as e:
        return {'status': 'failure', 'error': str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        subject = request.form['subject']
        template_content = request.form['template_content']

        all_recipients = []

        # Handling multiple attachments
        attachments = request.files.getlist('attachments')

        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            try:
                if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                    df = pd.read_excel(file)
                elif file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    flash('Unsupported file format. Please upload an Excel or CSV file.', 'danger')
                    return redirect(url_for('index'))

                for index, row in df.iterrows():
                    email = row[1]  # Column B (index 1)
                    name = row[2]   # Column C (index 2)
                    if pd.notna(email) and pd.notna(name):
                        name_parts = name.strip().split()
                        first_name = name_parts[0] if len(name_parts) > 0 else ''
                        last_name = name_parts[-1] if len(name_parts) > 1 else ''
                        all_recipients.append({
                            'email': email, 
                            'first_name': first_name, 
                            'last_name': last_name
                        })
            except Exception as e:
                flash(f"Error processing file: {str(e)}", 'danger')
                return redirect(url_for('index'))
        else:
            for i in range(len(request.form.getlist('recipient_email'))):
                all_recipients.append({
                    'email': request.form.getlist('recipient_email')[i],
                    'first_name': request.form.getlist('first_name')[i],
                    'last_name': request.form.getlist('last_name')[i]
                })

        batch_size = 500
        total_recipients = len(all_recipients)
        pool = Pool(10)

        success_count = 0
        failure_count = 0
        for i in range(0, total_recipients, batch_size):
            batch = all_recipients[i:i + batch_size]
            jobs = [pool.spawn(send_email, subject, recipient['email'], recipient['first_name'], recipient['last_name'], template_content, attachments) for recipient in batch]
            pool.join()

            for job in jobs:
                if job.value['status'] == 'success':
                    success_count += 1
                else:
                    failure_count += 1

        if failure_count > 0:
            flash(f'Emails sent with {failure_count} failures. {success_count} emails sent successfully.', 'danger')
        else:
            flash(f'Emails sent successfully to {total_recipients} recipients!', 'success')

        return redirect(url_for('index'))

    templates = load_templates()
    return render_template('index.html', templates=templates)

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        try:
            if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                df = pd.read_excel(file)
            elif file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                return jsonify({'error': 'Unsupported file format. Please upload an Excel or CSV file.'}), 400

            recipients = []
            for index, row in df.iterrows():
                email = row[1]  # Column B (index 1)
                name = row[2]   # Column C (index 2)
                if pd.notna(email) and pd.notna(name):
                    name_parts = name.strip().split()
                    first_name = name_parts[0] if len(name_parts) > 0 else ''
                    last_name = name_parts[-1] if len(name_parts) > 1 else ''
                    recipients.append({
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name
                    })

            return jsonify(recipients)

        except Exception as e:
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500

    return jsonify({'error': 'No file uploaded.'}), 400

@app.route('/save_template', methods=['POST'])
def save_template():
    template_name = request.form['template_name']
    template_content = request.form['template_content']
    subject = request.form['subject']
    
    templates = load_templates()
    templates[template_name] = {
        'subject': subject,
        'content': template_content
    }
    
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f)
    
    return jsonify({"status": "success"})

@app.route('/load_templates')
def load_templates_route():
    templates = load_templates()
    return jsonify(templates)

@app.route('/delete_template/<template_name>', methods=['DELETE'])
def delete_template(template_name):
    templates = load_templates()
    if template_name in templates:
        del templates[template_name]
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(templates, f)
        return jsonify({"status": "success"})
    return jsonify({"error": "Template not found"}), 404

def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    return {}

if __name__ == '__main__':
    app.run(debug=True)
