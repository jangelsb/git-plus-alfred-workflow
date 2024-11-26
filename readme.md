# git+ for Alfred

A highly customizable Git interface for Alfred, allowing you to create personalized commands and menus to streamline your workflow.

For detailed documentation, see [docs.md](docs.md).

---

## 🚀 Features

### Search your repos 
![Filter Projects](images/filter_projects.png)

### Run commands in your repos
![Run Commands](images/commands.png)

### Switch branches 
![Checkout Branch](images/checkout_branch.png)

### Create new branches
![Create Branch](images/create_branch.png)

### Customize until your heart's content 
![Custom Commands](images/custom_commands.png)

---

## 📖 Usage

All commands in this workflow are defined in a YAML configuration file. See [actions.yaml](actions.yaml) for an example.

### Step 1: Set up your repos
```yaml
- title: Repo 1
  path: $repo_path1

- title: Repo 2
  path: "/path/to/repo2"
  actions_path: /path/to/actions.yaml

```
#### NOTE
* `actions_path` is an optional path to an actions.yaml that is only for that repo. The working directory for that path is the repo's directory.
* If you set a “bash profile”, you can use enviroment variables for your paths, e.g, `$REPO_PATH`


### Step 2 (Optional)
1. **Use the default configuration:** The included [actions.yaml](actions.yaml) contains a set of pre-defined commands.  

2. **Create a personalized config file:**
   - Copy the [actions.yaml](actions.yaml) file to a directory on your computer.
   - Reference your copy in the workflow configuration to prevent it from being overwritten during updates.
   - Periodically check [actions.yaml](actions.yaml) for new features or updates.

3. **Add your own commands:**
   - Modify the inline YAML or include an additional YAML file in your configuration.
   - Define repository-specific YAML files for commands unique to certain repos, see `actions_path` in Step 1.

---

## 📂 Configuration Example

Here’s a quick example of what a YAML configuration might look like:  

```yaml
- title: fetch
  icon: down.small.png
  command: |
    git fetch -p


- title: create
  icon: create.png
  command: |
    git checkout -b "[input_snake_case]"
```

For more information, see [docs.md](docs.md).

---

## 🛠️ Installation

1. Download [the latest workflow](https://github.com/jangelsb/git-plus-alfred-workflow/releases) and import it into Alfred.  
2. Configure the paths in the workflow settings.
3. Enjoy & God bless 

---

## 📃 Documentation

See [docs.md](docs.md) for full documentation, including advanced features and examples.
