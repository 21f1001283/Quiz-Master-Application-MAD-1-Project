from flask import Flask, render_template, request, redirect, url_for, flash, session, json
from datetime import datetime, timedelta
from app import app
from models import db, User, Score, Subject, Chapter, Quiz, Question
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy.sql import func

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
    
    subjects = Subject.query.all()
    now = datetime.now()
    #now= datetime(2025,4,2)
    # Query quizzes that are still valid (future or today)
    quizzes = Quiz.query.filter(Quiz.date_of_quiz >= now.date()).all()
    return render_template('index.html', subjects=subjects, quizzes=quizzes)

#------------------COMMON ROUTES FOR BOTH USER & ADMIN------------------
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
    session['is_admin'] = user.is_admin
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

# ----------ROUTES FOR ADMIN----------------

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

#----Route for Admin to view User Details----
@app.route('/admin/users')
@admin_required
def admin_view_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# Route for Admin to view Summary---
@app.route('/admin/summary')
@admin_required
def admin_summary():
    # Fetch subject-wise user attempts
    subject_attempts = (
        db.session.query(Subject.name, func.count(Score.id).label('attempt_count'))
        .join(Chapter, Chapter.subject_id == Subject.id)
        .join(Quiz, Quiz.chapter_id == Chapter.id)
        .join(Score, Score.quiz_id == Quiz.id)
        .group_by(Subject.name)
        .all()
    )

    # Fetch subject-wise top scores
    subject_top_scores = (
        db.session.query(Subject.name, func.max(Score.score).label('top_score'))
        .join(Chapter, Chapter.subject_id == Subject.id)
        .join(Quiz, Quiz.chapter_id == Chapter.id)
        .join(Score, Score.quiz_id == Quiz.id)
        .group_by(Subject.name)
        .all()
    )

    return render_template(
        'admin/summary.html',
        subject_attempts=subject_attempts,
        subject_top_scores=subject_top_scores
    )


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


#-------USER ROUTES---------
@app.route('/user_view_quiz/<int:id>/')
@auth_required
def user_view_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('index'))
    questions = quiz.questions
    return render_template('user/view_quiz.html', quiz=quiz)

@app.route('/user_view_quiz/close')
@auth_required
def user_close_quiz_details():
        return redirect(url_for('index'))

@app.route('/start_quiz/<int:id>', methods=['GET', 'POST'])
@auth_required
def start_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('index'))
    questions = quiz.questions
    current_question = int(request.args.get('current_question', 0))
    if 'remaining_time' not in session:
        session['remaining_time'] = quiz.time_duration.total_seconds()

    if request.method == 'POST':
        selected_answer = request.form.get('ans')
        if not selected_answer:
            selected_answer = ""
        # Store the selected answer in the session
        if 'answers' not in session:
            session['answers'] = {}
        answers = session['answers']  
        answers[str(questions[current_question].id)] = selected_answer
        session['answers'] = answers 

        session['remaining_time'] = int(request.form.get('remaining_time', session['remaining_time']))

        
        return redirect(url_for('start_quiz', id=id, current_question=current_question + 1))

        
    return render_template('user/start_quiz.html',
                           quiz=quiz, questions=questions,
                           current_question=current_question,
                           remaining_time=session['remaining_time'])


@app.route('/submit_quiz/<int:id>', methods=['POST'])
@auth_required
def submit_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash('Quiz does not exist!')
        return redirect(url_for('index'))
    
    score = 0  # Initialize score
    #----score for last question---------
    selected_last_answer = request.form.get('ans')
    length_of_questions = len(quiz.questions)
    #if selected_last_answer and selected_last_answer == quiz.questions[length_of_questions-1].correct_option:
        #score += 1
    
    questions = quiz.questions
    answers = session.get('answers', {}) 
    answers[str(quiz.questions[length_of_questions-1].id)]= selected_last_answer
    print(answers)

    for question in questions:
        selected_answer = answers.get(str(question.id))  # Use str(question.id) to match the key format
        if selected_answer and selected_answer == question.correct_option:
            score += 1 

    # Convert the user_answers dictionary to a JSON string
    #user_answers_json = json.dumps(answers)
    score_record = Score(user_id=session['user_id'],
                         quiz_id=quiz.id, score=score,
                         date_attempted=datetime.now().date())
    
    db.session.add(score_record)
    db.session.commit()

    session.pop('answers', None)
    session.pop('remaining_time', None)

    flash(f'Quiz submitted successfully! Your score: {score}/{len(questions)}')
    return redirect(url_for('index'))

@app.route('/score')
@auth_required
def score():
    user = User.query.get(session['user_id'])
    scores = Score.query.filter_by(user_id=user.id).all()
    for score in scores:
    # Count how many times the user has attempted this quiz before this score
        attempt_number = Score.query.filter(
            Score.user_id == user.id,
            Score.quiz_id == score.quiz_id,
            (Score.date_attempted < score.date_attempted) |  # Earlier dates
            ((Score.date_attempted == score.date_attempted) & (Score.id <= score.id))  # Same date, earlier or same ID
        ).count()
        score.attempt_number = attempt_number 
    return render_template('user/score.html', scores=scores)

@app.route('/view_quiz_answers/<int:id>')
@auth_required
def view_quiz_answers(id):
    score = Score.query.get(id)
    quiz = Quiz.query.get(score.quiz_id)
    questions = quiz.questions
    return render_template('user/quiz_ans.html', questions=questions)

@app.route('/user/summary')
@auth_required
def user_summary():
    user_id = session['user_id']

    # Fetch subject-wise number of quizzes attempted by the user
    subject_attempts = (
        db.session.query(Subject.name, func.count(Score.id).label('attempt_count'))
        .join(Chapter, Chapter.subject_id == Subject.id)
        .join(Quiz, Quiz.chapter_id == Chapter.id)
        .join(Score, Score.quiz_id == Quiz.id)
        .filter(Score.user_id == user_id)
        .group_by(Subject.name)
        .all()
    )

    # Fetch month-wise number of quizzes attempted by the user
    month_attempts = (
        db.session.query(
            func.strftime('%Y-%m', Score.date_attempted).label('month'),
            func.count(Score.id).label('attempt_count')
        )
        .filter(Score.user_id == user_id)
        .group_by(func.strftime('%Y-%m', Score.date_attempted))
        .order_by('month')
        .all()
    )

    return render_template(
        'user/summary.html',
        subject_attempts=subject_attempts,
        month_attempts=month_attempts
    )





    

    
