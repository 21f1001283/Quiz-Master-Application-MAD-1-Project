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
        if 'user_id' not in session:
            flash('Please, login to continue!')
            return redirect(url_for('login'))
            
        user = User.query.get(session['user_id'])
        if user is None:  # Check if user is found
            # flash('User not found!')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return inner

# decorator for admin_required
def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please, login to continue!')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user is None:  # Check if user is found
            # flash('User not found!')
            return redirect(url_for('login'))
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

# Routes for QUIZ MANAGEMENT Dashboard--------------
@app.route('/quiz')
@admin_required
def quiz():
    quizzes = Quiz.query.all()
    return render_template('quiz.html', quizzes=quizzes)

# Routes for quizzes to be added by admin
@app.route('/quiz/add')
@admin_required
def add_quiz():
    chapters = Chapter.query.all()
    return render_template('quiz/add.html', chapters=chapters)

@app.route('/quiz/add', methods=['POST'])
@admin_required
def add_quiz_post():
    remarks = request.form.get('remarks')
    date_of_quiz = request.form.get('date_of_quiz')
    time_duration = request.form.get('time_duration')
    chapter_id = request.form.get('chapter_id')

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        flash('Chapter does not exist!')
        return redirect(url_for('quiz'))
    if not date_of_quiz or not time_duration:
        flash('Please, fill out all fields!')
        return redirect(url_for('add_quiz',chapter_id=chapter_id)) 
    
    date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
    # Split into hours and minutes and convert to total minutes
    hours, minutes = map(int, time_duration.split(':'))
    total_minutes = hours * 60 + minutes  # Convert to total minutes
    # Create timedelta object
    duration = timedelta(minutes=total_minutes)
    
    if date_of_quiz < datetime.now().date():
        flash('Invalid date for quiz!')
        return redirect(url_for('add_quiz'))

    quiz = Quiz(remarks=remarks, date_of_quiz=date_of_quiz, time_duration=duration, chapter_id=chapter_id)
    db.session.add(quiz)
    db.session.commit()
    flash('Quiz added successfully!')
    return redirect(url_for('quiz'))


@app.route('/quiz/<int:id>/')
@admin_required
def view_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('admin'))
    return render_template('quiz/view.html', quiz=quiz)

@app.route('/quiz/<int:id>/edit')
@admin_required
def edit_quiz(id):
    chapters = Chapter.query.all()
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    return render_template('quiz/edit.html', quiz=quiz, chapters=chapters)

@app.route('/quiz/<int:id>/edit', methods=['POST'])
@admin_required
def edit_quiz_post(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    remarks = request.form.get('remarks')
    date_of_quiz = request.form.get('date_of_quiz')
    time_duration = request.form.get('time_duration')
    chapter_id = request.form.get('chapter_id')

    if not date_of_quiz or not time_duration:
        flash('Please, fill out all fields!')
        return redirect(url_for('edit_quiz', id=id))
    
    date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
    # Split into hours and minutes and convert to total minutes
    hours, minutes = map(int, time_duration.split(':'))
    total_minutes = hours * 60 + minutes  # Convert to total minutes
    # Create timedelta object
    duration = timedelta(minutes=total_minutes)
    
    if date_of_quiz < datetime.now().date():
        flash('Invalid date for quiz!')
        return redirect(url_for('edit_quiz', id=id))
    
    quiz.remarks = remarks
    quiz.date_of_quiz = date_of_quiz
    quiz.time_duration = duration
    quiz.chapter_id = chapter_id
    db.session.commit()
    flash('Quiz updated successfully!')
    return redirect(url_for('quiz'))


@app.route('/quiz/<int:id>/delete')
@admin_required
def delete_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    return render_template('quiz/delete.html', quiz=quiz)

@app.route('/quiz/<int:id>/delete', methods=['POST'])
@admin_required
def delete_quiz_post(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully!')
    return redirect(url_for('quiz'))

# Routes for Questions to be added to the Quizzes------------------
@app.route('/question/add/<int:quiz_id>')
@admin_required
def add_question(quiz_id):
    quizzes = Quiz.query.all()
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    return render_template('question/add.html', quiz=quiz, quizzes=quizzes)

@app.route('/quiz/add/', methods=['POST'])
@admin_required
def add_question_post():
    question_title = request.form.get('question_title')
    question_statement = request.form.get('question_statement')
    option1 = request.form.get('option1')
    option2 = request.form.get('option2')
    option3 = request.form.get('option3')
    option4 = request.form.get('option4')
    correct_option = request.form.get('correct_option')
    quiz_id = request.form.get('quiz_id')

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('quiz'))
    if not question_title or not question_statement or not option1 or not option2 or not option3 or not option4 or not correct_option:
        flash('Please, fill out all fields!')
        return redirect(url_for('add_question', quiz_id=quiz_id))
    
    question = Question(question_title=question_title, question_statement=question_statement, option1=option1, option2=option2, option3=option3, option4=option4, correct_option=correct_option, quiz_id=quiz_id)
    db.session.add(question)
    db.session.commit()
    flash('Question added successfully!')
    return redirect(url_for('view_quiz', id=quiz_id))

@app.route('/question/<int:id>/edit')
@admin_required
def edit_question(id):
    quizzes = Quiz.query.all()
    question = Question.query.get(id)
    return render_template('question/edit.html', question=question, quizzes=quizzes)

@app.route('/question/<int:id>/edit', methods=['POST'])
@admin_required
def edit_question_post(id):
    question_title = request.form.get('question_title')
    question_statement = request.form.get('question_statement')
    option1 = request.form.get('option1')
    option2 = request.form.get('option2')
    option3 = request.form.get('option3')
    option4 = request.form.get('option4')
    correct_option = request.form.get('correct_option')
    quiz_id = request.form.get('quiz_id')

    question = Question.query.get(id)
    if not question:
        flash('Question does not exist!')
        return redirect(url_for('quiz'))
    if not question_title or not question_statement or not option1 or not option2 or not option3 or not option4 or not correct_option:
        flash('Please, fill out all fields!')
        return redirect(url_for('edit_question', id=id))
    
    question.question_title = question_title
    question.question_statement = question_statement
    question.option1 = option1
    question.option2 = option2
    question.option3 = option3
    question.option4 = option4
    question.correct_option = correct_option
    question.quiz_id = quiz_id
    db.session.commit()
    flash('Question updated successfully!')
    return redirect(url_for('view_quiz', id=quiz_id))

@app.route('/question/<int:id>/delete')
@admin_required
def delete_question(id):
    question = Question.query.get(id)
    if not question:
        flash('Question does not exist!')
        return redirect(url_for('Quiz'))
    return render_template('question/delete.html', question=question)

@app.route('/question/<int:id>/delete', methods=['POST'])
@admin_required
def delete_question_post(id):
    question = Question.query.get(id)
    if not question:
        flash('Question does not exist!')
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!')
    return redirect(url_for('view_quiz', id=question.quiz_id))




    
