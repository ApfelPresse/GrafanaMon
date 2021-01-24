import os


def get_env(key, default=None):
    try:
        return os.environ[key]
    except:
        if not default:
            raise
    return default
