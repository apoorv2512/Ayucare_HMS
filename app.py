#importing necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from datetime import datetime
import pickle
import numpy as np 
import pandas as pd 
from datetime import datetime,date
from models import db, User,dailyrecord,UserProfile  #  healthrecords is also defined in models.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import fitz  # PyMuPDF


app = Flask(__name__)
GMAIL_USER = "ayucarefitbitdemo@gmail.com"
GMAIL_APP_PASSWORD = "vhuv yils lyfc lbay"

SYSTOLIC_PEAK = 130
DIASTOLIC_PEAK = 90
FASTING_SUGAR_PEAK = 126
BEDTIME_SUGAR_PEAK = 140

# Function to send an email alert
def send_peak_alert_email(to_email, data_type, value):
    print(f"Sending email to {to_email} for {data_type} = {value}")
    subject = f"🚨 Ayucare Health Alert: High {data_type} Detected"
    body = f"""
    Dear user,

    We detected that your {data_type} reading is higher than the peak threshold:

    {data_type}: {value}

    Please consult your healthcare provider immediately.

    Regards,
    Ayucare Team
    """

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/AyuCare_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Required for session management
#database Initalization
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()
# creating google auth

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=("312305571102-69senclm6pe4lnre2g4g4k9brm146b70.apps.googleusercontent.com"),  # Use the Client ID from Google Cloud Console
    client_secret=("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"),  # Use the Client Secret from Google Cloud Console
    
    authorize_params=None,
    
    access_token_params=None,
    
    refresh_token_url=None,
   server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid profile email",
    }
)
#Callback function for google auth
@app.route('/callback')
def authorize():
    token = google.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = google.parse_id_token(token, nonce=nonce)
    
    if not user_info:
        flash("Failed to retrieve user information.", "error")
        return redirect(url_for("login"))

    # Check if the user already exists in PostgreSQL
    user = User.query.filter_by(email=user_info['email']).first()

    # If the user does not exist, create a new record
    if not user:
        user = User(
            email=user_info['email'],
            username=user_info['name'],  # Use Google-provided name
            profile_picture=user_info.get('picture')  # Store profile picture if available
        )
        db.session.add(user)
        db.session.commit()  # Save to PostgreSQL

    # Log the user in by setting session variables
    session['user_id'] = user.id
    session['email'] = user.email
    session['profile_picture'] = user.profile_picture  # Store profile picture in session

    flash('Logged in successfully via Google!', 'success')

    # Redirect user to the intended page or home
    next_url = session.pop('next', None)  
    return redirect(next_url or url_for('home'))
#Login function for google auth
@app.route('/login')
def login():
    next_url = request.args.get('next')  # Capture the next page from query params
    if next_url:
        session['next'] = next_url  # Store in session
    return google.authorize_redirect(url_for('authorize', _external=True))
#Index Page Route
@app.route("/")
def index():
    
    return render_template("index.html")
#Home Function 
@app.route("/home")
def home():
    user_id = session.get('user_id')
    # Retrieve the logged-in user's ID from the session
    

    if user_id:
        user = User.query.get(user_id)  # Query the User model to get the user
        if user:
            username = user.username# Get the username from the user object
            profile_picture=user.profile_picture
            return render_template("index.html", username=username,profile_picture=profile_picture)
    return render_template("index.html")    
#database debbuging
@app.route('/test-db')
def test_db():
    try:
        db.session.execute('SELECT 1')  # Simple test query
        return "Database is working!"
    except Exception as e:
        return f"Database connection failed: {e}"
#Signup Route
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        identifier = request.form['identifier']  # Could be email or username
        password = request.form['password']

        # Check if the user exists in the database by email or username
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user and user.check_password(password):
            # If user exists and password matches, sign in
            session['user_id'] = user.id
            session['email'] = user.email
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        else:
            # If user does not exist or password doesn't match, show error
            flash('Invalid email or username or password. Please try again or register if you are a new user.')
            return redirect(url_for('signin'))

    return render_template('signin.html')
#Registeration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Debug info
        print(f"Received POST request: Username: {username}, Email: {email}, Password: {password}")

        # Check if all fields are filled
        if not username or not email or not password:
            print("Error: Missing required fields")
            return "All fields are required."

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            print("Error: Username or email already exists.")
            return "Username or email already exists."

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            print("User successfully registered and added to the database.")
            # Redirect to the signin page after successful registration
            return redirect(url_for('signin'))
        
        except Exception as e:
            db.session.rollback()  # Rollback in case of an error
            print(f"Database Error: {e}")  # More detailed error output
            return "Registration failed. Please try again."

    return render_template('register.html')
