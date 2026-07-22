import os
import json

CONFIG_FILE = 'bp_tracker_config.json'


def get_config_path():
    from kivy.app import App
    app = App.get_running_app()
    if app:
        return os.path.join(app.user_data_dir, CONFIG_FILE)
    return CONFIG_FILE


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_config(config):
    path = get_config_path()
    with open(path, 'w') as f:
        json.dump(config, f)


def get_api_key():
    return load_config().get('google_vision_api_key', '')


def set_api_key(key):
    config = load_config()
    config['google_vision_api_key'] = key
    save_config(config)
