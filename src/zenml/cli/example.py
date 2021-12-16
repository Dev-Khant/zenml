#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
import shutil
from pathlib import Path
from typing import List, Dict

import click
from git.exc import GitCommandError, NoSuchPathError
from git.repo.base import Repo
from packaging.version import Version, parse

from zenml import __version__ as zenml_version_installed
from zenml.cli.cli import cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    pretty_print,
    title,
    warning,
)
from zenml.constants import APP_NAME, GIT_REPO_URL
from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)

EXAMPLES_GITHUB_REPO = "zenml_examples"


def is_example_installed_at_path(path: str) -> bool:
    """ Checks if the example is installed at the given path.

    Args:
        path: Root path to local examples
        example: Name of the example
    """
    return (fileio.file_exists(path)
            and fileio.is_dir(path))

class Example:
    """Class for all example objects."""

    def __init__(self, name: str, path_in_repo: Path) -> None:
        """Create a new Example instance.

        Args:
            name: The name of the example, specifically the name of the folder
                  on git
            path_in_repo: Path to the local example within the global zenml
                          folder.
        """
        self.name = name
        self.path_in_repo = path_in_repo

    @property
    def readme_content(self) -> str:
        """Returns the readme content associated with a particular example."""
        readme_file = os.path.join(self.path_in_repo, "README.md")
        try:
            with open(readme_file) as readme:
                readme_content = readme.read()
            return readme_content
        except FileNotFoundError:
            if fileio.file_exists(str(self.path_in_repo)) and fileio.is_dir(
                    str(self.path_in_repo)
            ):
                raise ValueError(f"No README.md file found in "
                                 f"{self.path_in_repo}")
            else:
                raise FileNotFoundError(
                    f"Example {self.name} is not one of the available options."
                    f"\nTo list all available examples, type: `zenml example "
                    f"list`"
                )

    def run(self) -> None:
        """Runs the example script.

        Raises:
            NotImplementedError: This method is not yet implemented."""
        # TODO [ENG-191]: Add an example-run command to run an example. (ENG-145)
        raise NotImplementedError("Functionality is not yet implemented.")


class ExamplesRepo:
    """Class for the examples repository object."""

    def __init__(self, cloning_path: Path) -> None:
        """Create a new ExamplesRepo instance."""
        self.cloning_path = cloning_path
        try:
            self.repo = Repo(self.cloning_path)
        except NoSuchPathError:
            self.repo = None  # type: ignore
            logger.debug(
                f"`cloning_path`: {self.cloning_path} was empty, "
                f"but ExamplesRepo was created. "
                "Ensure a pull is performed before doing any other operations."
            )

    @property
    def latest_release(self) -> str:
        """Returns the latest release for the examples repository."""
        tags = sorted(
            self.repo.tags, key=lambda t: t.commit.committed_datetime
            # type: ignore
        )
        latest_tag = parse(tags[-1].name)
        if type(latest_tag) is not Version:
            return "main"
        return tags[-1].name  # type: ignore

    @property
    def is_cloned(self) -> bool:
        """Returns whether we have already cloned the examples repository."""
        return self.cloning_path.exists()

    @property
    def examples_dir(self) -> str:
        """Returns the path for the examples directory."""
        return os.path.join(self.cloning_path, "examples")

    def clone(self) -> None:
        """Clones repo to cloning_path.

        If you break off the operation with a `KeyBoardInterrupt` before the
        cloning is completed, this method will delete whatever was partially
        downloaded from your system."""
        self.cloning_path.mkdir(parents=True, exist_ok=False)
        try:
            logger.info(f"Cloning repo {GIT_REPO_URL} to {self.cloning_path}")
            self.repo = Repo.clone_from(
                GIT_REPO_URL, self.cloning_path, branch="main"
            )
        except KeyboardInterrupt:
            self.delete()
            logger.error("Cancelled download of repository.. Rolled back.")

    def delete(self) -> None:
        """Delete `cloning_path` if it exists."""
        if self.cloning_path.exists():
            shutil.rmtree(self.cloning_path)
        else:
            raise AssertionError(
                f"Cannot delete the examples repository from "
                f"{self.cloning_path} as it does not exist."
            )

    def checkout(self, branch: str) -> None:
        """Checks out a specific branch or tag of the examples repository

        Raises:
            GitCommandError: if branch doesn't exist.
        """
        logger.info(f"Checking out branch: {branch}")
        self.repo.git.checkout(branch)

    def checkout_latest_release(self) -> None:
        """Checks out the latest release of the examples repository."""
        self.checkout(self.latest_release)


