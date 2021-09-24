import json
import os
import pathlib
import shutil
import sys
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pydoc import importfile
from types import ModuleType
from typing import Dict, List, Optional, Set
from stemplates import render_template

user_config_dir = pathlib.Path(f"{os.environ['HOME']}/.config/codetemplates")
ignored = set(["__pycache__", "node_modules", "__main__.py", "__init__.py"])


class TemplateKind(Enum):
    PLAIN_DIR = 0
    PYTHON_MODULE = 1
    PYTHON_MODULE_DIR = 2


@dataclass
class DirConfig:
    description: str


@dataclass
class TemplateMetaInfo:
    kind: TemplateKind
    name: str
    full_path: pathlib.Path
    dir_config: Optional[DirConfig] = None
    mod: Optional[ModuleType] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class UserConfig:
    templates_dir_path: pathlib.Path


def load_dir_config(dir_config_path: pathlib.Path):
    with open(dir_config_path, "r") as f:
        parsed = json.load(f)
    if "description" not in parsed:
        print(
            'Invalid directory config at "{dir_config_path}": \
                    No description specified',
            file=sys.stderr,
        )
    return DirConfig(**parsed)


class MissingRequiredModuleExport(Exception):
    def __init__(self, mod, key):
        self.mod = mod
        self.key = key

    def __str__(self):
        return f'Failed to load python module template. Required \
                export symbol is not defined: "{self.key}"'


