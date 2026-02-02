# Just Streets T.3.4
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

This is the source code for the objective safety analysis for [Just Streets](https://www.just-streets.eu/), WP 3.4 by [Clément Sebastiao](https://orcid.org/0009-0009-3084-0071) and [Michael Szell](https://orcid.org/0000-0003-3022-2483).


## Installation
First clone the repository:

```
git clone https://github.com/csebastiao/JS_crashes
```

Go to the cloned folder and create a new virtual environment. You can either create a new virtual environment then install the necessary dependencies with `pip` using the `requirements.txt` file:

```
pip install -r requirements.txt
```

Or create a new environment with the dependencies with `conda` or `mamba` using the `environment.yml` file:

```
mamba env create -f environment.yml
```
Then, install the virtual environment's kernel in Jupyter:

```
mamba activate JS_crashes
ipython kernel install --user --name=JS_crashes
mamba deactivate
```

You can now run `jupyter lab` with kernel `JS_crashes` (Kernel > Change Kernel > JS_crashes).

## Repository structure

```
├── data
│   ├── processed           <- Modified data
│   └── raw                 <- Original, immutable data
├── notebooks               <- Jupyter notebooks
├── plots                   <- Generated figures
├── scripts                 <- Scripts to execute
├── .gitignore              <- Files and folders ignored by git
├── .pre-commit-config.yaml <- Pre-commit hooks used
├── CITATION.cff            <- Citation file (template)
├── README.md
├── TEMPLATE.md             <- Explanation for the template, delete it after use
├── environment.yml         <- Environment file to set up the environment using conda/mamba
└── requirements.txt        <- Requirements file to set up the environment using pip
```

## Credits


Development of Just Streets was supported by the European Union [Grant Agreement ID: 101104240](https://cordis.europa.eu/project/id/101104240)


