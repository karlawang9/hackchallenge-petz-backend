import json

from db import db
from flask import Flask, request
from db import User, Category, Review
import datetime
import users_dao

app = Flask(__name__)
db_filename = "petz.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


# generalized response formats
def success_response(data, code=200):
    return json.dumps(data, default=str), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


def extract_token(request):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, json.dumps({"error": "Missing auth header"})
    bearer_token = auth_header.replace("Bearer", "").strip()
    if not bearer_token:
        return False, json.dumps({"error": "Invalid auth header"})
    return True, bearer_token


# -- USER ROUTES ------------------------------------------------------


@app.route("/")
@app.route("/users/")
def get_users():
    """
    Endpoint for getting all users
    """
    users = [user.serialize() for user in User.query.all()]
    return success_response({"users": users})


@app.route("/users/<int:user_id>/")
def get_user(user_id):
    """
    Endpoint for getting a specific user by id
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:    
        return failure_response("User not found")
    return success_response(user.serialize())


@app.route("/users/categories/<int:category_id>/")
def get_users_by_category(category_id):
    """
    Endpoint for getting all host users by a category id
    """
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found")
    return success_response(category.serialize().get("hosts"))


@app.route("/users/available/")
def get_available_users():
    """
    Endpoint for getting all host users that are available
    """
    available_hosts = User.query.filter_by(available=True)
    return success_response({"available hosts": [host.serialize() for host in available_hosts]})


# @app.route("/users/", methods=["POST"])
# def create_user():
#     """
#     Endpoint for creating a new user
#     """
#     body = json.loads(request.data)
#     username = body.get("username")
#     bio = body.get("bio")
#     contact = body.get("contact")
#     host = body.get("host", False)
#     owner = body.get("owner", False)
#     available = body.get("available", False)
#     if (username is None) or (contact is None):
#         return failure_response("Missing input", 400)
#     new_user = User(
#         username = username,
#         bio = bio,
#         contact = contact,
#         host = host,
#         owner = owner,
#         available = available
#     )
#     db.session.add(new_user)
#     db.session.commit()
#     return success_response(new_user.serialize(), 201)


@app.route("/users/<int:user_id>/", methods=["POST"])
def update_user_by_id(user_id):
    """
    Endpoint for updating a specific user by id
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found")
    body = json.loads(request.data)
    bio = body.get("bio")
    if bio is not None:
        user.bio = bio
    contact = body.get("contact")
    if contact is not None:
        user.contact = contact
    host = body.get("host")
    if host is not None:
        user.host = host
    owner = body.get("owner")
    if owner is not None:
        user.owner = owner
    available = body.get("available")
    if available is not None:
        user.available = available
    db.session.commit()
    return success_response(user.serialize(), 201)


@app.route("/users/<int:user_id>/", methods=["DELETE"])
def delete_user(user_id):
    """
    Endpoint for deleting a specific user by id
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found")
    db.session.delete(user)
    db.session.commit()
    return success_response(user.serialize())


# -- CATEGORY ROUTES ------------------------------------------------------


@app.route("/categories/")
def get_categories():
    """
    Endpoint for getting all categories
    """
    categories = [category.serialize() for category in Category.query.all()]
    return success_response({"categories": categories})


