from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import pandas as pd
from twilio.rest import Client
import os
from dotenv import load_dotenv
import logging

load_dotenv()
app = Flask(__name__)
CORS(app) 

# Fetch Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
if not all([account_sid, auth_token, twilio_whatsapp_number]):
    raise ValueError("Twilio credentials are not properly set in environment variables")

# Initialize Twilio Client
client = Client(account_sid, auth_token)
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# API to upload and process the Excel file
@app.route('/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    print(f"Received file: {file.filename}")
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Invalid file format. Please upload an Excel file.'}), 400

    try:
        df = pd.read_excel(file, header=4)
        df_filtered = df[['Unnamed: 0', 'Unnamed: 25', 'Unnamed: 26']].copy()
        df_filtered.columns = ['Name', 'Total Percentage', 'WhatsAppNumber']
        df_filtered.dropna(subset=['Name', 'WhatsAppNumber'], inplace=True)
        df_filtered['Total Percentage'] = pd.to_numeric(df_filtered['Total Percentage'], errors='coerce')
        df_filtered.dropna(subset=['Total Percentage'], inplace=True)

        print(f"Excel file loaded successfully: {df_filtered.head()}")  
    except Exception as e:
        logging.error(f"Error reading Excel file: {str(e)}")
        return jsonify({'error': f"Error reading Excel file: {str(e)}"}), 400
    
    low_attendance_students = df_filtered[df_filtered['Total Percentage'] < 60]
    if low_attendance_students.empty:
        return jsonify({'message': 'No students with less than 60% attendance found.'}), 200
    print(f"Low attendance students: {low_attendance_students}")
    return low_attendance_students.to_json(orient='records')

# API to send WhatsApp messages
@app.route('/send-messages', methods=['POST'])
def send_messages():
    students = request.json
    if not students:
        return jsonify({'error': 'No students provided for messaging'}), 400

    for student in students:
        try:
            message = client.messages.create(
                body=f"Dear {student['Name']}, your attendance is below 60%. Please improve it.",
                from_=f'whatsapp:{twilio_whatsapp_number}',  # WhatsApp number from Twilio
                to=f"whatsapp:+{student['WhatsAppNumber']}"
            )
            print(f"Message sent to {student['Name']} ({student['WhatsAppNumber']})")
        except Exception as e:
            logging.error(f"Error sending message to {student['Name']} ({student['WhatsAppNumber']}): {str(e)}")
    return jsonify({'status': 'Messages sent successfully'})

if __name__ == '__main__':
    app.run(debug=True)