#Profile Route
@app.route('/profile')
def profile():
    user_id = session.get('user_id')  # Get the logged-in user ID from the session
    
    if not user_id:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('signin'))
    
    # Fetch the user from the User model
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('signin'))
    
    # Fetch the user profile
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()

    return render_template('profile.html', user=user, user_profile=user_profile)
#Profile Editing Route
@app.route('/profile_edit', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')  # Ensure user is logged in and get user_id from session

    # Fetch the user's profile
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not user_profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('profile'))  # Redirect to profile if no profile exists

    if request.method == 'POST':
        # Get data from form
        user_profile.phone_number = request.form['phone_number']
        user_profile.age = request.form['age']
        user_profile.weight = request.form['weight']
        user_profile.address = request.form['address']
        user_profile.bio = request.form['bio']
        
        # Update the 'updated_at' field
        user_profile.updated_at = datetime.now()

        # Commit changes to the database
        db.session.commit()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Render the edit profile template with the current user profile data
    return render_template('profile_form.html', user_profile=user_profile)
#Profile Addition Route
@app.route('/add_profile', methods=['GET', 'POST'])
def add_profile():
    user_id = session.get('user_id')  # Get the logged-in user's ID

    if not user_id:
        flash('You need to be logged in to create a profile.', 'danger')
        return redirect(url_for('login'))  # Redirect to login if not logged in

    # Check if the user already has a profile
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()
    if user_profile:
        flash('Profile already exists. You can edit it instead.', 'warning')
        return redirect(url_for('edit_profile'))

    if request.method == 'POST':
        # Collect data from the form
        phone_number = request.form['phone_number']
        age = request.form['age']
        weight = request.form['weight']
        address = request.form['address']
        bio = request.form['bio']

        # Create a new profile record
        new_profile = UserProfile(
            user_id=user_id,
            phone_number=phone_number,
            age=age,
            weight=weight,
            address=address,
            bio=bio
        )

        # Save to the database
        db.session.add(new_profile)
        db.session.commit()

        flash('Profile created successfully!', 'success')
        return redirect(url_for('profile'))  # Redirect to the profile view

    # Render the form for adding a new profile
    return render_template('profile_form.html', user_profile=None)
#Records Page Route
@app.route('/records', methods=['GET', 'POST'])
def records():
    if 'user_id' not in session:  # Ensure user is logged in
        return render_template('records.html')
    else:
     user_id = session['user_id']  # Get the logged-in user's ID
     user = User.query.get(user_id)
     return render_template("records.html",username=user.username)
#Record ---> Daily_Record----> Add record like BP, Sugar Etc..
@app.route("/daily_record", methods=['GET', 'POST'])
def daily_record():
    if 'user_id' not in session:  # Ensure the user is logged in
        return redirect(url_for('signin'))  # Redirect to the sign-in page
    else:
     user_id = session['user_id']  # Get the logged-in user's ID
     user = User.query.get(user_id)
    
    if request.method == 'POST':
        record_type = request.form.get('record_type')
        
        # Get the current date and time
        current_date = datetime.now().date()
        current_time = datetime.now().time()

        # Prepare to save data based on the selected record type
        if record_type == 'bp':
            systolic = request.form.get('systolic')
            diastolic = request.form.get('diastolic')
            new_record = dailyrecord(
                title='Blood Pressure',
                systolic=systolic,
                diastolic=diastolic,
                fasting_sugar=None,
                bedtime_sugar=None,
                weight=None,
                height=None,
                user_id=session['user_id'],  # Associate with the logged-in user
                record_date=current_date,  # Store the current date
                record_time=current_time   # Store the current time
            )
            if int(systolic) > SYSTOLIC_PEAK or int(diastolic) > DIASTOLIC_PEAK:
                send_peak_alert_email(user.email, "Blood Pressure", f"Systolic: {systolic}, Diastolic: {diastolic}")
        elif record_type == 'sugar':
            fasting_sugar = request.form.get('fasting_sugar')
            bedtime_sugar = request.form.get('bedtime_sugar')
            new_record = dailyrecord(
                title='Sugar',
                systolic=None,  # Set to None as these fields are not used for sugar
                diastolic=None,
                fasting_sugar=fasting_sugar,
                bedtime_sugar=bedtime_sugar,
                weight=None,
                height=None,
                user_id=session['user_id'],  # Associate with the logged-in user
                record_date=current_date,  # Store the current date
                record_time=current_time   # Store the current time
            )
            if int(fasting_sugar) > FASTING_SUGAR_PEAK or int(bedtime_sugar) > BEDTIME_SUGAR_PEAK:
                send_peak_alert_email(user.email, "Sugar", f"Fasting: {fasting_sugar}, Bedtime: {bedtime_sugar}")
        elif record_type == 'weight':
            weight = request.form.get('weight')
            height = request.form.get('height')
            new_record = dailyrecord(
                title='Weight & Height',
                systolic=None,  # Set to None as these fields are not used for sugar
                diastolic=None,
                fasting_sugar=None,
                bedtime_sugar=None,
                weight=weight,
                height=height,
                user_id=session['user_id'],  # Associate with the logged-in user
                record_date=current_date,  # Store the current date
                record_time=current_time   # Store the current time
            )    
        else:
            flash('Please select a valid reading type.', 'error')
            return redirect(url_for('daily_record'))
        

        # Add the new record to the database
        db.session.add(new_record)
        db.session.commit()
        flash('Record added successfully!', 'success')
        return redirect(url_for('daily_record'))  # Redirect to another route after adding

    return render_template('bp.html', title='Add Daily Record',username=user.username)