@app.route("/users/<int:user_id>/category/")
def get_categories_by_host(user_id):
    """
    Endpoint for getting all categories for a specific host
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found")
    return success_response([c.serialize()["description"] for c in user.categories_h])


@app.route("/categories/", methods=["POST"])
def create_category():
    """
    Endpoint for creating a new category
    """
    body = json.loads(request.data)
    description = body.get("description")
    if (description is None):
        return failure_response("Missing input", 400)
    new_category = Category(
        description = description
    )
    db.session.add(new_category)
    db.session.commit()
    return success_response(new_category.serialize(), 201)


@app.route("/categories/<int:category_id>/add/", methods=["POST"])
def assign_user_to_category(category_id):
    """
    Endpoint for adding a user to a specific category by id
    """
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found!")
    body = json.loads(request.data)
    type = body.get("type")
    user_id = body.get("user_id")
    if (type != "host") and (type != "owner"):
        return failure_response("Invalid input", 400)

    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    if type == "host":
        category.hosts.append(user)
    elif type == "owner":
        category.owners.append(user)
    db.session.commit()
    return success_response(category.serialize(), 201)


@app.route("/categories/<int:category_id>/", methods=["DELETE"])
def delete_category(category_id):
    """
    Endpoint for deleting a specific category
    """
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found")
    db.session.delete(category)
    db.session.commit()
    return success_response(category.serialize())


# -- REVIEW ROUTES ------------------------------------------------------


@app.route("/users/<int:reviewee_id>/review/", methods=["POST"])
def create_review(reviewee_id):
    """
    Endpoint for creating a review for a user by user id (reviewee_id)
    """
    reviewee = User.query.filter_by(id=reviewee_id).first()
    if reviewee is None:
        return failure_response("User not found")
    body = json.loads(request.data)
    rating = body.get("rating")
    text = body.get("text")
    if (rating is None) or (text is None):
        return failure_response("Missing input", 400)
    if (rating < 0) or (rating > 5):
        return failure_response("Rating must be an integer from 0 through 5", 400)
    new_review = Review(
        rating = rating,
        text = text,
        reviewee_id = reviewee_id
    )
    db.session.add(new_review)
    # reviewee.reviews.append(new_review.id)
    if reviewee.overall_rating is None:
        reviewee.overall_rating = rating
    else:
        reviewee.overall_rating = (reviewee.overall_rating * (len(reviewee.reviews) - 1) + rating) / (len(reviewee.reviews))
    reviewee.reviews.append(new_review)
    db.session.commit()
    res = new_review.serialize()
    return success_response(res, 201)


@app.route("/reviews/<int:review_id>/")
def get_review(review_id):
    """
    Endpoint for getting a review by review_id
    """
    review = Review.query.filter_by(id=review_id).first()
    if review is None:    
        return failure_response("Review not found")
    return success_response(review.serialize())


@app.route("/users/<int:reviewee_id>/review/")
def get_reviews_by_reviewee(reviewee_id):
    """
    Endpoint for getting all reviews for a specific user (reviewee)
    """
    reviewee = User.query.filter_by(id=reviewee_id).first()
    if reviewee is None:
        return failure_response("User not found")
    return success_response(reviewee.serialize().get("reviews"))


# @app.route("/reviews/<int:review_id>/", methods=["DELETE"])
# def delete_review(review_id):
#     """
#     Endpoint for deleting a specific review by review_id
#     """
#     review = Review.query.filter_by(id=review_id).first()
#     if review is None:
#         return failure_response("Review not found")
#     db.session.delete(review)
#     db.session.commit()
#     return success_response(review.serialize())


# -- AUTH ROUTES ------------------------------------------------------


@app.route("/users/", methods=["POST"])
def register_account():
    """
    Endpoint for registering a new user
    """
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")
    name = body.get("name")
    username = body.get("username")
    bio = body.get("bio")
    contact = body.get("contact")
    host = body.get("host", False)
    owner = body.get("owner", False)
    available = body.get("available", False)

    if email is None or password is None:
        return failure_response("Invalid email or password", 400)
    
    if (name is None) or (username is None) or (contact is None):
        return failure_response("Missing input", 400)
    
    created, user = users_dao.create_user(
        email=email, 
        password=password,
        name = name, 
        username = username, 
        bio = bio,
        contact = contact,
        host = host,
        owner = owner, 
        available = available
    )
    
    if not created:
        return json.dumps({"error": "Incorrect email or password"}), 400

    return json.dumps(
        {
        "user": user.serialize(),
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "update_token": user.update_token
        }
    ), 201


@app.route("/login/", methods=["POST"])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")

    if email is None or password is None:
        return json.dumps({"error": "Invalid email or password"}), 400
    
    success, user = users_dao.verify_credentials(email, password)

    if not success:
        return json.dumps({"error": "Incorrect email or password"}), 400
    
    return json.dumps(
        {
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "update_token": user.update_token
        }
    )


@app.route("/session/", methods=["POST"])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, update_token = extract_token(request)
    
    if not success:
        return update_token
    
    user = users_dao.renew_session(update_token)
    
    if user is None:
        return json.dumps({"error": "Invalid update token"})
    
    return json.dumps(
        {
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "update_token": user.update_token
        }
    )


