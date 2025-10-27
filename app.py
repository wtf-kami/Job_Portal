from flask import Flask, render_template,jsonify, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy import or_ , cast, String

app = Flask(__name__)
app.secret_key = '546bba35450ab4c5183fed98d3b332ae'
app.config['SQLALCHEMY_DATABASE_URI'] ='postgresql://postgres:[YOUR_PASSWORD]@db.ubxsdebwtptlctecfivd.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    __tablename__ = 'user_db'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable = True)
    last_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Skillset(db.Model):
    __tablename__='skillset'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey('user_db.id'),nullable = False)
    job_role =db.Column(db.String(100),nullable = False)
    skills = db.Column(db.String(255),nullable=False)

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    skills_required = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    salary_range = db.Column(db.String(50), nullable=True)
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)
    apply_link = db.Column(db.String(255), nullable=True)
    

    def __repr__(self):
        return f'<Job{self.title}> at {self.company}>'
    
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        first_name = data.get('firstName')
        middle_name = data.get('middleName', '')
        last_name = data.get('lastName')
        dob = data.get('dob')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirmPassword', password)

        # Validation
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            username=username,
            email=email,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'Signup successful!', 'user': {'username': username, 'email': email}}), 201

    return render_template('signup.html')


from flask import jsonify

@app.route('/signin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = user.username
            
            #check if user has user onboarding data
            skillset_exists =  Skillset.query.filter_by(user_id=user.id).first()

            if not skillset_exists:
                return jsonify({
                    'message': 'Welcome! Please complete onboarding.',
                    'redirect': url_for('onboarding')
                }),200
            else:
                return jsonify({
                    'message': f'Welcome back, {user.first_name}!',
                    'redirect': url_for('dashboard')

                }),200
            
        else:
            return jsonify({'error': 'Invalid username or password!'}), 401

    return render_template('signin.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in first.','warning')
        return redirect('/login')
    
    user = User.query.filter_by(username =  session['user']).first()

    skillset =  Skillset.query.filter_by(user_id=user.id).first()

    if not skillset:
        flash('please complete onboarding first.','info')
        return redirect(url_for('onboarding'))
    
    #jobs = Job.query.filter(Job.role.ilike(f"%{skillset.job_role}%")).all()

    return render_template('dashboard.html',user=user)

@app.route('/api/jobs', methods=['GET', 'POST'])
def jobs_api():
    if request.method == 'POST':
        data = request.get_json()

        title = data.get('title')
        company = data.get('company')
        location = data.get('location')
        role = data.get('role')
        skills_required = data.get('skills_required')
        description = data.get('description')
        salary_range = data.get('salary_range')
        posted_on = data.get('posted_on')
        apply_link = data.get('apply_link')

        # --- Validation ---
        if not title or not company or not location or not role:
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            job = Job(
                title=title,
                company=company,
                location=location,
                role=role,
                skills_required=skills_required,
                description=description,
                salary_range=salary_range,
                apply_link=apply_link
            )

            # Optional: If a date string is provided
            if posted_on:
                job.posted_on = datetime.fromisoformat(posted_on.replace("Z", ""))

            db.session.add(job)
            db.session.commit()

            return jsonify({'message': 'Job posted successfully!', 'id': job.id}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # --- GET ---
    role_query = request.args.get('roles', '')  # comma-separated roles
    role_list = [r.strip() for r in role_query.split(',') if r.strip()]

    if role_list:
        filters = [Job.role.ilike(f"%{r}%") for r in role_list]
        jobs = Job.query.filter(or_(*filters)).all()
    else:
        jobs = Job.query.all()

    jobs_data = [
        {
            'id': j.id,
            'title': j.title,
            'company': j.company,
            'location': j.location,
            'role': j.role,
            'skills_required': j.skills_required,
            'description': j.description,
            'salary_range': j.salary_range,
            'apply_link': j.apply_link,
            'posted_on': j.posted_on.isoformat() if j.posted_on else None
        } for j in jobs
    ]
    return jsonify(jobs_data)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    if 'user' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['user']).first()

    if request.method == 'POST':
        job_role = request.form.get('job_role')
        selected_skills = request.form.getlist('skills')  # multiple checkboxes
        skills_str = ', '.join(selected_skills)

        # Save to database
        new_skillset = Skillset(user_id=user.id, job_role=job_role, skills=skills_str)
        db.session.add(new_skillset)
        db.session.commit()

        flash('Onboarding complete! Skills added successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('onboarding.html', user=user)

@app.route('/api/onboarding', methods=['POST'])
def save_onboarding():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()  # <- parse JSON sent from JS
    skills = data.get('skills', [])
    roles = data.get('roles', [])

    if not skills or not roles:
        return jsonify({'error': 'Skills and roles required'}), 400

    user = User.query.filter_by(username=session['user']).first()

    new_skillset = Skillset(
        user_id=user.id,
        job_role=', '.join(roles),
        skills=', '.join(skills)
    )

    db.session.add(new_skillset)
    db.session.commit()

    return jsonify({'message': 'Onboarding saved!'}), 201

@app.route('/jobposting', methods=['GET', 'POST'])
def job_posting():
    return render_template('JobPosting.html')
# ------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