#Dashboard Route
@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:  # Ensure user is logged in
        return render_template('dashboard.html')
    else:
     user_id = session['user_id']  # Get the logged-in user's ID
     user = User.query.get(user_id)
     return render_template("dashboard.html",username=user.username)
#Dashboard---->Daily_Dashboard---->see insights regarding stored data
@app.route("/dailydashboard", methods=['GET', 'POST'])
def dailydashboard():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return redirect(url_for('signin'))
    
    today_date = date.today()

    # Fetch all BP & Sugar records sorted by date and time (latest first)
    bp_sugar_records = dailyrecord.query.filter_by(user_id=user_id) \
        .order_by(dailyrecord.record_date.desc(), dailyrecord.record_time.desc()).all()

    total_records = len(bp_sugar_records)

    # Fetch the latest BP entry (if exists)
    latest_bp_record = dailyrecord.query.filter(
        dailyrecord.user_id == user_id,
        dailyrecord.record_date == today_date,
        dailyrecord.systolic.isnot(None),
        dailyrecord.diastolic.isnot(None)
    ).order_by(dailyrecord.record_time.desc()).first()

    # Fetch the latest Sugar entry (if exists)
    latest_sugar_record = dailyrecord.query.filter(
        dailyrecord.user_id == user_id,
        dailyrecord.record_date == today_date,
        dailyrecord.fasting_sugar.isnot(None),
        dailyrecord.bedtime_sugar.isnot(None)
    ).order_by(dailyrecord.record_time.desc()).first()

    # Assign latest BP values
    latest_systolic = latest_bp_record.systolic if latest_bp_record else 'N/A'
    latest_diastolic = latest_bp_record.diastolic if latest_bp_record else 'N/A'

    # Assign latest Sugar values
    latest_fasting_sugar = latest_sugar_record.fasting_sugar if latest_sugar_record else 'N/A'
    latest_bedtime_sugar = latest_sugar_record.bedtime_sugar if latest_sugar_record else 'N/A'

    # Calculate averages
    avg_values = db.session.query(
        func.avg(dailyrecord.systolic).label('avg_systolic'),
        func.avg(dailyrecord.diastolic).label('avg_diastolic'),
        func.avg(dailyrecord.fasting_sugar).label('avg_fasting_sugar'),
        func.avg(dailyrecord.bedtime_sugar).label('avg_bedtime_sugar')
    ).filter(dailyrecord.user_id == user_id).first()

    avg_systolic = round(avg_values.avg_systolic, 1) if avg_values and avg_values.avg_systolic is not None else 'N/A'
    avg_diastolic = round(avg_values.avg_diastolic, 1) if avg_values and avg_values.avg_diastolic is not None else 'N/A'
    avg_fasting_sugar = round(avg_values.avg_fasting_sugar, 1) if avg_values and avg_values.avg_fasting_sugar is not None else 'N/A'
    avg_bedtime_sugar = round(avg_values.avg_bedtime_sugar, 1) if avg_values and avg_values.avg_bedtime_sugar is not None else 'N/A'

    avg_sugar = (avg_fasting_sugar + avg_bedtime_sugar) / 2 if avg_fasting_sugar != 'N/A' and avg_bedtime_sugar != 'N/A' else 'N/A'

    # Prepare chart data (reverse to show oldest to newest)
    labels = []
    systolic_data = []
    diastolic_data = []
    fasting_sugar_data = []
    bedtime_sugar_data = []

    for record in reversed(bp_sugar_records):  # older first
        labels.append(record.record_date.strftime("%b %d") if record.record_date else "")
        systolic_data.append(record.systolic if record.systolic is not None else "null")
        diastolic_data.append(record.diastolic if record.diastolic is not None else "null")
        fasting_sugar_data.append(record.fasting_sugar if record.fasting_sugar is not None else "null")
        bedtime_sugar_data.append(record.bedtime_sugar if record.bedtime_sugar is not None else "null")

    # Now pass the data to the template
    return render_template(
        "daily_dashboard.html",
        username=user.username,
        latest_systolic=latest_systolic,
        latest_diastolic=latest_diastolic,
        latest_fasting_sugar=latest_fasting_sugar,
        latest_bedtime_sugar=latest_bedtime_sugar,
        avg_systolic=avg_systolic,
        avg_diastolic=avg_diastolic,
        avg_fasting_sugar=avg_fasting_sugar,
        avg_bedtime_sugar=avg_bedtime_sugar,
        avg_sugar=avg_sugar,
        total_records=total_records,
        labels=labels,
        systolic_data=systolic_data,
        diastolic_data=diastolic_data,
        fasting_sugar_data=fasting_sugar_data,
        bedtime_sugar_data=bedtime_sugar_data
    )
