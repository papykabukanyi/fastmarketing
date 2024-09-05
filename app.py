# import os
# import logging
# import pandas as pd
# import asyncio
# import json  # Ensure json is imported
# from dotenv import load_dotenv
# from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# import aiosmtplib
# import ssl
# import time

# # Load environment variables from .env file
# load_dotenv()

# # Flask app configuration
# app = Flask(__name__)
# app.secret_key = os.getenv('SECRET_KEY')

# # Logging configuration
# logging.basicConfig(level=logging.INFO)

# # SMTP Configuration
# SMTP_SERVER = os.getenv('SMTP_SERVER')
# SMTP_PORT = int(os.getenv('SMTP_PORT'))
# SMTP_USERNAME = os.getenv('SMTP_USERNAME')
# SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# # Define the templates file globally
# TEMPLATES_FILE = 'templates.json'

# async def send_email(subject, recipient_email, first_name, last_name, template_content, attachments=[], retries=3):
#     try:
#         logging.info(f"Preparing to send email to {recipient_email}")

#         msg = MIMEMultipart()
#         msg['From'] = SMTP_USERNAME
#         msg['To'] = recipient_email
#         msg['Subject'] = subject

#         # Mark the email as important
#         msg['X-Priority'] = '1'  # 1 is for High priority
#         msg['X-MSMail-Priority'] = 'High'
#         msg['Importance'] = 'High'

#         # Personalize the template
#         personalized_content = template_content.replace("{first name}", first_name).replace("{last name}", last_name)
#         msg.attach(MIMEText(personalized_content, 'html'))

#         # Attach each file if provided
#         for attachment in attachments:
#             if attachment:
#                 part = MIMEBase('application', 'octet-stream')
#                 part.set_payload(attachment.read())
#                 encoders.encode_base64(part)
#                 part.add_header('Content-Disposition', f'attachment; filename="{attachment.filename}"')
#                 msg.attach(part)

#         # Set up the TLS context
#         context = ssl.create_default_context()

#         # Send email asynchronously
#         await aiosmtplib.send(
#             msg,
#             hostname=SMTP_SERVER,
#             port=SMTP_PORT,
#             username=SMTP_USERNAME,
#             password=SMTP_PASSWORD,
#             use_tls=False,  # Ensure use_tls is set to False because we're using starttls
#             start_tls=True,  # Start TLS after establishing the connection
#             tls_context=context,
#         )

#         logging.info(f"Email sent to {recipient_email} successfully")
#         return {'status': 'success'}
    
#     except aiosmtplib.SMTPException as e:
#         logging.error(f"Failed to send email to {recipient_email}: {str(e)}")
#         if retries > 0:
#             wait_time = (4 - retries) * 2  # Exponential backoff
#             logging.info(f"Retrying in {wait_time} seconds...")
#             time.sleep(wait_time)
#             return await send_email(subject, recipient_email, first_name, last_name, template_content, attachments, retries-1)
#         return {'status': 'failure', 'error': str(e)}

# @app.route('/', methods=['GET', 'POST'])
# async def index():
#     if request.method == 'POST':
#         subject = request.form['subject']
#         template_content = request.form['template_content']

#         all_recipients = []

#         # Handling multiple attachments
#         attachments = request.files.getlist('attachments')

#         if 'file' in request.files and request.files['file'].filename:
#             file = request.files['file']
#             try:
#                 if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
#                     df = pd.read_excel(file)
#                 elif file.filename.endswith('.csv'):
#                     df = pd.read_csv(file)
#                 else:
#                     flash('Unsupported file format. Please upload an Excel or CSV file.', 'danger')
#                     return redirect(url_for('index'))

#                 for index, row in df.iterrows():
#                     email = row[1]  # Column B (index 1)
#                     name = row[2]   # Column C (index 2)
#                     if pd.notna(email) and pd.notna(name):
#                         name_parts = name.strip().split()
#                         first_name = name_parts[0] if len(name_parts) > 0 else ''
#                         last_name = name_parts[-1] if len(name_parts) > 1 else ''
#                         all_recipients.append({
#                             'email': email, 
#                             'first_name': first_name, 
#                             'last_name': last_name
#                         })
#             except Exception as e:
#                 flash(f"Error processing file: {str(e)}", 'danger')
#                 return redirect(url_for('index'))
#         else:
#             for i in range(len(request.form.getlist('recipient_email'))):
#                 all_recipients.append({
#                     'email': request.form.getlist('recipient_email')[i],
#                     'first_name': request.form.getlist('first_name')[i],
#                     'last_name': request.form.getlist('last_name')[i]
#                 })

#         batch_size = 500
#         total_recipients = len(all_recipients)

#         tasks = []
#         for i in range(0, total_recipients, batch_size):
#             batch = all_recipients[i:i + batch_size]
#             for recipient in batch:
#                 tasks.append(
#                     send_email(subject, recipient['email'], recipient['first_name'], recipient['last_name'], template_content, attachments)
#                 )

#             # Delay between batches to avoid hitting limits
#             await asyncio.sleep(2)

#         results = await asyncio.gather(*tasks)

#         success_count = sum(1 for result in results if result['status'] == 'success')
#         failure_count = sum(1 for result in results if result['status'] == 'failure')

#         if failure_count > 0:
#             flash(f'Emails sent with {failure_count} failures. {success_count} emails sent successfully.', 'danger')
#         else:
#             flash(f'Emails sent successfully to {total_recipients} recipients!', 'success')

#         return redirect(url_for('index'))

#     templates = load_templates()
#     return render_template('index.html', templates=templates)

