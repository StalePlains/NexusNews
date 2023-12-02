from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
import stripe
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  first_name = db.Column(db.String(100))
  last_name = db.Column(db.String(100))
  email = db.Column(db.String(120), unique=True, nullable=False)
  phone = db.Column(db.String(20))
  username = db.Column(db.String(80), unique=True, nullable=False)
  password_hash = db.Column(db.String(128))

  def __init__(self, first_name, last_name, email, phone, username, password):
      self.first_name = first_name
      self.last_name = last_name
      self.email = email
      self.phone = phone
      self.set_password(password)

  def set_password(self, password):
      self.password_hash = generate_password_hash(password)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/email-bot')
def email_bot():
  return render_template('email-bot.html')

@app.route('/checkout')
def checkout():
  return render_template('stripepayment.html')

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            ui_mode = 'embedded',
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': '{{PRICE_ID}}',
                    'quantity': 1,
                },
            ],
            mode='payment',
            return_url='/return.html?session_id={CHECKOUT_SESSION_ID}',
        )
    except Exception as e:
        return str(e)

    return jsonify(clientSecret=session.client_secret)

@app.route('/session-status', methods=['GET'])
def session_status():
  session = stripe.checkout.Session.retrieve(request.args.get('session_id'))

  return jsonify(status=session.status, customer_email=session.customer_details.email)

@app.route('/send-emails', methods=['POST'])
def send_emails():
  sender_email = request.form['fromEmail']
  sender_password = request.form['emailPass']
  email_count = int(request.form['emailCount'])
  subject = request.form['subject']
  message_text = request.form['message']
  file = request.files['excelFile']
  if file and file.filename != '' and type(file.filename) is not None:
  
      df = pd.read_excel(file)
  
      # Set up the SMTP server
      server = smtplib.SMTP('smtp-mail.outlook.com', 587)  # Example for Gmail
      server.starttls()
      server.login(sender_email, sender_password)
  
      for _, row in df.iterrows():
          recipient_email = row['Email']  # Assuming the column is named 'Email'
          for _ in range(email_count):
              msg = MIMEMultipart()
              msg['From'] = sender_email
              msg['To'] = recipient_email
              msg['Subject'] = subject
  
              msg.attach(MIMEText(message_text, 'plain'))
  
              try:
                  server.send_message(msg)
              except Exception as e:
                  print(e)
                  return 'An error occurred while sending emails', 500
  
      server.quit()
      return 'Emails sent successfully', 200
  else:
      return 'No file uploaded', 400

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        new_user = User(first_name, last_name, email, phone, password)
        print(f"Added user {new_user.username} to the database")
        db.session.add(new_user)
        db.session.commit()

      
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('index'))

        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/view-users')
def view_users():
    users = User.query.all()
    return render_template('viewtable.html', users=users)

with app.app_context():
  db.create_all()
if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=8000)