#Route For Blood Presure Chart
@app.route("/bpchart",methods=['GET', 'POST'])
def bpchart():
    return render_template("bp_chart.html")
# Sympai API Endpoint for Machine Learning Model
# This section defines the API endpoint for serving requests to the Sympai machine learning model.
# - Service Name: Sympai
# - Functionality: Accepts input data, preprocesses it, sends it to the model for prediction, 
#   and returns the prediction as a response. 
#Loading Databases Used in SympAi
sym_des = pd.read_csv("dataset/symtoms_df.csv")
precautions = pd.read_csv("dataset/precautions_df.csv")
workout = pd.read_csv("dataset/workout_df.csv")
description = pd.read_csv("dataset/description.csv")
medications = pd.read_csv('dataset/medications.csv')
diets = pd.read_csv("dataset/diets.csv")
#Linear Regression Model ----> Random Forest Model for prediction 
rf = pickle.load(open('model/rf.pxl','rb'))
#Defining Helper Functions
def helper(dis):
    # Description
    desc_series = description[description['Disease'] == dis]['Description']
    desc = " ".join(desc_series.tolist()) if not desc_series.empty else "No description available."

    # Precautions
    pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    # Medications
    med_series = medications[medications['Disease'] == dis]['Medication']
    med = med_series.tolist() if not med_series.empty else []

    # Diets
    diet_df = diets[diets['Disease'] == dis][['Diet_1', 'Diet_2', 'Diet_3', 'Diet_4', 'Diet_5']]
    diet_list = diet_df.values.tolist()
    die = diet_list[0] if diet_list else []

    # Workout
    wrk_series = workout[workout['disease'] == dis]['workout']
    wrkout = wrk_series.tolist() if not wrk_series.empty else []

    return desc, pre, med, die, wrkout