@app.route("/secret/", methods=["GET"])
def secret_message():
    """
    Endpoint for verifying a session token and returning a secret message

    In your project, you will use the same logic for any endpoint that needs 
    authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return session_token
    user = users_dao.get_user_by_session_token(session_token)
    if user is None or user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"})
    return json.dumps({"message": "Wow we implemented session token!!"})


@app.route("/logout/", methods=["POST"])
def logout():
    """
    Endpoint for logging out a user
    """
    success, session_token = extract_token(request)
    if not success:
        return session_token
    
    user = users_dao.get_user_by_session_token(session_token)
    
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token"}), 400
    
    user.session_expiration = datetime.datetime.now()
    db.session.commit()

    return json.dumps({"message": "User has successfully logged out"})


# -- TRANSACTION ROUTES ------------------------------------------------------

"""
outline of transaction routes below
"""
# @app.route("/transactions/<int:txn_id>")
# def get_txn_by_id(txn_id):
#     """
#     Endpoint for getting a transaction by a specific transaction id
#     """

# @app.route("/transactions/", methods=["POST"])
# def create_txn():
#     """
#     Endpoint for creating a transaction by sending or requesting money
#     """

# @app.route("/transactions/<int:txn_id>", methods=["POST"])
# def update_accepted(txn_id):
#     """
#     Endpoint for accepting or denying a payment request given the transaction id
#     """



# ----------------------------------------------------------------------------

# @app.route("/api/users/", methods=["POST"])
# def create_user():
#     """
#     Endpoint for creating a user
#     """
#     body = json.loads(request.data)
#     name = body.get("name")
#     netid = body.get("netid")
#     if (name is None) or (netid is None):
#         return failure_response("Missing input", 400)
#     new_user = User(
#         name = name,
#         netid = netid
#     )
#     db.session.add(new_user)
#     db.session.commit()
#     res = new_user.serialize()
#     res["courses"] = []
#     return success_response(res, 201)

# @app.route("/api/users/<int:user_id>/")
# def get_user(user_id):
#     """
#     Endpoint for getting a specific user by id
#     """
#     user = User.query.filter_by(id=user_id).first()
#     if user is None:
#         return failure_response("User not found!")
#     userinfo = user.serialize()
#     coursesinfo = {"courses": [c.joint_serialize() for c in user.courses_i] + [c.joint_serialize() for c in user.courses_s]}
#     return success_response(dict(userinfo, **coursesinfo))

# @app.route("/api/courses/<int:course_id>/add/", methods=["POST"])
# def add_user_to_course(course_id):
#     """
#     Endpoint for adding a user to a specific course by id
#     """
#     course = Course.query.filter_by(id=course_id).first()
#     if course is None:
#         return failure_response("Course not found!")
#     body = json.loads(request.data)
#     user_id = body.get("user_id")
#     type = body.get("type")
#     if type != "student" and type != "instructor":
#         return failure_response("Invalid input", 400)

#     user = User.query.filter_by(id=user_id).first()
#     if user is None:
#         return failure_response("User not found!")
#     if type == "instructor":
#         course.instructors.append(user)
#     elif type == "student":
#         course.students.append(user)
#     db.session.commit()
#     return success_response(course.serialize())


# -- REVIEW ROUTES ------------------------------------------------------


# @app.route("/api/courses/<int:course_id>/assignment/", methods=["POST"])
# def create_assignment(course_id):
#     """
#     Endpoint for creating an assignment for a course by course id
#     """
#     course = Course.query.filter_by(id=course_id).first()
#     if course is None:
#         return failure_response("Course not found!")
#     body = json.loads(request.data)
#     title = body.get("title")
#     due_date = body.get("due_date")
#     if (title is None) or (due_date is None):
#         return failure_response("Missing input", 400)
#     new_assignment = Assignment(
#         title = title,
#         due_date = due_date,
#         course_id = course_id
#     )
#     db.session.add(new_assignment)
#     course.assignments.append(new_assignment)
#     db.session.commit()
#     res = new_assignment.serialize()
#     res["course"] = {"id": course_id, "code": course.code, "name": course.name}
#     return success_response(res, 201)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
