from flask_sqlalchemy import SQLAlchemy
import datetime
import os
import hashlib
import bcrypt

db = SQLAlchemy()

association_table_h = db.Table(
    "association_host",
    db.Column("category_id", db.Integer, db.ForeignKey("category.id")),
    db.Column("host_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_o = db.Table(
    "association_owner",
    db.Column("category_id", db.Integer, db.ForeignKey("category.id")),
    db.Column("owner_id", db.Integer, db.ForeignKey("user.id"))
)

class User(db.Model):
    """
    User model
    """

    __tablename___ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    bio = db.Column(db.String, nullable=True) #for profile
    contact = db.Column(db.String, nullable=False) #email or phone number
    overall_rating = db.Column(db.Float, nullable=True)
    reviews = db.relationship("Review", cascade="delete")
    #images = 
    host = db.Column(db.Boolean, default=False)
    owner = db.Column(db.Boolean, default=False)
    categories_h = db.relationship("Category", secondary=association_table_h, back_populates="hosts")
    categories_o = db.relationship("Category", secondary=association_table_o, back_populates="owners")
    available = db.Column(db.Boolean, default=False) #available for hosting
    # user info for auth
    email = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)
    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        """
        Initializes a User model
        """
        self.name = kwargs.get("name")
        self.username = kwargs.get("username")
        self.bio = kwargs.get("bio")
        self.contact = kwargs.get("contact")
        self.host = kwargs.get("host")
        self.owner = kwargs.get("owner")
        self.available = kwargs.get("available")
        # auth stuff
        self.email = kwargs.get("email")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()

    def serialize(self):
        """
        Serializes a User object
        """
        return {
            "id": self.id,
            "name": self.name, 
            "username": self.username,
            "bio": self.bio,
            "contact": self.contact,
            "overall_rating": self.overall_rating,
            "reviews": [r.serialize() for r in self.reviews],
            "host": self.host,
            "owner": self.owner,
            "categories_h": [c.description for c in self.categories_h],
            "categories_o": [c.description for c in self.categories_o],
            # "categories_h": [h.serialize() for h in self.categories_h],
            # "categories_o": [o.serialize() for o in self.categories_o],
            "available": self.available
        }
    
    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token


class Category(db.Model):
    """
    Category model (category = pet type)
    """

    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String, nullable=False)
    hosts = db.relationship("User", secondary=association_table_h, back_populates="categories_h")
    owners = db.relationship("User", secondary=association_table_o, back_populates="categories_o")

    def __init__(self, **kwargs):
        """
        Initializes a Category object
        """
        self.description = kwargs.get("description")

    def serialize(self):
        """
        Serializes a Category object
        """
        return {
            "id": self.id, 
            "description": self.description,
            "hosts": [h.serialize() for h in self.hosts],
            "owners": [o.serialize() for o in self.owners]
        }
    
    # def joint_serialize(self):
    #     """
    #     Serializes a Category object with only id and description. Used for joint serialization of categories_h and categories_o.
    #     """
    #     return {
    #         "id": self.id, 
    #         "description": self.description
    #     }

class Review(db.Model):
    """
    Review model
    """

    __tablename__ = "review"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a Review object
        """
        self.rating = kwargs.get("rating")
        self.text = kwargs.get("text")
        self.date = datetime.datetime.now()
        self.reviewee_id = kwargs.get("reviewee_id")
        # self.reviewer_id = kwargs.get("reviewer_id")

    def serialize(self):
        """
        Serializes a Review object
        """
        return {
            "id": self.id, 
            "rating": self.rating,
            "text": self.text,
            "date": self.date,
            "reviewee_id": self.reviewee_id
            # "reviewer_id": self.reviewer_id
        }
    
#class Transaction(db.Model):
    """
    Transaction model [not implemented lol]
    """