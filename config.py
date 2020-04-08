import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'some-key-that-should-not-get-hacked'