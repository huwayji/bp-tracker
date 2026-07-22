[app]
title = BP Tracker
package.name = bptracker
package.domain = org.bptracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,md
version = 1.0
requirements = python3,kivy,pillow,requests
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 21
android.ndk = 27b
android.arch = arm64-v8a
android.permissions = INTERNET,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.enable_androidx = True
android.accept_sdk_license = True
android.copy_libs = True
android.wakelock = False
android.keep_screen_on = False
author = 
description = Blood Pressure Tracking App
icon = 
presplash = 
source.exclude = __pycache__/*.pyc,*.pyc,.git
log_level = 2
log_dir = ./.logs

[buildozer]
log_level = 2
warn_on_root = 1
archive = 0
