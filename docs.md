# git+ YAML Documentation 

---

## **Overview**

This workflow allows you to execute complex Bash/Zsh commands, dynamically reference inputs and contexts, and create hierarchical command structures. It is highly customizable, supports dynamic reloading, and provides seamless integration with Git and other command-line utilities.

### **Core Features**
- **Shell Command Execution**: Supports Bash/Zsh commands directly in the YAML configuration.
- **Dynamic Placeholders**:
  - `[input]` and `[input_snake_case]` for user input.
  - `[parent]` and `[parent~n]` to reference parent commands in the hierarchy.
- **Reloading**: Refresh workflows dynamically using `[reload]` and `[reload~n]`.
- **Visual Customization**: Optional icons and subtitles for better UI experience.
- **Nested Commands**: Build complex workflows with subcommands referencing parent contexts.

---

## **Structure of a Command**

Each command is defined with the following structure:

### **Basic Fields**
| **Field**      | **Description**                                                                 |
|-----------------|---------------------------------------------------------------------------------|
| `title`        | The name of the command as displayed in Alfred.                                |
| `subtitle`     | (Optional) A short description of the command.                                            |
| `icon`         | (Optional) Path to an image for the command icon in Alfred.                   |
| `command`      | The shell command to execute. Supports dynamic placeholders.                  |
| `values` | (Optional) A list of items for the user to select from. When an item is selected, the command will be executed, with [input] in the command replaced by the selected value. If subcommands are present, the `command` will be ignored and the selected value can be referenced using [parent]. |
| `values_command` | (Optional) Treated the same as `values` but the values are generated from this bash command. Each new line is a different value. |
| `mods`         | (Optional) Modifier-specific actions (e.g., `cmd`, `alt`).                    |

### **Dynamic Placeholders**
| **Placeholder**     | **Description**                                                                                     |
|----------------------|-----------------------------------------------------------------------------------------------------|
| `[input]`           | User-provided input at runtime.                                                                     |
| `[input_snake_case]`| Same as `[input]`, but converted to `snake_case`.                                                   |
| `[parent]`          | Refers to the immediate parent command.                                                             |
| `[parent~n]`        | References `n` levels back in the parent hierarchy.                                                 |
| `[reload]`          | Reloads the workflow at the current context. Must be echoed to take effect.                         |
| `[reload~n]`        | Reloads the workflow `n` levels back in the hierarchy. Must be echoed to take effect.               |


### **Icons**
| **Preview**                                                                 | **Icon File Name**    | **Description**                 |
|-----------------------------------------------------------------------------|------------------------|----------------------------------|
| <img src="./icons/info.png" width="64" alt="info.png">                      | `info.png`            | Represents information or details. |
| <img src="./icons/down.small.png" width="64" alt="down.small.png">          | `down.small.png`      | Indicates a small downward action. |
| <img src="./icons/icon.png" width="64" alt="icon.png">                      | `icon.png`            | The default icon for commands.  |
| <img src="./icons/action.png" width="64" alt="action.png">                  | `action.png`          | Represents an actionable item.  |
| <img src="./icons/rebase.png" width="64" alt="rebase.png">                  | `rebase.png`          | Used for Git rebase actions.    |
| <img src="./icons/tag.png" width="64" alt="tag.png">                        | `tag.png`             | Represents Git tags or labels.  |
| <img src="./icons/down.big.png" width="64" alt="down.big.png">              | `down.big.png`        | Indicates a large downward action. |
| <img src="./icons/create.png" width="64" alt="create.png">                  | `create.png`          | Represents creation of new items. |
| <img src="./icons/pick.png" width="64" alt="pick.png">                      | `pick.png`            | Represents selection or picking. |
| <img src="./icons/list.png" width="64" alt="list.png">                      | `list.png`            | Represents a list or multiple items. |
| <img src="./icons/search.png" width="64" alt="search.png">                  | `search.png`          | Represents a search or lookup action. |
| <img src="./icons/folder.png" width="64" alt="folder.png">                  | `folder.png`          | Represents a folder or directory. |
| <img src="./icons/globe.png" width="64" alt="globe.png">                    | `globe.png`           | Represents internet or global scope. |
| <img src="./icons/pencil.png" width="64" alt="pencil.png">                  | `pencil.png`          | Represents editing or writing.  |
| <img src="./icons/open.png" width="64" alt="open.png">                      | `open.png`            | Represents opening a file or folder. |
| <img src="./icons/trash.png" width="64" alt="trash.png">                    | `trash.png`           | Represents deletion or removal. |
| <img src="./icons/up.big.png" width="64" alt="up.big.png">                  | `up.big.png`          | Indicates a large upward action. |
| <img src="./icons/fork.png" width="64" alt="fork.png">                      | `fork.png`            | Represents branching or forking. |
| <img src="./icons/copy.png" width="64" alt="copy.png">                      | `copy.png`            | Represents copying or duplication. |


