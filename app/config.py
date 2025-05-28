import os

from dotenv import load_dotenv


class Config:
    """
    Configuration class for the application.
    Attributes:
        SECRET_KEY (str): Secret key for the application.
        ENV (str): Environment in which the application is running. Defaults to "prod".
        DEBUG (bool): Flag indicating whether debug mode is enabled. Defaults to False.
    """

    load_dotenv()
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    ENV = os.environ["ENVIRONMENT"]
    DEBUG = bool(ENV == "LOCAL" or ENV == "DEV")
