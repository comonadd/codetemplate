import os
import pathlib

description = "Create a Django project using django-admin utility"
tags = ["python", "django", "web", "app", "framework"]
requirements = {"pip": ["django-admin", "django"]}


def new_project(where: pathlib.Path):
    os.system(f"django-admin startproject {str(where)}")