---

## **Examples**

### **Simple Commands**

#### **1. Print Input to Console**
```yaml
- title: print
  subtitle: Echo user input
  command: echo "You entered: [input]"
```
- **Description**: Echoes the user-provided input to the console.
- **Usage**: Type input in Alfred and execute the command.

---

#### **2. Create a New Git Branch**
```yaml
- title: create-branch
  subtitle: Create a new Git branch
  command: |
    git checkout -b "[input_snake_case]"
```
- **Description**: Creates a new Git branch using the user-provided input, formatted as `snake_case`.

---

### **Intermediate Commands**

#### **1. Count Modified Git Files**
```yaml
- title: modified-files
  subtitle_command: |
    modified=$(git diff --name-only | wc -l | xargs)
    echo "$modified file(s) modified"
  command: |
    modified=$(git diff --name-only | wc -l | xargs)
    if [ "$modified" -gt 0 ]; then
        echo "[reload]"
    else
        echo "No changes to reload"
    fi
```
- **Description**: Counts the number of modified files in the current Git repository and reloads the workflow if any changes are found.

---

#### **2. Switch Git Branch**
```yaml
- title: switch-branch
  subtitle: Switch to a branch
  values_command: git branch --format='%(refname:short)'
  command: |
    git checkout "[input]"
    echo "[reload~1]"
```
- **Description**: Lists all branches, switches to the selected branch, and reloads the parent workflow.

---

### **Advanced Commands**

#### **1. Nested Subcommands with Parent Context**
```yaml
- title: git-operations
  subtitle: Perform Git operations
  values_command: |
    echo "commit"
    echo "push"
    echo "pull"
  command: echo "Selected: [input]"

- title: commit
  parent: git-operations
  command: |
    git commit -m "[parent~1]: [input]"
    echo "Committed changes with message: [input]"
    echo "[reload]"
```
- **Description**:
  - The main `git-operations` command provides options (`commit`, `push`, `pull`).
  - Selecting `commit` allows the user to add a commit message, referencing the parent context for clarity.

---

#### **2. Interactive Git Stash Management**
```yaml
- title: stash-operations
  subtitle: Manage Git stashes
  values_command: git stash list --pretty=format:"%s"
  command: |
    git stash pop "$(git stash list --pretty=format:'%H' | sed -n [input])"
    echo "Popped stash: [input]"
    echo "[reload]"
```
- **Description**:
  - Dynamically lists all Git stashes.
  - Pops the selected stash and reloads the workflow.

---

#### **3. Dynamic Reload Based on Command State**
```yaml
- title: add-modified-files
  subtitle: Stage modified files
  command: |
    modified=$(git diff --name-only | wc -l | xargs)
    git add "[input]"
    if [ "$modified" -eq 1 ]; then
        echo "[reload~1]"
    else
        echo "[reload]"
    fi
  values_command: git diff --name-only
```
- **Description**: 
  - Adds a selected modified file to the staging area.
  - Reloads based on whether multiple files are staged or just one.

---

### **Modifiers (`mods`)**

#### **Example with Modifiers**
```yaml
- title: git-status
  subtitle: View Git status
  command: git status
  mods:
    cmd:
      subtitle: Open file in editor
      command: code "[input]"
    alt:
      subtitle: Discard changes
      command: git checkout -- "[input]"
```
- **Description**:
  - Default action: View Git status.
  - `cmd` modifier: Open the file in VS Code.
  - `alt` modifier: Discard changes in the selected file.

---

## **Best Practices**

1. **Use `[reload]` Wisely**:
   - Reloads ensure the workflow stays up-to-date but can add overhead if overused.

2. **Leverage `values` and `values_command`**:
   - Use it for populating lists (e.g., build script commands, Git branches, files, etc.).

3. **Optimize Hierarchical References**:
   - Utilize `[parent~n]` to reference previous command titles in your bash command.

4. **Combine with Scripts**:
   - Offload complex logic to standalone scripts and call them within `command`.
