from flask import Flask, render_template, flash , redirect, url_for, session, logging, request

from functools import wraps
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt


app = Flask(__name__)

#config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myflask'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#init MYSQL
mysql = MySQL(app)



# Register Form class
class RegisterForm(Form):

    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message="Password do not match")
    ])
    confirm = PasswordField('Confirm Password')
#Article Form class
class ArticleForm(Form):

    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


#Index
@app.route('/')
def index():
    return render_template('home.html')
#About
@app.route('/about')
def about():
    return render_template('about.html')
#Articles
@app.route('/articles')
def articles():
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    #result = cur.execute("SELECT * FROM articles")
    # Get articles
    result = cur.execute(
        "SELECT a.id, a.title, a.body, a.create_data, u.name FROM articles AS a INNER JOIN users AS u ON a.author = u.id ORDER BY a.create_data DESC")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)

    cur.close()

    #return render_template('articles.html',articles = Articles)
# Single article
@app.route('/article/<string:id>')
def article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    result = cur.execute("SELECT c.id, c.user_id, c.post_id, c.text, c.created_data,u.id, u.name FROM comments AS c INNER JOIN users AS u ON c.user_id = u.id WHERE c.post_id = %s",[id])

    comments = cur.fetchall()

    # Commit to DB
    mysql.connection.commit()
    # Close connection
    cur.close()



    return render_template('article.html',article = article, comments =comments)

#user register
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #Create cursor
        cur = mysql.connection.cursor()

        #Execute query
        cur.execute("INSERT INTO users(name, email, username, password) "
                                    "VALUES(%s, %s, %s, %s)",
                                    (name,email,username,password))
        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registred and can log in', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()
        # get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            #Get stored hash
            data = cur.fetchone()
            password = data['password']
            user_id = data['id']

            # Compare Passwprds
            if sha256_crypt.verify(password_candidate, password):
                #app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['username'] = username
                session['id'] = user_id

                flash('You are now log in', 'success')
                return redirect(url_for('dashboard'))
            else:
                #app.logger.info('PASSWORD NOT MATCHED')
                error = 'Invalid login'
                return render_template('login.html', error=error)

            #close connetion
            cur.close()

        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Plase login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    #Get articles
    result = cur.execute("SELECT a.id, a.title, a.body, a.create_data, u.name FROM articles AS a LEFT JOIN users AS u ON a.author = u.id ORDER BY a.create_data DESC")

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)

    cur.close()


#Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        #Creatae caursor
        cur = mysql.connection.cursor()
        #Execute
        cur.execute("INSERT INTO articles(title, body, author ) VALUES(%s, %s, %s)", (title, body, session['id']))

        #Commit
        mysql.connection.commit()

        #Close
        cur.close()

        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)

# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    #create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    #Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        #Creatae caursor
        cur = mysql.connection.cursor()
        #Execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s", (title,body,id))

        #Commit
        mysql.connection.commit()

        #Close
        cur.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)
#Delete Article
@app.route('/delete_article/<string:id>', methods = ['POST'])
@is_logged_in
def delete_article(id):
    #create cursor
    cur = mysql.connection.cursor()

    #Execute
    cur.execute("DELETE FROM articles WHERE id = %s",[id])
    # Commit to Db
    mysql.connection.commit()
    #close conn
    cur.close()

    flash('Article Deleted', 'success')
    return  redirect(url_for('dashboard'))

#Add Comment
@app.route('/add_comment/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def add_comment(id):

    if request.method == 'POST':

        text = request.form['text']
        post_id = id
        user_id = session['id']

        #Creatae caursor
        cur = mysql.connection.cursor()
        #Execute
        cur.execute("INSERT INTO comments(user_id, post_id, text ) VALUES(%s, %s, %s)", (user_id, post_id, text))
        #Commit
        mysql.connection.commit()
        #Close
        cur.close()
        flash('Comment added', 'success')

        #Create cursor
        cur = mysql.connection.cursor()

        # Get articles
        result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

        article = cur.fetchone()

        result = cur.execute(
            "SELECT c.id, c.user_id, c.post_id, c.text, c.created_data,u.id, u.name FROM comments AS c INNER JOIN users AS u ON c.user_id = u.id WHERE c.post_id = %s",
            [id])

        comments = cur.fetchall()


    return render_template('article.html', article= article, comments= comments)



if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)



