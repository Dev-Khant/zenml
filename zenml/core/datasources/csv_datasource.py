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
"""CSv Datasource definition"""

from typing import Text, Dict

from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.steps.data.csv_data_step import CSVDataStep
from zenml.utils import path_utils


class CSVDatasource(BaseDatasource):
    """ZenML CSV datasource definition.

    Use this for CSV training pipelines.
    """
    DATA_STEP = CSVDataStep

    def __init__(self, name: Text, path: Text, schema: Dict = None):
        """
        Create a CSV datasource. Creating this datasource creates a Beam
        pipeline that converts the CSV file into TFRecords for pipelines to
        use.

        The path can be a local path or a Google Cloud Storage bucket
        path for now (S3, Azure coming soon). The path defines the datasource,
        meaning a change in it (including file name) should be dealt with by
        creating another datasource.

        Args:
            name (str): name of datasource.
            path (str): path to csv file.
            schema (str): optional schema for data to conform to.
        """
        super().__init__(name, schema)
        self.path = path

        if not path_utils.file_exists(path):
            raise Exception(f'{path} does not exist!')