class GitExamplesHandler(object):
    """Class for the GitExamplesHandler that interfaces with the CLI tool."""

    def __init__(self) -> None:
        """Create a new GitExamplesHandler instance."""
        self.repo_dir = click.get_app_dir(APP_NAME)
        self.examples_dir = Path(os.path.join(self.repo_dir,
                                              EXAMPLES_GITHUB_REPO))
        self.examples_repo = ExamplesRepo(self.examples_dir)

    @property
    def examples(self) -> List[Example]:
        """Property that contains a list of examples"""
        return [
            Example(
                name, Path(os.path.join(self.examples_repo.examples_dir, name))
            )
            for name in sorted(os.listdir(self.examples_repo.examples_dir))
            if (
                    not name.startswith(".")
                    and not name.startswith("__")
                    and not name.startswith("README")
            )
        ]

    @property
    def is_installed(self) -> bool:
        return (fileio.file_exists(str(self.examples_dir))
                and fileio.is_dir(str(self.examples_dir)))

    def get_examples(self, example_name: str = None) -> List[Example]:
        """Method that allows you to get an example by name. If no example is
            supplied,  all examples are returned

            Args:
              example_name: Name of an example.
        """
        example_dict = {e.name: e for e in self.examples}
        if example_name:
            if example_name in example_dict.keys():
                return [example_dict[example_name]]
            else:
                raise KeyError(
                    f"Example {example_name} does not exist! "
                    f"Available examples: {[example_dict.keys()]}"
                )
        else:
            return self.examples

    def pull(self, version: str = "", force: bool = False) -> None:
        """Pulls the examples from the main git examples repository."""
        if version == "":
            version = self.examples_repo.latest_release

        if not self.examples_repo.is_cloned:
            self.examples_repo.clone()
        elif force:
            self.examples_repo.delete()
            self.examples_repo.clone()

        try:
            self.examples_repo.checkout(version)
        except GitCommandError:
            logger.warning(
                f"Version {version} does not exist in remote repository. "
                f"Reverting to `main`."
            )
            self.examples_repo.checkout("main")

    def pull_latest_examples(self) -> None:
        """Pulls the latest examples from the examples repository."""
        self.pull(version=self.examples_repo.latest_release, force=True)

    def copy_example(self, example: Example, destination_dir: str) -> None:
        """Copies an example to the destination_dir."""
        fileio.create_dir_if_not_exists(destination_dir)
        fileio.copy_dir(str(example.path_in_repo), destination_dir,
                        overwrite=True)

    def clean_current_examples(self) -> None:
        """Deletes the ZenML examples directory from your current working
        directory."""
        examples_directory = os.path.join(os.getcwd(), "zenml_examples")
        shutil.rmtree(examples_directory)


pass_git_examples_handler = click.make_pass_decorator(
    GitExamplesHandler, ensure=True
)


@cli.group(help="Access all ZenML examples.")
def example() -> None:
    """Examples group"""


@example.command(help="List the available examples.")
@pass_git_examples_handler
def list(git_examples_handler: GitExamplesHandler) -> None:
    """List all available examples."""
    declare("Listing examples: \n")

    for example in git_examples_handler.get_examples():
        declare(f"{example.name}")

    declare("\nTo pull the examples, type: ")
    declare("zenml example pull EXAMPLE_NAME")


