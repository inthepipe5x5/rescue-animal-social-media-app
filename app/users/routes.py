import os
from flask import Blueprint, flash, redirect, session, g, render_template, url_for, request
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from models import db, User
from forms import UserEditForm
from ..users.routes import do_logout

users_bp = Blueprint('users', __name__, template_folder='templates', static_folder='static', url_prefix='/users')

load_dotenv()
CURR_USER_KEY = os.environ.get("CURR_USER_KEY", 'curr_user')


##############################################################################
# General user routes:

@users_bp.route('/')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('/index.html', users=users)


@users_bp.route('/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)
    
    return render_template('/show.html', user=user)


@users_bp.route('/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('/following.html', user=user)


@users_bp.route('/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('/followers.html', user=user)


@users_bp.route('/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/{g.user.id}/following")


@users_bp.route('/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/{g.user.id}/following")


@users_bp.route('/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for('login'))
    
    else:
        logged_in_user = User.query.get(g.user.id)
        form = UserEditForm(obj=logged_in_user)

        if form.validate_on_submit(): 
            if User.authenticate(form.username.data, form.password.data):
                form.populate_obj(logged_in_user)
                db.session.add(logged_in_user)
                db.session.commit() #commit to db
                flash('Changes saved successfully','success') #show success to user
                return redirect(url_for('users_show',user_id=logged_in_user.id))
            else: 
                db.session.rollback()
                flash('You were unsuccessful, try again','error') #show success to user
                return render_template('/edit.html', form=form, user=logged_in_user) 
                
        return render_template('/edit.html', form=form, user=logged_in_user) 




@users_bp.route('/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")

