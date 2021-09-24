import os
import pathlib
import shutil
import json
from stemplates import render_template

# Template
description = "Rollup Library"
tags = ["javascript", "js", "library", "browser", "web", "rollup", "react", "npm"]


# TODO: Browser tests support using jest-puppeteer
def new_project(where: pathlib.Path, resources_dir: pathlib.Path, h):
    if os.path.exists(where):
        shutil.rmtree(where)
    os.mkdir(where)
    os.chdir(where)

    # Setup npm and dependencies
    os.system("npm init")
    ts_enabled = h.ask_boolean("Set up TypeScript?")
    tests_enabled = h.ask_boolean("Set up tests?")
    deps = [
        "rollup",
        "@rollup/plugin-commonjs",
        "cross-env",
        "rollup-plugin-terser",
        "rollup-plugin-node-resolve",
        "del",
    ]
    if ts_enabled:
        ts_deps = ["@rollup/plugin-typescript", "typescript"]
        deps = [*deps, *ts_deps]
    if tests_enabled:
        deps = [*deps, "jest"]
    if ts_enabled and tests_enabled:
        deps = [*deps, "@types/jest", "ts-jest"]
    deps_s = " ".join(deps)
    os.system(f"npm install {deps_s}")

    # Create directories
    src_dir = h.ask_string("Directory name for library source code: ")
    entry_file_name = h.ask_string("Entry file name: ")
    os.mkdir(src_dir)

    # Modify package.json
    out_prefix = os.path.splitext(entry_file_name)[0]
    package_json_path = os.path.join("package.json")
    with open(package_json_path, "r") as pf:
        package_json = json.load(pf)
    package_json["main"] = f"./build/{out_prefix}.min.js"
    package_json["browser"] = f"./build/{out_prefix}.min.js"
    package_json["module"] = f"./build/{out_prefix}-esm.js"
    if ts_enabled:
        package_json["types"] = f"./build/{out_prefix}.d.js"
    package_json["files"] = ["build"]
    package_json["directories"] = {"test": "test"}
    package_json["scripts"] = {}
    package_json["scripts"][
        "build"
    ] = "cross-env NODE_ENV=production rollup -c rollup.config.js"
    package_json["scripts"]["build-dev"] = (
        "cross-env NODE_ENV=development rollup -c rollup.config.js",
    )
    if tests_enabled:
        package_json["scripts"]["test"] = "jest"
    with open(package_json_path, "w") as pf:
        json.dump(package_json, pf, indent=4)

    # Create rollup config
    h.open_stg_and_write_with(
        fin=res_path("rollup.config.js.stg"),
        fout="rollup.config.js",
        source_dir_path=src_dir,
        entry_file_name=entry_file_name,
        out_prefix=out_prefix,
    )
    entry_file_path = os.path.join(src_dir, entry_file_name)
    h.copy_resource("entry-file.js", entry_file_path)

    # tsconfig.json
    if ts_enabled:
        h.open_stg_and_write_with(
            fin=res_path("tsconfig.json.stg"),
            fout="tsconfig.json",
            source_dir_path=src_dir,
        )

    # Test directory
    if ts_enabled and tests_enabled:
        h.copy_resource("jest.config-ts.js", "jest.config.js")
        h.copy_resource("test-ts", "test")
    elif tests_enabled:
        h.copy_resource("test-js", "test")

    return True