# @app.route('/upload_file', methods=['POST'])
# async def upload_file():
#     if 'file' in request.files and request.files['file'].filename:
#         file = request.files['file']
#         try:
#             if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
#                 df = pd.read_excel(file)
#             elif file.filename.endswith('.csv'):
#                 df = pd.read_csv(file)
#             else:
#                 return jsonify({'error': 'Unsupported file format. Please upload an Excel or CSV file.'}), 400

#             recipients = []
#             for index, row in df.iterrows():
#                 email = row[1]  # Column B (index 1)
#                 name = row[2]   # Column C (index 2)
#                 if pd.notna(email) and pd.notna(name):
#                     name_parts = name.strip().split()
#                     first_name = name_parts[0] if len(name_parts) > 0 else ''
#                     last_name = name_parts[-1] if len(name_parts) > 1 else ''
#                     recipients.append({
#                         'email': email,
#                         'first_name': first_name,
#                         'last_name': last_name
#                     })

#             return jsonify(recipients)

#         except Exception as e:
#             return jsonify({'error': f"Error processing file: {str(e)}"}), 500

#     return jsonify({'error': 'No file uploaded.'}), 400

# @app.route('/save_template', methods=['POST'])
# async def save_template():
#     template_name = request.form['template_name']
#     template_content = request.form['template_content']
#     subject = request.form['subject']
    
#     templates = load_templates()
#     templates[template_name] = {
#         'subject': subject,
#         'content': template_content
#     }
    
#     with open(TEMPLATES_FILE, 'w') as f:
#         json.dump(templates, f)
    
#     return jsonify({"status": "success"})

# @app.route('/load_templates')
# async def load_templates_route():
#     templates = load_templates()
#     return jsonify(templates)

# @app.route('/delete_template/<template_name>', methods=['DELETE'])
# async def delete_template(template_name):
#     templates = load_templates()
#     if template_name in templates:
#         del templates[template_name]
#         with open(TEMPLATES_FILE, 'w') as f:
#             json.dump(templates, f)
#         return jsonify({"status": "success"})
#     return jsonify({"error": "Template not found"}), 404

# def load_templates():
#     if os.path.exists(TEMPLATES_FILE):
#         with open(TEMPLATES_FILE, 'r') as f:
#             return json.load(f)
#     return {}

# async def run_app():
#     app.run(debug=True, use_reloader=False)

# if __name__ == '__main__':
#     asyncio.run(run_app())


import os
import logging
import pandas as pd
import asyncio
import json
from io import BytesIO
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
import ssl
import time

# Load environment variables from .env file
load_dotenv()

# Flask app configuration
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Logging configuration
logging.basicConfig(level=logging.INFO)

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Define the templates file globally
TEMPLATES_FILE = 'templates.json'

async def send_email(subject, recipient_email, first_name, last_name, template_content, attachments=[], retries=3):
    try:
        logging.info(f"Preparing to send email to {recipient_email}")

        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Mark the email as important
        msg['X-Priority'] = '1'  # 1 is for High priority
        msg['X-MSMail-Priority'] = 'High'
        msg['Importance'] = 'High'

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
                attachment.seek(0)  # Reset file pointer

        # Set up the TLS context
        context = ssl.create_default_context()

        # Send email asynchronously
        await aiosmtplib.send(
            msg,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            use_tls=False,  # Ensure use_tls is set to False because we're using starttls
            start_tls=True,  # Start TLS after establishing the connection
            tls_context=context,
        )

        logging.info(f"Email sent to {recipient_email} successfully")
        return {'status': 'success'}
    
    except aiosmtplib.SMTPException as e:
        logging.error(f"Failed to send email to {recipient_email}: {str(e)}")
        if retries > 0:
            wait_time = (4 - retries) * 2  # Exponential backoff
            logging.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            return await send_email(subject, recipient_email, first_name, last_name, template_content, attachments, retries-1)
        return {'status': 'failure', 'error': str(e)}

@app.route('/', methods=['GET', 'POST'])
async def index():
    if request.method == 'POST':
        subject = request.form['subject']
        template_content = request.form['template_content']

        all_recipients = []

        # Handling multiple attachments
        attachments = []
        for attachment in request.files.getlist('attachments'):
            if attachment.filename:
                attachments.append(BytesIO(attachment.read()))
                attachments[-1].filename = attachment.filename

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

        tasks = []
        email_report = []

        for i in range(0, total_recipients, batch_size):
            batch = all_recipients[i:i + batch_size]
            for recipient in batch:
                task = send_email(subject, recipient['email'], recipient['first_name'], recipient['last_name'], template_content, attachments)
                tasks.append(task)
                email_report.append({'email': recipient['email'], 'status': 'pending'})

            await asyncio.sleep(2)  # Delay between batches to avoid hitting limits

        results = await asyncio.gather(*tasks)

        for idx, result in enumerate(results):
            email_report[idx]['status'] = result['status']

        success_count = sum(1 for result in results if result['status'] == 'success')
        failure_count = sum(1 for result in results if result['status'] == 'failure')

        if failure_count > 0:
            flash(f'Emails sent with {failure_count} failures. {success_count} emails sent successfully.', 'danger')
        else:
            flash(f'Emails sent successfully to {total_recipients} recipients!', 'success')

        return render_template('index.html', templates=load_templates(), email_report=email_report)

    templates = load_templates()
    return render_template('index.html', templates=templates)

@app.route('/upload_file', methods=['POST'])
async def upload_file():
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
async def save_template():
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
async def load_templates_route():
    templates = load_templates()
    return jsonify(templates)

@app.route('/delete_template/<template_name>', methods=['DELETE'])
async def delete_template(template_name):
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

async def run_app():
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    asyncio.run(run_app())
