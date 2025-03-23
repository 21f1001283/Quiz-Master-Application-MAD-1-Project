from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from app import app
from models import db, User, Score, Subject, Chapter, Quiz, Question
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# decorator for auth_required
def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please, login to continue!')
            return redirect(url_for('login'))
    return inner

# decorator for admin_required
def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please, login to continue!')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.is_admin:
            flash('You are not authorized to view this page!')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return inner


@app.route('/')
@auth_required
def index():
    user = User.query.get(session['user_id'])
    if user.is_admin:
        return redirect(url_for('admin'))
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Please, fill out all fields!')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Username does not exist!')
        return redirect(url_for('login'))
    
    if not check_password_hash(user.passhash, password):
        flash('Incorrect password!')
        return redirect(url_for('login'))
    
    session['user_id'] = user.id
    flash('Login successful!')
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    name = request.form.get('name')
    dob = request.form.get('dob')
    if dob:
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            dob = None  # Handle invalid formats
    else:
        dob = None  # Handle empty input
    
    if dob > datetime.now().date():
        flash('Invalid date of birth!')
        return redirect(url_for('register'))
    
    qualification = request.form.get('qualification')
    if not qualification:
        qualification = None

    if not username or not password or not confirm_password or not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('register'))
    
    if password != confirm_password:
        flash('Passwords do not match!')
        return redirect(url_for('register'))
    
    user = User.query.filter_by(username=username).first()
    if user:
        flash('Username already exists!')
        return redirect(url_for('register'))
    
    password_hash = generate_password_hash(password)
    new_user = User(username=username, passhash=password_hash, name=name, dob=dob, qualification=qualification)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

@app.route('/profile')
@auth_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile', methods=['POST'])
@auth_required
def profile_post():
    username = request.form.get('username')
    cpassword = request.form.get('cpassword')
    password = request.form.get('password')
    name = request.form.get('name')
    if not username or not cpassword or not password or not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('profile'))

    user = User.query.get(session['user_id'])
    if not check_password_hash(user.passhash, cpassword):
        flash('Incorrect current password!')
        return redirect(url_for('profile'))
    if username != user.username:
        new_username = User.query.filter_by(username=username).first()
        if new_username:
            flash('Username already exists!')
            return redirect(url_for('profile'))
    
    new_password_hash = generate_password_hash(password)
    user.username = username
    user.passhash = new_password_hash
    user.name = name
    db.session.commit()
    flash('Profile updated successfully!')
    return redirect(url_for('profile'))


@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))

# ROUTES FOR ADMIN----------------

@app.route('/admin')
@admin_required
def admin():
    subjects = Subject.query.all()
    return render_template('admin.html', subjects=subjects)

# Routes for subjects to be added by admin
@app.route('/subject/add')
@admin_required
def add_subject():
    return render_template('subject/add.html')

@app.route('/subject/add', methods=['POST'])
@admin_required
def add_subject_post():
    name = request.form.get('name')
    description = request.form.get('description')
    if not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('add_subject'))
    
    subject = Subject(name=name, description=description)
    db.session.add(subject)
    db.session.commit()
    flash('Subject added successfully!')
    return redirect(url_for('admin'))

@app.route('/subject/<int:id>/')
@admin_required
def view_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    return render_template('subject/view.html', subject=subject)

@app.route('/subject/<int:id>/edit')
@admin_required
def edit_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    return render_template('subject/edit.html', subject=subject)

@app.route('/subject/<int:id>/edit', methods=['POST'])
@admin_required
def edit_subject_post(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    name = request.form.get('name')
    description = request.form.get('description')
    if not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('edit_subject', id=id))
    
    subject.name = name
    subject.description = description
    db.session.commit()
    flash('Subject updated successfully!')
    return redirect(url_for('admin'))


@app.route('/subject/<int:id>/delete')
@admin_required
def delete_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    return render_template('subject/delete.html', subject=subject)

@app.route('/subject/<int:id>/delete', methods=['POST'])
@admin_required
def delete_subject_post(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!')
    return redirect(url_for('admin'))


# Routes for chapters to be added by admin

@app.route('/chapter/add/<int:subject_id>')
@admin_required
def add_chapter(subject_id):
    subjects = Subject.query.all()
    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    return render_template('chapter/add.html', subject=subject, subjects=subjects)

@app.route('/chapter/add/', methods=['POST'])
@admin_required
def add_chapter_post():
    name = request.form.get('name')
    description = request.form.get('description')
    subject_id = request.form.get('subject_id')

    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject does not exist!')
        return redirect(url_for('admin'))
    if not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('add_chapter', subject_id=subject_id))
    
    chapter = Chapter(name=name, description=description, subject_id=subject_id)
    db.session.add(chapter)
    db.session.commit()
    flash('Chapter added successfully!')
    return redirect(url_for('view_subject', id=subject_id))

@app.route('/chapter/<int:id>/edit')
@admin_required
def edit_chapter(id):
    subjects = Subject.query.all()
    chapter = Chapter.query.get(id)
    return render_template('chapter/edit.html', chapter=chapter, subjects=subjects)

@app.route('/chapter/<int:id>/edit', methods=['POST'])
@admin_required
def edit_chapter_post(id):
    name = request.form.get('name')
    description = request.form.get('description')
    subject_id = request.form.get('subject_id')

    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist!')
        return redirect(url_for('admin'))
    if not name:
        flash('Please, fill out all fields!')
        return redirect(url_for('edit_chapter', id=id))
    
    chapter.name = name
    chapter.description = description
    chapter.subject_id = subject_id
    db.session.commit()
    flash('Chapter updated successfully!')
    return redirect(url_for('view_subject', id=subject_id))

@app.route('/chapter/<int:id>/delete')
@admin_required
def delete_chapter(id):
    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist!')
        return redirect(url_for('admin'))
    return render_template('chapter/delete.html', chapter=chapter)

@app.route('/chapter/<int:id>/delete', methods=['POST'])
@admin_required
def delete_chapter_post(id):
    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist!')
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted successfully!')
    return redirect(url_for('view_subject', id=chapter.subject_id))


    
