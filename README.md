# codetemplate

Software project template manager. Allows to create, search, and utilize
project templates. Custom templates are Python scripts or simple directories.
You can create your own templates in the user-local `~/.config/codetemplate/templates`
directory. For examples of how project templates are configured, look into the
[built-in templates](./templates) directory.

## Usage

Find all available js-related templates installed:

```bash
codetemplate search js
```

Create new project at "./new-proj" using template "rollup-lib". This will then
ask for your input on certain parameters.

```bash
codetemplate new rollup-lib new-proj
```
