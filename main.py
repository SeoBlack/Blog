import sqlalchemy.exc
from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from functools import wraps
from flask_gravatar import Gravatar
import os



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL","sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES
def admin_only(f):
    @wraps(f)
    def  decoration_function(*args,**kwargs):
        if current_user.id != 1:
            return redirect(url_for("get_all_posts"))
        return f(*args,**kwargs)
    return decoration_function
class User(UserMixin,db.Model):
    __tablename__ = "users"
    id= db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(250),nullable=False)
    email = db.Column(db.String(250),nullable=False,unique=True)
    password = db.Column(db.String(500),nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates= "post")
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer,db.ForeignKey("blog_posts.id"))
    post = relationship("BlogPost", back_populates="comments")
    author = relationship("User", back_populates ="comments")
    text=db.Column(db.String(250),nullable=False)




db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    if current_user.is_authenticated:
        return render_template("index.html", all_posts=posts,logged_in = current_user.is_authenticated,user_id = current_user.id)
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


@app.route('/register',methods = ["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.data.get("email")).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        new_user = User()
        new_user.name = form.data.get("name")
        new_user.email = form.data.get("email")
        new_user.password = generate_password_hash(form.data.get("password"),"pbkdf2:sha256",salt_length=16)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html",form=form,logged_in = current_user.is_authenticated)


@app.route('/login',methods = ["POST","GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.data.get("email")
        password = form.data.get("password")
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password,password):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password incorrect, please try again")
                return redirect(url_for("login"))
        else:
            flash("User account was not found, please try again")
            return redirect(url_for("login"))

    return render_template("login.html",form = form,logged_in = current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods = ["POST","GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment =  Comment()
            new_comment.text = form.comment.data
            new_comment.author = current_user
            new_comment.post = requested_post
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("Please Login to comment")
            return redirect(url_for("login"))
    comments = Comment.query.all()
    if current_user.is_authenticated:
        return render_template("post.html", post=requested_post,logged_in = current_user.is_authenticated,user_id= current_user.id,form=form)
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated,comments = comments)


@app.route("/about")
def about():
    return render_template("about.html",logged_in = current_user.is_authenticated)


@app.route("/contact")
@login_required
def contact():
    return render_template("contact.html",logged_in = current_user.is_authenticated)


@app.route("/new-post",methods=["POST","GET"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,logged_in = current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>")
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,logged_in = current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route("/delete/<int:post_id>/<int:comment_id>")
@login_required
@admin_only
def delete_comment(comment_id,post_id):
    comment = Comment.query.get(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for("show_post",post_id=post_id))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