@example.command(help="Deletes the ZenML examples directory.")
@pass_git_examples_handler
def clean(git_examples_handler: GitExamplesHandler) -> None:
    """Deletes the ZenML examples directory from your current working
    directory."""

    if (
            git_examples_handler.is_installed
            and
            confirmation("Do you wish to delete the ZenML"
                         " examples directory? \n "
                         f"{git_examples_handler.examples_dir}")
    ):
        git_examples_handler.clean_current_examples()
        declare(
            "ZenML examples directory was deleted from your current working "
            "directory."
        )
    elif not git_examples_handler.is_installed:
        logger.error(
            f"Unable to delete the ZenML examples directory - "
            f"{git_examples_handler.examples_dir} - "
            "as it was not found in your current working directory."
        )


@example.command(help="Find out more about an example.")
@pass_git_examples_handler
@click.argument("example_name")
def info(git_examples_handler: GitExamplesHandler, example_name: str) -> None:
    """Find out more about an example."""
    # TODO [ENG-148]: fix markdown formatting so that it looks nicer (not a
    #  pure .md dump)
    try:
        example_obj = git_examples_handler.get_examples(example_name)[0]

    except KeyError as e:
        error(str(e))

    else:
        title(example_obj.name)
        pretty_print(example_obj.readme_content)


@example.command(
    help="Pull examples straight into your current working directory."
)
@pass_git_examples_handler
@click.argument("example_name", required=False, default=None)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force the redownload of the examples folder to the ZenML config "
         "folder.",
)
@click.option(
    "--version",
    "-v",
    type=click.STRING,
    default=zenml_version_installed,
    help="The version of ZenML to use for the force-redownloaded examples.",
)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_examples",
    help="Relative path at which you want to install the example(s)"
)
def pull(
        git_examples_handler: GitExamplesHandler,
        example_name: str,
        force: bool,
        version: str,
        path: str
) -> None:
    """Pull examples straight into your current working directory.
    Add the flag --force or -f to redownload all the examples afresh.
    Use the flag --version or -v and the version number to specify
    which version of ZenML you wish to use for the examples."""
    git_examples_handler.pull(force=force, version=version)
    examples_dir = os.path.join(os.getcwd(), path)
    fileio.create_dir_if_not_exists(examples_dir)
    try:
        examples = git_examples_handler.get_examples(example_name)

    except KeyError as e:
        error(str(e))

    else:
        for example in examples:
            destination_dir = os.path.join(os.getcwd(), path, example.name)

            if is_example_installed_at_path(path=destination_dir):
                if confirmation(
                        f"Example {example.name} is already pulled. "
                        "Do you wish to overwrite the directory at "
                        f"{destination_dir}?"
                ):
                    fileio.rm_dir(destination_dir)
                else:
                    warning(f"Example {example.name} not overwritten.")
                    continue

            declare(f"Pulling example {example.name}...")

            fileio.create_dir_if_not_exists(destination_dir)
            git_examples_handler.copy_example(example, destination_dir)

            declare(f"Example pulled in directory: {destination_dir}")


@example.command(
    help="Run the example that you previously installed with "
         "`zenml example pull`"
)
@pass_git_examples_handler
@click.argument("example_name", required=True)
@click.option(
    "--path",
    "-p",
    type=click.STRING,
    default="zenml_examples",
    help="Relative path at which you want to install the example(s)"
)
def run(
        git_examples_handler: GitExamplesHandler,
        example_name: str,
        path: str
) -> None:
    examples_dir = Path(os.getcwd()) / path
    try:
        example = git_examples_handler.get_examples(example_name)[0]
    except KeyError as e:
        error(str(e))
    else:
        if not is_example_installed_at_path(path):
            error(f"Example {example_name} is not installed at {examples_dir})")
        else:
            example_dir = examples_dir / example.name

            os.chdir(example_dir)
            import subprocess
            subprocess.check_call(["./setup.sh"], cwd=example_dir)

            declare("Pipeline run finished. Feel free to edit the code at")

# from click.testing import CliRunner
#
# runner = CliRunner()
#
# result = runner.invoke(example, ["pull", "airflow_local", "-f"])
