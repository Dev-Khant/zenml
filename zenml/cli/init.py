#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Text, Dict

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation
from zenml.core.repo.repo import Repository


@cli.command()
@click.option('--repo_path', type=click.Path(exists=True))
@click.option('--artifact_store_path', type=click.Path(exists=True))
@click.option('--metadata_dict', type=dict)
@click.option('--pipelines_dir', type=click.Path(exists=True))
@click.option('--analytics_opt_in', '-a', type=click.BOOL)
def init(repo_path: Text, artifact_store_path: Text = None,
         metadata_dict: Dict = None, pipelines_dir: Text = None,
         analytics_opt_in: bool = None):
    """Initialize ZenML on given path."""
    if repo_path is None:
        repo_path = os.getcwd()

    if analytics_opt_in is None:
        analytics_opt_in = confirmation(
            "ZenML collects anonymized usage information. This data helps us "
            "create a better product and understand the needs of the "
            "community better. You can find more information about exactly "
            "what information we collect on: . "
            "Would you like to opt-in to usage analytics?")

    metadata_store = None
    Repository.init_repo(
        repo_path,
        artifact_store_path,
        metadata_store,
        pipelines_dir,
        analytics_opt_in,
    )
    click.echo(f'ZenML repo initialized at {repo_path}')
