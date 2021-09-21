import os
import pathlib
import shutil
from string import Template
import json

description = "Rollup Library"
tags = ["javascript", "js", "library", "browser", "web", "rollup", "react", "npm"]


def ask_boolean(text: str) -> bool:
    return input(f"{text} ").lower() == "y"


def ask_string(text: str) -> str:
    return input(text)


def open_stg_and_write_with(fin, fout, **kwargs):
    with open(fin, "r") as rc:
        tt = rc.read()
        tp = Template(tt)
        tt = tp.substitute(**kwargs)
    with open(fout, "w") as ww:
        ww.write(tt)


# TODO: Browser tests support using jest-puppeteer
def new_project(where: pathlib.Path, resources_dir: pathlib.Path):
    shutil.rmtree(where)
    os.mkdir(where)
    os.chdir(where)

    def res_path(fname: str):
        return os.path.join(resources_dir, fname)

    def copy_resource(fin: str, fout: str):
        finp = res_path(fin)
        if os.path.isfile(finp):
            shutil.copy(finp, fout)
        else:
            shutil.copytree(finp, fout)

    # Setup npm and dependencies
    os.system("npm init")
    ts_enabled = ask_boolean("Set up TypeScript?")
    tests_enabled = ask_boolean("Set up tests?")
    deps = ["rollup", "@rollup/plugin-commonjs"]
    if ts_enabled:
        ts_deps = ["@rollup/plugin-typescript", "typescript"]
        deps = [*deps, *ts_deps]
    if tests_enabled:
        deps = [*deps, "jest"]
    if ts_enabled and tests_enabled:
        deps = [*deps, "@types/jest"]
    deps_s = " ".join(deps)
    # os.system(f"npm install {deps_s}")

    # Create directories
    src_dir = ask_string("Directory name for library source code: ")
    entry_file_name = ask_string("Entry file name: ")
    os.mkdir(src_dir)

    # Modify package.json
    out_prefix = os.path.splitext(entry_file_name)[0]
    package_json_path = os.path.join(src_dir, "package.json")
    with open(package_json_path, "r") as pf:
        package_json = json.load(pf)
    package_json["main"] = f"./build/{out_prefix}.min.js"
    package_json["browser"] = f"./build/{out_prefix}.min.js"
    package_json["module"] = f"./build/{out_prefix}-esm.js"
    if ts_enabled:
        package_json["types"] = f"./build/{out_prefix}.d.js"
    package_json["files"] = ["build"]
    package_json["directories"] = {"test": "test"}
    package_json["scripts"] = {
        "build": "cross-env NODE_ENV=production rollup -c rollup.config.js",
        "build-dev": "cross-env NODE_ENV=development rollup -c rollup.config.js",
    }
    if tests_enabled:
        package_json["scripts"] = {"test": "jest"}
    with open(package_json_path, "w") as pf:
        json.dump(pf, package_json)

    # Create rollup config
    open_stg_and_write_with(
        fin=res_path("rollup.config.js.stg"),
        fout="rollup.config.js",
        source_dir_path=src_dir,
        entry_file_name=entry_file_name,
        out_prefix=out_prefix,
    )
    entry_file_path = os.path.join(src_dir, entry_file_name)
    copy_resource("entry-file.js", entry_file_path)

    # tsconfig.json
    if ts_enabled:
        open_stg_and_write_with(
            fin=res_path("tsconfig.json.ctg"),
            fout="tsconfig.json",
            source_dir_path=src_dir,
        )

    # Test directory
    if ts_enabled and tests_enabled:
        copy_resource("jest.config-ts.js", "jest.config.js")
        copy_resource("test-ts", "test")
    elif tests_enabled:
        copy_resource("test-js", "test")

    return True
