import os
import pathlib

description = "Create a React project using create-react-app utility"

def new_project(where: pathlib.Path):
    print("Creating new React project")
    os.system(f"create-react-app {str(where)}")
