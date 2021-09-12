import os
import sys
import pathlib
import json
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from types import ModuleType
from enum import Enum
from pydoc import importfile

dir_path = pathlib.Path(f"{os.environ['HOME']}/.config/codetemplates")
templates_dir_path = pathlib.Path(f"{dir_path}/templates")
ignored = set(["__pycache__", "node_modules", "__main__.py", "__init__.py"])

class TemplateKind(Enum):
    PLAIN_DIR = 0
    PYTHON_MODULE = 1


@dataclass
class DirConfig:
    description: str


@dataclass
class TemplateMetaInfo:
    kind: TemplateKind
    name: str
    full_path: pathlib.Path
    dir_config: DirConfig = None
    mod: ModuleType = None
    description: str = None


@dataclass
class UserConfig:
    templates: List[TemplateMetaInfo]


def load_dir_config(dir_config_path: pathlib.Path):
    with open(dir_config_path, "r") as f:
        parsed = json.load(f)
    if not "description" in parsed:
        print("Invalid directory config at \"{dir_config_path}\": No description specified", file=sys.stderr)
    return DirConfig(**parsed)


class MissingRequiredModuleExport(Exception):
    def __init__(self, mod, key):
        self.mod = mod
        self.key = key

    def __str__(self):
        return f"Failed to load python module template. Required export symbol is not defined: \"{self.key}\""


class InvalidModuleName(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f"This utility can only parse template modules of .py extension or plain directories. Found file \"{self.path}\""


def get_template_module_prop(mod, key, required=True):
    val = mod.__dict__.get(key, None)
    if val is None:
        raise MissingRequiredModuleExport(mod, key)
    return val


def import_py_template(tpath: pathlib.Path):
    name, ext = os.path.splitext(tpath)
    name = os.path.basename(name)
    if ext != ".py":
        raise InvalidModuleName(tpath)
    mod = importfile(str(tpath))
    description = get_template_module_prop(mod, "description")
    kind = TemplateKind.PYTHON_MODULE
    tmeta = TemplateMetaInfo(kind=kind, full_path=tpath, name=str(name), mod=mod, description=description)
    return tmeta


def load_template_from_path(tpath: pathlib.Path):
    if os.path.isdir(tpath):
        # Plain directory
        kind = TemplateKind.PLAIN_DIR
        name = os.path.basename(tpath)
        tmeta = TemplateMetaInfo(kind=kind, full_path=tpath, name=name)
        # Check if has yml config
        yconfig_paths = [pathlib.Path(tpath, "codetemplates.json")]
        for p in yconfig_paths:
            if os.path.exists(p):
                tmeta.dir_config = load_dir_config(p)
                tmeta.description = tmeta.dir_config.description
        return tmeta
    else:
        return import_py_template(tpath)


def should_ignore_template_name(tpath: pathlib.Path):
    name = os.path.basename(tpath)
    if name in ignored:
        return True
    return False


def load_user_config():
    dir_path.mkdir(parents=True, exist_ok=True)
    templates_dir_path.mkdir(parents=True, exist_ok=True)
    templates = []
    for tfile in os.listdir(templates_dir_path):
        tpath = pathlib.Path(templates_dir_path, tfile)
        if should_ignore_template_name(tpath):
            continue
        tmeta = load_template_from_path(tpath)
        templates.append(tmeta)
    return UserConfig(templates=templates)


def load_template(template: str):
    dtp = pathlib.Path(templates_dir_path, template)
    if os.path.exists(dtp):
        return load_template_from_path(dtp)
    pytp = pathlib.Path(templates_dir_path, f"{template}.py")
    if os.path.exists(pytp):
        return load_template_from_path(pytp)
    return None


def new_project_with_template(t: TemplateMetaInfo, where: pathlib.Path):
    if t.kind == TemplateKind.PLAIN_DIR:
        shutil.copytree(t.full_path, where)
    elif t.kind == TemplateKind.PYTHON_MODULE:
        res = t.mod.new_project(where)


class CodeTemplateManager:
    templates = []

    def __init__(self):
        self.config = load_user_config()
        self.templates = self.config.templates

    def search(self, what):
        print(f"Searching \"{what}\"")
        entries = []
        for t in self.templates:
            what = what.lower()
            desc = t.description if t.description else ""
            if what in t.name.lower() or what in desc.lower():
                entries.append(t)
        if len(entries) == 0:
            print("Nothing found")
            return
        for entry in entries:
            if entry.kind == TemplateKind.PLAIN_DIR:
                if entry.description is not None:
                    print(f"[dir] {entry.name}: {entry.description}")
                else:
                    print(f"[dir] {entry.name}")
            elif entry.kind == TemplateKind.PYTHON_MODULE:
                print(f"[python] {entry.name}: {entry.description}")
        print(f"Total templates found: {len(entries)}")

    def new(self, template, where):
        print(f"Creating new project with template \"{template}\"")
        t = load_template(template)
        if t is None:
            print(f"Failed to load template \"{template}\"")
            return
        new_project_with_template(t, where)

    def init(self, template):
        print(f"Initializing project with template \"{template}\"")