class InvalidModuleName(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f'This utility can only parse template modules of \
                .py extension or plain directories. Found file "{self.path}"'


def get_template_module_prop(mod, key, required=True, default_value=None):
    val = mod.__dict__.get(key, default_value)
    if val is None and required:
        raise MissingRequiredModuleExport(mod, key)
    return val


def import_py_template(tpath: pathlib.Path, with_resources=False):
    name, ext = os.path.splitext(tpath)
    if with_resources:
        tpath = os.path.join(tpath, "codetemplate.py")
        ext = ".py"
    name = os.path.basename(name)
    if ext != ".py":
        raise InvalidModuleName(tpath)
    mod = importfile(str(tpath))
    description = get_template_module_prop(mod, "description")
    tags = get_template_module_prop(mod, "tags", required=False, default_value=[])
    kind = (
        TemplateKind.PYTHON_MODULE_DIR if with_resources else TemplateKind.PYTHON_MODULE
    )
    tmeta = TemplateMetaInfo(
        kind=kind,
        full_path=tpath,
        name=str(name),
        mod=mod,
        description=description,
        tags=tags,
    )
    return tmeta


def import_py_dir_template(tpath: pathlib.Path):
    return import_py_template(tpath, with_resources=True)


def load_template_from_path(tpath: pathlib.Path):
    if os.path.isdir(tpath):
        py_mod_path = os.path.join(tpath, "codetemplate.py")
        is_python_anyway = os.path.exists(py_mod_path)
        if is_python_anyway:
            return import_py_dir_template(tpath)
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
    user_config_dir.mkdir(parents=True, exist_ok=True)
    templates_dir_path = pathlib.Path(f"{user_config_dir}/templates")
    templates_dir_path.mkdir(parents=True, exist_ok=True)
    return UserConfig(templates_dir_path=templates_dir_path)


@dataclass
class PipIssue:
    name: str

    def resolve(self):
        os.system(f"pip install {self.name}")

    def __str__(self):
        return self.name


def pip_installed_packages() -> Set[str]:
    return set(
        [
            a.strip().split(" ")[0].lower()
            for a in subprocess.run(["pip", "list"], capture_output=True)
            .stdout.decode()
            .split("\n")
            if a != ""
        ]
    )


def static_local(gen_statics):
    def dec(fun):
        statics = None

        def wrapper(*args, **kwargs):
            nonlocal statics
            if statics is None:
                statics = gen_statics()
            return fun(*args, **kwargs, **statics)

        return wrapper

    return dec


@static_local(lambda: {"installed_packs": pip_installed_packages()})
def pip_is_req_installed(req: str, installed_packs):
    return req in installed_packs


@static_local(lambda: {"installed_packs": npm_installed_packages()})
def pip_is_req_installed(req: str, installed_packs):
    return req in installed_packs


def pip_reqs(reqs):
    issues = []
    for req in reqs:
        i = pip_is_req_installed(req)
        if not i:
            issues.append(PipIssue(req))
    return issues


def npm_reqs(reqs):
    issues = []
    for req in reqs:
        i = npm_is_req_installed(req)
        if not i:
            issues.append(NpmIssue(req))
    return issues


class Helpers:
    resources_dir: Optional[str]

    def __init__(self, resources_dir: str):
        self.resources_dir = resources_dir

    def res_path(self, fname: str):
        return os.path.join(self.resources_dir, fname)

    def copy_resource(self, fin: str, fout: str):
        finp = self.res_path(fin)
        if os.path.isfile(finp):
            shutil.copy(finp, fout)
        else:
            shutil.copytree(finp, fout)

    def ask_boolean(self, text: str) -> bool:
        return input(f"{text} ").lower() == "y"

    def ask_string(self, text: str) -> str:
        return input(text)

    def open_stg_and_write_with(self, fin, fout, **kwargs):
        with open(fin, "r") as rc:
            tt = rc.read()
            tt = render_template(tt, **kwargs)
        with open(fout, "w") as ww:
            ww.write(tt)


def py_template_new_project(t: TemplateMetaInfo, where: pathlib.Path):
    # check if requirements are satisfied
    requirements = get_template_module_prop(
        t.mod, "requirements", required=False, default_value=None
    )
    handlers = {
        "pip": pip_reqs,
        "npm": npm_reqs,
    }
    dep_issues = []
    if requirements is not None:
        for rkind, rs in requirements.items():
            h = handlers.get(rkind, None)
            if h is None:
                raise Exception(
                    f'Invalid requirement specified: unknown requirement specifier "{rkind}"'
                )
            dep_issues += h(rs)
    if len(dep_issues) != 0:
        # unresolved dependency issues
        adj = "are not installed" if len(dep_issues) > 1 else "is not installed"
        print(
            f"There are unresolved dependency issues: {', '.join(map(str, dep_issues))} {adj}."
        )
        yn = input("Install required packages (y/n)? ")
        if yn.lower() == "y":
            print("Trying to automatically install dependencies... ")
            for issue in dep_issues:
                print("resolving issue", issue)
                issue.resolve()
            print("done")
        else:
            return None
    if t.kind == TemplateKind.PYTHON_MODULE:
        h = Helpers(None)
        res = t.mod.new_project(where, h)
    elif t.kind == TemplateKind.PYTHON_MODULE_DIR:
        resources_dir = os.path.join(os.path.dirname(t.full_path), "resources")
        h = Helpers(resources_dir)
        res = t.mod.new_project(where, resources_dir, h)
    if not res:
        print("Failed to create a new project", file=sys.stderr)


def new_project_with_template(t: TemplateMetaInfo, where: pathlib.Path):
    if t.kind == TemplateKind.PLAIN_DIR:
        shutil.copytree(t.full_path, where)
    elif (
        t.kind == TemplateKind.PYTHON_MODULE or t.kind == TemplateKind.PYTHON_MODULE_DIR
    ):
        py_template_new_project(t, where)


SearchPath = List[pathlib.Path]


def load_templates_from(search_path: SearchPath):
    templates = []
    for dp in search_path:
        for tfile in os.listdir(dp):
            tpath = pathlib.Path(dp, tfile)
            if should_ignore_template_name(tpath):
                continue
            tmeta = load_template_from_path(tpath)
            templates.append(tmeta)
    return templates


class CodeTemplateManager:
    search_path: SearchPath = []
    config: UserConfig

    def __init__(self):
        self.config = load_user_config()
        self.search_path.append(self.config.templates_dir_path)
        script_dir = pathlib.Path(__file__).parent.resolve()
        self.search_path.append(pathlib.Path(script_dir, "../templates").resolve())

    def search(self, what: str):
        templates = load_templates_from(self.search_path)
        entries = []
        for t in templates:
            what = what.lower()
            desc = t.description if t.description else ""
            if (
                what in t.name.lower()
                or what in desc.lower()
                or any([what in t for t in t.tags])
            ):
                entries.append(t)
        return entries

    def load_template(self, template: str):
        for dp in self.search_path:
            dtp = pathlib.Path(dp, template)
            if os.path.exists(dtp):
                return load_template_from_path(dtp)
            pytp = pathlib.Path(dp, f"{template}.py")
            if os.path.exists(pytp):
                return load_template_from_path(pytp)
        return None

    def new(self, template, where):
        t = self.load_template(template)
        if t is None:
            return False
        new_project_with_template(t, where)
        return True

    def init(self, template):
        return True


class CodeTemplateManagerCLI:
    def __init__(self):
        self.manager = CodeTemplateManager()

    def search(self, what):
        print(f'Searching "{what}"')
        entries = self.manager.search(what)
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
            elif entry.kind == TemplateKind.PYTHON_MODULE_DIR:
                print(f"[python-dir] {entry.name}: {entry.description}")
        print(f"Total templates found: {len(entries)}")

    def new(self, template, where):
        print(f'Creating new project with template "{template}"')
        if not self.manager.new(template, where):
            print(f'Failed to load template "{template}"')

    def init(self, template):
        print(f'Initializing project with template "{template}"')
        self.manager.init(template)