#labeling For Symptoms and Diseases
symptoms_dict = {'itching': 0, 'skin rash': 1, 'nodal skin eruptions': 2, 'continuous sneezing': 3, 'shivering': 4, 'chills': 5, 'joint pain': 6, 'stomach pain': 7, 'acidity': 8, 'ulcers on tongue': 9, 'muscle wasting': 10, 'vomiting': 11, 'burning micturition': 12, 'spotting urination': 13, 'fatigue': 14, 'weight gain': 15, 'anxiety': 16, 'cold hands and feets': 17, 'mood swings': 18, 'weight loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches in hroat': 22, 'irregular sugar level': 23, 'cough': 24, 'high fever': 25, 'sunken eyes': 26, 'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish skin': 32, 'dark urine': 33, 'nausea': 34, 'loss of appetite': 35, 'pain behind the eyes': 36, 'back pain': 37, 'constipation': 38, 'abdominal pain': 39, 'diarrhoea': 40, 'mild fever': 41, 'yellow urine': 42, 'yellowing of eyes': 43, 'acute liver failure': 44, 'fluid overload': 45, 'swelling of stomach': 46, 'swelled lymph nodes': 47, 'malaise': 48, 'blurred and distorted vision': 49, 'phlegm': 50, 'throat irritation': 51, 'redness of eyes': 52, 'sinus pressure': 53, 'runny nose': 54, 'congestion': 55, 'chest pain': 56, 'weakness in limbs': 57, 'fast heart rate': 58, 'pain during bowel movements': 59, 'pain in anal region': 60, 'bloody stool': 61, 'irritation in anus': 62, 'neck pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen legs': 68, 'swollen blood vessels': 69, 'puffy face and eyes': 70, 'enlarged thyroid': 71, 'brittle nails': 72, 'swollen extremeties': 73, 'excessive hunger': 74, 'extra marital contacts': 75, 'drying and tingling lips': 76, 'slurred speech': 77, 'knee pain': 78, 'hip joint pain': 79, 'muscle weakness': 80, 'stiff neck': 81, 'swelling joints': 82, 'movement stiffness': 83, 'spinning movements': 84, 'loss of balance': 85, 'unsteadiness': 86, 'weakness of one body side': 87, 'loss of smell': 88, 'bladder discomfort': 89, 'foul smell of urine': 90, 'continuous feel of urine': 91, 'passage of gases': 92, 'internal itching': 93, 'toxic look (typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle pain': 97, 'altered sensorium': 98, 'red spots over body': 99, 'belly pain': 100, 'abnormal menstruation': 101, 'dischromic  patches': 102, 'watering from eyes': 103, 'increased appetite': 104, 'polyuria': 105, 'family history': 106, 'mucoid sputum': 107, 'rusty sputum': 108, 'lack of concentration': 109, 'visual disturbances': 110, 'receiving blood transfusion': 111, 'receiving unsterile injections': 112, 'coma': 113, 'stomach bleeding': 114, 'distention of abdomen': 115, 'history of alcohol consumption': 116, 'fluid overload.1': 117, 'blood in sputum': 118, 'prominent veins on calf': 119, 'palpitations': 120, 'painful walking': 121, 'pus filled pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin peeling': 125, 'silver like dusting': 126, 'small dents in nails': 127, 'inflammatory nails': 128, 'blister': 129, 'red sore around nose': 130, 'yellow crust ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}
#Function to get symptoms from patients
def get_predicted_value(patient_symptoms):
    # Create a zero vector for the symptoms
    input_vector = np.zeros(len(symptoms_dict))
    
    # Debugging output
    print(f"Patient symptoms received: {patient_symptoms}")
    
    for item in patient_symptoms:
        # Check if the symptom is in the symptoms dictionary
        if item in symptoms_dict:
            input_vector[symptoms_dict[item]] = 1
        else:
            print(f"Warning: '{item}' is not a valid symptom.")

    # Print the input vector for debugging
    print(f"Input vector for prediction: {input_vector}")
    
    # Make the prediction
    predicted_index = rf.predict([input_vector])[0]
    
    # Return the predicted disease based on the index
    predicted_disease = diseases_list.get(predicted_index, "Unknown Disease")
    print(f"Predicted disease: {predicted_disease}")  # Debugging output
    
    return predicted_disease
#Route for showing the prediction results 
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        symptoms = request.form.get('custom_symptoms')

        # Check if symptoms are provided and not just whitespace
        if symptoms and symptoms.strip():
            print(f"Received symptoms: {symptoms}")  # Debugging output

            # Process and clean the input symptoms (split by comma and strip spaces)
            user_symptoms = [s.strip().lower() for s in symptoms.split(',') if s.strip()]
            print(f"Processed symptoms: {user_symptoms}")  # Debugging output

            # Check if all user symptoms are valid
            invalid_symptoms = [s for s in user_symptoms if s not in symptoms_dict]
            print(f"Invalid symptoms: {invalid_symptoms}")  # Debugging output
            
            if invalid_symptoms:
                # Return an error message for invalid symptoms
                message = f"Some symptoms you entered are invalid or misspelled: {', '.join(invalid_symptoms)}. Please check and try again."
                return render_template('meds_rec.html', message=message, symptoms=symptoms)
            
            # Predict the disease and get additional information
            predicted_disease = get_predicted_value(user_symptoms)
            dis_des, precautions, medications, rec_diet, workout = helper(predicted_disease)
            print(precautions)
            # Prepare list of precautions
            my_precautions = [precaution for precaution in precautions[0]]
            
            
            # Render the result template with disease information
            return render_template('meds_rec.html', 
                                   predicted_disease=predicted_disease, 
                                   dis_des=dis_des,
                                   my_precautions=my_precautions, 
                                   medications=medications, 
                                   my_diet=rec_diet,
                                   workout=workout)
        else:
            message = "Please enter symptoms."
            return render_template('meds_rec.html', message=message,symptoms=symptoms)
    
    # Render the form template if the request method is not POST
    return render_template('meds_rec.html')
#Route For Charts
@app.route("/charts", methods=['GET', 'POST'])
def charts():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        return redirect(url_for('signin'))
    
    today_date = date.today()

    # Fetch BP & Sugar records for the user
    bp_sugar_records = dailyrecord.query.filter_by(user_id=user_id) \
        .order_by(dailyrecord.record_date.desc(), dailyrecord.record_time.desc()).all()

    # Prepare data for the charts
    labels = []
    systolic_data = []
    diastolic_data = []
    fasting_sugar_data = []
    bedtime_sugar_data = []

    for record in reversed(bp_sugar_records):  # reverse to show from oldest to newest
        labels.append(record.record_date.strftime("%b %d") if record.record_date else "")
        systolic_data.append(record.systolic if record.systolic is not None else "null")
        diastolic_data.append(record.diastolic if record.diastolic is not None else "null")
        fasting_sugar_data.append(record.fasting_sugar if record.fasting_sugar is not None else "null")
        bedtime_sugar_data.append(record.bedtime_sugar if record.bedtime_sugar is not None else "null")

    return render_template("dashboard_charts.html", 
                           username=user.username,
                           labels=labels,
                           systolic_data=systolic_data,
                           diastolic_data=diastolic_data,
                           fasting_sugar_data=fasting_sugar_data,
                           bedtime_sugar_data=bedtime_sugar_data)
#Now we will create CBC Testing Feature
import joblib
rf_model =joblib.load("model/rf_model.pkl")

def extract_lab_report_data(pdf_path):
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    extracted_data = {}

    # Personal & Referral Info
    if "Age :" in full_text:
        extracted_data["Age"] = full_text.split("Age :")[1].split("\n")[0].strip()
    if "Sex :" in full_text:
        extracted_data["Sex"] = full_text.split("Sex :")[1].split("\n")[0].strip()
    if "PID :" in full_text:
        extracted_data["PID"] = full_text.split("PID :")[1].split("\n")[0].strip()
    if "Ref. By:" in full_text:
        extracted_data["Referred By"] = full_text.split("Ref. By:")[1].split("\n")[0].strip()

    # Test Values
    fields = {
        "Hemoglobin (Hb)": "Hemoglobin",
        "Total RBC count": "Total RBC count",
        "Total WBC count": "Total WBC count",
        "Neutrophils": "Neutrophils",
        "Lymphocytes": "Lymphocytes",
        "Eosinophils": "Eosinophils",
        "Monocytes": "Monocytes",
        "Basophils": "Basophils",
        "Platelet Count": "Platelet Count",
        "Packed Cell Volume (PCV)": "PCV",
        "Mean Corpuscular Volume (MCV)": "MCV",
        "MCH ": "MCH",
        "MCHC": "MCHC",
        "RDW": "RDW"
    }

    for key, label in fields.items():
        if key in full_text:
            try:
                extracted_data[label] = full_text.split(key)[1].split()[0].strip()
            except IndexError:
                extracted_data[label] = "Not found"

    return extracted_data

diseases_list_cbc = {
    0: "Allergic Reaction or Inflammation, Anemia",
    1: "Allergic Reaction or Inflammation, Iron Deficiency",
    2: "Allergic Reaction or Inflammation",
    3: "Allergy or Parasitic Infection, Allergic Reaction or Inflammation",
    4: "Allergy or Parasitic Infection, Anemia or Fluid Overload",
    5: "Allergy or Parasitic Infection, Anemia",
    6: "Allergy or Parasitic Infection, Dehydration or Polycythemia",
    7: "Allergy or Parasitic Infection, Folate Deficiency",
    8: "Allergy or Parasitic Infection, Iron Deficiency",
    9: "Allergy or Parasitic Infection, Polycythemia (High RBC Production)",
    10: "Allergy or Parasitic Infection, Thrombocytopenia",
    11: "Allergy or Parasitic Infection, Thrombocytosis (Inflammation, Iron Deficiency)",
    12: "Allergy or Parasitic Infection, Vitamin B12 Deficiency",
    13: "Allergy or Parasitic Infection",
    14: "Anemia or Fluid Overload, Folate Deficiency",
    15: "Anemia or Fluid Overload, Iron Deficiency",
    16: "Anemia or Fluid Overload, Thrombocytopenia",
    17: "Anemia or Fluid Overload, Thrombocytosis (Inflammation, Iron Deficiency)",
    18: "Anemia or Fluid Overload, Vitamin B12 Deficiency",
    19: "Anemia or Fluid Overload",
    20: "Anemia, Anemia or Fluid Overload",
    21: "Anemia, Folate Deficiency",
    22: "Anemia, Iron Deficiency",
    23: "Anemia, Thrombocytopenia",
    24: "Anemia, Thrombocytosis (Inflammation, Iron Deficiency)",
    25: "Anemia, Vitamin B12 Deficiency",
    26: "Anemia",
    27: "Bacterial Infection or Stress, Allergic Reaction or Inflammation",
    28: "Bacterial Infection or Stress, Allergy or Parasitic Infection",
    29: "Bacterial Infection or Stress, Anemia or Fluid Overload",
    30: "Bacterial Infection or Stress, Anemia",
    31: "Bacterial Infection or Stress, Chronic Inflammation or Infection Recovery",
    32: "Bacterial Infection or Stress, Dehydration or Polycythemia",
    33: "Bacterial Infection or Stress, Folate Deficiency",
    34: "Bacterial Infection or Stress, Iron Deficiency",
    35: "Bacterial Infection or Stress, Polycythemia (High RBC Production)",
    36: "Bacterial Infection or Stress, Thrombocytopenia",
    37: "Bacterial Infection or Stress, Thrombocytosis (Inflammation, Iron Deficiency)",
    38: "Bacterial Infection or Stress, Viral Infection",
    39: "Bacterial Infection or Stress, Vitamin B12 Deficiency",
    40: "Bacterial Infection or Stress",
    41: "Chronic Inflammation or Infection Recovery, Allergic Reaction or Inflammation",
    42: "Chronic Inflammation or Infection Recovery, Allergy or Parasitic Infection",
    43: "Chronic Inflammation or Infection Recovery, Anemia or Fluid Overload",
    44: "Chronic Inflammation or Infection Recovery, Anemia",
    45: "Chronic Inflammation or Infection Recovery, Dehydration or Polycythemia",
    46: "Chronic Inflammation or Infection Recovery, Folate Deficiency",
    47: "Chronic Inflammation or Infection Recovery, Iron Deficiency",
    48: "Chronic Inflammation or Infection Recovery, Polycythemia (High RBC Production)",
    49: "Chronic Inflammation or Infection Recovery, Thrombocytopenia",
    50: "Chronic Inflammation or Infection Recovery, Thrombocytosis (Inflammation, Iron Deficiency)",
    51: "Chronic Inflammation or Infection Recovery, Vitamin B12 Deficiency",
    52: "Chronic Inflammation or Infection Recovery",
    53: "Dehydration or Polycythemia, Folate Deficiency",
    54: "Dehydration or Polycythemia, Iron Deficiency",
    55: "Dehydration or Polycythemia, Thrombocytopenia",
    56: "Dehydration or Polycythemia, Thrombocytosis (Inflammation, Iron Deficiency)",
    57: "Dehydration or Polycythemia, Vitamin B12 Deficiency",
    58: "Dehydration or Polycythemia",
    59: "Folate Deficiency",
    60: "Infection/Inflammation, Allergy or Parasitic Infection",
    61: "Infection/Inflammation, Bacterial Infection or Stress",
    62: "Infection/Inflammation, Chronic Inflammation or Infection Recovery",
    63: "Infection/Inflammation, Possible Leukemia",
    64: "Infection/Inflammation, Viral Infection",
    65: "Iron Deficiency, Folate Deficiency",
    66: "Iron Deficiency, Vitamin B12 Deficiency",
    67: "Iron Deficiency",
    68: "Polycythemia (High RBC Production), Dehydration or Polycythemia",
    69: "Polycythemia (High RBC Production), Iron Deficiency",
    70: "Polycythemia (High RBC Production), Thrombocytopenia",
    71: "Polycythemia (High RBC Production)",
    72: "Thrombocytopenia, Folate Deficiency",
    73: "Thrombocytopenia, Iron Deficiency",
    74: "Thrombocytopenia, Vitamin B12 Deficiency",
    75: "Thrombocytopenia",
    76: "Thrombocytosis (Inflammation, Iron Deficiency), Folate Deficiency",
    77: "Thrombocytosis (Inflammation, Iron Deficiency), Iron Deficiency",
    78: "Thrombocytosis (Inflammation, Iron Deficiency), Vitamin B12 Deficiency",
    79: "Thrombocytosis (Inflammation, Iron Deficiency)",
    80: "Viral Infection, Allergy or Parasitic Infection",
    81: "Viral Infection, Anemia or Fluid Overload",
    82: "Viral Infection, Anemia",
    83: "Viral Infection, Chronic Inflammation or Infection Recovery",
    84: "Viral Infection, Dehydration or Polycythemia",
    85: "Viral Infection, Folate Deficiency",
    86: "Viral Infection, Iron Deficiency",
    87: "Viral Infection, Polycythemia (High RBC Production)",
    88: "Viral Infection, Thrombocytopenia",
    89: "Viral Infection, Thrombocytosis (Inflammation, Iron Deficiency)",
    90: "Viral Infection, Vitamin B12 Deficiency",
    91: "Viral Infection",
    92: "Vitamin B12 Deficiency, Folate Deficiency",
    93: "Vitamin B12 Deficiency",
    94: "No Clear Diagnosis"
}


def lab_report_predict_disease(data):
    feature_order = [
        "GENDER", "WBC", "NE#", "LY#", "MO#", "EO#", "BA#", 
        "RBC", "HGB", "MCV", "MCH", "MCHC", "PLT"
    ]

    def to_float(value):
        try:
            return float(value.replace(",", ""))
        except:
            return 0.0

    def gender_to_numeric(gender):
        if not gender:
            return 0
        gender = gender.lower()
        if "male" in gender:
            return 1
        elif "female" in gender:
            return 0
        return 0

    # Map your extracted data keys to the model's expected keys
    mapping = {
        "GENDER": gender_to_numeric(data.get("Sex", "")),
        "WBC": data.get("Total WBC count", "0"),
        "NE#": data.get("Neutrophils", "0"),
        "LY#": data.get("Lymphocytes", "0"),
        "MO#": data.get("Monocytes", "0"),
        "EO#": data.get("Eosinophils", "0"),
        "BA#": data.get("Basophils", "0"),
        "RBC": data.get("Total RBC count", "0"),
        "HGB": data.get("Hemoglobin", "0"),
        "MCV": data.get("MCV", "0"),
        "MCH": data.get("MCH", "0"),
        "MCHC": data.get("MCHC", "0"),
        "PLT": data.get("Platelet Count", "0")
    }

    # Build input vector in correct order
    input_vector = []
    for feat in feature_order:
        if feat == "GENDER":
            input_vector.append(mapping["GENDER"])
        else:
            input_vector.append(to_float(mapping[feat]))

    input_array = np.array(input_vector).reshape(1, -1)
    prediction = rf_model.predict(input_array)

    # Extract prediction index and disease name
    predicted_index = prediction[0]
    predicted_disease = diseases_list_cbc.get(predicted_index, "Unknown Disease")
    print(predicted_index, predicted_disease)

    return predicted_index, predicted_disease




@app.route("/fileupload", methods=["GET", "POST"])
def fileupload():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = f"uploads/{file.filename}"
            file.save(file_path)

            extracted_data = extract_lab_report_data(file_path)
            predicted_disease = lab_report_predict_disease(extracted_data)

            return render_template("result.html", data=extracted_data, prediction=predicted_disease)
    return render_template("cbc_file_upload.html")


# Route for displaying extracted data
@app.route("/result")
def result():
    return render_template("result.html")





















#Route for Logout 
@app.route('/logout')
def logout():
    session.clear()  # This clears all session variables
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))
#For execution of the application/Script
if __name__ == "__main__":
    app.run(debug=True)