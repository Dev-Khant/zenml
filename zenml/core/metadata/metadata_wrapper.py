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

from typing import Text, List, Dict

import pandas as pd
from ml_metadata.metadata_store import metadata_store
from ml_metadata.proto import metadata_store_pb2

from zenml.utils.enums import PipelineStatusTypes


class ZenMLMetadataStore:
    STORE_TYPE = None

    def __init__(self, **kwargs):
        pass

    @staticmethod
    def initiate_store_mysql(
            host: Text,
            port: int,
            database: Text,
            username: Text,
            password: Text
    ) -> metadata_store_pb2.ConnectionConfig:
        """Initiates the configuration of the store. :param host: The name or
        network address of the instance of MySQL to :param connect to.: :param
        port: The port MySQL is using to listen for connections. :param
        database: The name of the database to use. :param username: The MySQL
        login account being used. :param password: The password for the MySQL
        account being used.

        Args:
            host (Text):
            port (int):
            database (Text):
            username (Text):
            password (Text):

        Returns:
            the instance of the MD Store
        """
        config = metadata_store_pb2.ConnectionConfig(
            mysql=metadata_store_pb2.MySQLDatabaseConfig(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password))

        return metadata_store.MetadataStore(config)

    @staticmethod
    def initiate_store_sqlite(uri: Text):
        """Initiates the configuration of the store :param uri: path the the
        metadata store :return: the instance of the MD Store

        Args:
            uri (Text):
        """
        config = metadata_store_pb2.ConnectionConfig()
        config.sqlite.filename_uri = uri
        return metadata_store.MetadataStore(config)

    @classmethod
    def from_config(cls, config: Dict):
        """
        Converts ZenML config to ZenML Metadata Store.

        Args:
            config (dict): ZenML config block for metadata.
        """
        from zenml.core.metadata.metadata_wrapper_factory import \
            wrapper_factory
        store_type = config['type']
        args = config['args']
        class_ = wrapper_factory.get_single_metadata_wrapper(store_type)
        obj = class_(**args)
        return obj

    def to_config(self) -> Dict:
        """
        Converts from ZenML Metadata store back to config.
        """
        args_dict = self.__dict__.copy()
        args_dict.pop('store')  # TODO: [LOW] Again a hack
        return {
            'type': self.STORE_TYPE,
            'args': args_dict
        }

    def get_pipeline_status(self, pipeline_name: Text) -> Text:
        """
        Query metadata store to find status of pipeline.

        Args:
            pipeline_name (str): name of pipeline
        """
        components_status = self.get_components_status(pipeline_name)
        for status in components_status:
            if status != 'complete' or status != 'cached':
                return PipelineStatusTypes.Running.name
        return PipelineStatusTypes.Succeeded.name

    def get_components_status(self, pipeline_name: Text):
        pipeline_executions = self.get_pipeline_executions(pipeline_name)
        return {
            e.properties['component_id'].string_value: e.properties[
                'state'].string_value for e in
            pipeline_executions
        }

    def get_pipeline_executions(self, pipeline_name: Text):
        c = self.get_pipeline_context(pipeline_name)
        return self.store.get_executions_by_context(c.id)

    def get_pipeline_context(self, pipeline_name: Text):
        return self.store.get_context_by_type_and_name(
            type_name='pipeline',
            context_name=pipeline_name
        )

    def get_artifacts_by_component(self, pipeline_name: Text,
                                   component_name: Text):
        """
        Args:
            pipeline_name:
            component_name:
        """
        # First , you get the execution associated with the component
        e = self.get_component_execution(pipeline_name, component_name)

        # Second, you will get artifacts
        return self.get_artifacts_by_execution(e.id)

    def get_component_execution(self, pipeline_name: Text,
                                component_name: Text):
        pipeline_executions = self.get_pipeline_executions(pipeline_name)
        for e in pipeline_executions:
            # TODO: [LOW] Create a more refined way to find components.
            if component_name in e.properties['component_id'].string_value:
                return e

    def get_artifacts_by_execution(self, execution_id):
        # First get all the events for this execution
        """
        Args:
            execution_id:
        """
        events = self.store.get_events_by_execution_ids([execution_id])

        artifact_ids = []
        for e in events:
            # MAJOR Assumptions: 4 means its output channel
            if e.type == 4:
                artifact_ids.append(e.artifact_id)
                break

        if not artifact_ids:
            raise AssertionError("This execution has no output artifact.")

        # Get artifacts
        return self.store.get_artifacts_by_id(artifact_ids)

    def get_pipeline_contexts(self) -> List:
        """Gets list of pipeline contexts"""
        return self.store.get_contexts_by_type(type_name='pipeline')

    # old
    def get_run_context_by_comp_execution_id(self, comp_exec_id):
        """
        Args:
            comp_exec_id:
        """
        all_cs = self.store.get_contexts_by_execution(comp_exec_id)
        for c in all_cs:
            if 'run_id' in c.properties:
                return c

    def get_execution_ids_by_value(self, param, value):
        """
        Args:
            param:
            value:
        """
        if self.store:
            db_uri = 'mysql+pymysql://{user}:{password}@{host}/{db}'.format(
                user=self.username,
                password=self.password,
                host=self.host,
                db=self.database,
            )
            engine = create_engine(db_uri)
            with engine.connect() as con:
                query = """
                SELECT * FROM ExecutionProperty
                WHERE (name='{}' and string_value='{}')
                """.format(param, value)
                rs = con.execute(query)
                return [r.execution_id for r in rs]
        else:
            raise AssertionError("Metadata store does not exist.")

    # old stuff
    def visualize_contexts(self):
        """Creates a DataFrame of the available contexts :return:
        pd.DataFrame
        """
        context_df = pd.DataFrame(columns=['run_id',
                                           'pipeline_name',
                                           'context_name',
                                           'context_id'])
        for c in self.store.get_contexts():
            context_df.loc[c.id] = pd.Series({
                'context_id': c.id,
                'context_name': c.name,
                'run_id': c.properties['run_id'].string_value,
                'pipeline_name': c.properties['pipeline_name'].string_value})
        return context_df

    def get_executions_by_context(self, context: str):
        """
        Args:
            context (str):
        """
        context_id = self.store.get_context_by_type_and_name(
            type_name='run',
            context_name=context,
        ).id
        return self.store.get_executions_by_context(context_id)

    def list_registered_components(self):
        """returns a list of registered components :return: list"""
        executions = self.store.get_executions()
        component_list = list({e.properties['component_id'].string_value
                               for e in executions})
        return component_list

    def filter_executions_by_component(self, component):
        """
        Args:
            component:
        """
        assert component in self.list_registered_components()
        executions = self.store.get_executions()
        return [e for e in executions
                if e.properties['component_id'].string_value == component]

    def filter_executions_by_condition(self, condition):
        """
        Args:
            condition:
        """
        component = condition['component']
        property_name = condition['property_name']
        value = condition['value']

        executions = self.filter_executions_by_component(component)
        return [e for e in executions
                if e.properties[property_name].string_value == value]

    def map_execution_to_context(self, executions):
        """
        Args:
            executions:
        """
        return [self.store.get_contexts_by_execution(e.id)[0]
                for e in executions]

    def list_contexts_by_condition(self, condition):
        """
        Args:
            condition:
        """
        executions = self.filter_executions_by_condition(condition)
        contexts = self.map_execution_to_context(executions)
        return contexts

    # Got shit done

    def get_outcomes_in_context(self,
                                context: str = None,
                                output_components: List = None):
        """
        Args:
            context (str):
            output_components (List):
        """
        if output_components:
            output_ids = output_components
        else:
            output_ids = self.list_registered_components()

        context_id = self.store.get_context_by_type_and_name(
            type_name='run',
            context_name=context,
        ).id

        # Among all the executions in context, select the right component
        execs_in_context = self.store.get_executions_by_context(context_id)
        execs_components = {e.properties['component_id'].string_value: e.id
                            for e in execs_in_context
                            if e.properties['component_id'].string_value
                            in output_ids}

        result = {}
        # Get the corresponding event and extract the output artifact ids of it
        for component, exec_id in execs_components.items():
            events = self.store.get_events_by_execution_ids([exec_id])
            artifact_ids = [e.artifact_id for e in events if e.type == 4]
            result[component] = self.store.get_artifacts_by_id(artifact_ids)
        return result

    def get_outcomes(self,
                     contexts: List[Text] = None,
                     context_names: List[Text] = None,
                     output_components: List[Text] = None,
                     conditions: List[Dict] = None):

        """
        Args:
            contexts:
            context_names:
            output_components:
            conditions:
        """
        if bool(contexts) and bool(context_names):
            raise Exception("Cant define context id/names at the same time")

        if contexts:
            target_context_ids = [
                self.store.get_context_by_type_and_name(type_name='run',
                                                        context_name=c).id for
                c in contexts]
        elif context_names:
            target_contexts = self.store.get_contexts()
            target_context_ids = [c.id for c in target_contexts if
                                  c.name in context_names]
        else:
            target_contexts = self.store.get_contexts()
            target_context_ids = [c.id for c in target_contexts]

        if conditions:
            for cond in conditions:
                context_w_cond = self.list_contexts_by_condition(cond)
                context_w_cond_ids = [c.id for c in context_w_cond]
                target_context_ids = [c for c in target_context_ids
                                      if c in context_w_cond_ids]

        result = {}
        for c_id in target_context_ids:
            result[c_id] = self.get_outcomes_in_context(c_id,
                                                        output_components)

        return {k: self.extract_uris(v) for k, v in result.items()}

    def get_context_by_run_id(self, run_id):
        """
        Args:
            run_id:
        """
        contexts = self.store.get_contexts()
        for c in contexts:
            if c.properties['run_id'].string_value == run_id:
                return c.id

    def get_execution_by_component_type(self, context, component_id):
        """
        Args:
            context:
            component_id:
        """
        context_id = self.store.get_context_by_type_and_name(
            type_name='run',
            context_name=context,
        ).id
        execs = self.store.get_executions_by_context(context_id)
        for e in execs:
            full = e.properties['component_id'].string_value
            instance_name = full.split('.')[1]
            if instance_name == component_id:
                return e

    def is_component_cached(self, context, component_id):
        """
        Args:
            context:
            component_id:
        """
        context_id = self.store.get_context_by_type_and_name(
            type_name='run',
            context_name=context,
        ).id
        execs = self.store.get_executions_by_context(context_id)
        for e in execs:
            full = e.properties['component_id'].string_value
            instance_name = full.split('.')[1]
            if instance_name == component_id:
                if e.properties[
                    'state'].string_value == ExecutionStates.cached.name:
                    return True
                else:
                    return False
        return False

    def find_original_context_and_artifacts_from_exec(self, execution):
        """
        Args:
            execution:
        """
        events = self.store.get_events_by_execution_ids([execution.id])

        # get all the OUTPUT artifacts from these events
        artifacts_ids = []
        for e in events:
            if e.type == 4:
                artifacts_ids.append(e.artifact_id)

        if artifacts_ids:
            artifact_id = artifacts_ids[-1]  # lets take the last one

        # If cached
        if execution.properties[
            'state'].string_value == ExecutionStates.cached.name:
            new_events = self.store.get_events_by_artifact_ids([artifact_id])
            for e in new_events:
                if e.type == 4:
                    return self.find_original_context_and_artifacts_from_exec(
                        self.store.get_executions_by_id([e.execution_id])[0])
        else:
            # we got the relevant run
            # run_id = execution.properties['run_id'].string_value
            context = self.store.get_contexts_by_execution(execution.id)[
                0].name

            # we got the relevant artifacts
            artifacts = self.store.get_artifacts_by_id(artifacts_ids)

            # and we got the relevant execution
            return context, artifacts

    def find_original_context_and_artifacts_from_context(self,
                                                         context,
                                                         component_type):
        """
        Args:
            context:
            component_type:
        """
        execution = self.get_execution_by_component_type(
            context,
            component_type
        )
        return self.find_original_context_and_artifacts_from_exec(execution)

    def get_next_context_id(self):
        if self.store:
            db_uri = 'mysql+pymysql://{user}:{password}@{host}/{db}'.format(
                user=self.username,
                password=self.password,
                host=self.host,
                db=self.database,
            )
            engine = create_engine(db_uri)
            with engine.connect() as con:
                query = """
                SELECT AUTO_INCREMENT FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = '{}' AND TABLE_NAME = 'Context'
                """.format(self.database)
                rs = con.execute(query)
                for row in rs:
                    return row[0]
        else:
            raise AssertionError("Metadata store does not exist.")

    @staticmethod
    def extract_uris(result):
        """
        Args:
            result:
        """
        return {k: [a.uri for a in v] for k, v in result.items()}
