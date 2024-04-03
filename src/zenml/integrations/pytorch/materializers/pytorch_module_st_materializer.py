#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of the PyTorch Module materializer using Safetensors."""

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

try:
    from safetensors.torch import save_file
except ImportError:
    raise ImportError(
        "You are using `PytorchMaterializer` with safetensors.",
        "You can install `safetensors` by running `pip install safetensors`.",
    )

from torch.nn import Module

from zenml.enums import ArtifactType
from zenml.integrations.pytorch.materializers.base_pytorch_st_materializer import (
    BasePyTorchSTMaterializer,
)
from zenml.integrations.pytorch.utils import count_module_params

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "entire_model.safetensors"
CHECKPOINT_FILENAME = "checkpoint.safetensors"


class PyTorchModuleSTMaterializer(BasePyTorchSTMaterializer):
    """Materializer to read/write Pytorch models.

    Inspired by the guide:
    https://pytorch.org/tutorials/beginner/saving_loading_models.html
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Module,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    FILENAME: ClassVar[str] = DEFAULT_FILENAME

    def save(self, model: Module) -> None:
        """Writes a PyTorch model, as a model and a checkpoint.

        Args:
            model: A torch.nn.Module or a dict to pass into model.save
        """
        # Save entire model to artifact directory, This is the default behavior
        # for loading model in development phase (training, evaluation)
        super().save(model)

        # Also save model checkpoint to artifact directory,
        # This is the default behavior for loading model in production phase (inference)
        if isinstance(model, Module):
            filename = os.path.join(self.uri, CHECKPOINT_FILENAME)
            save_file(model.state_dict(), filename)

    def extract_metadata(self, model: Module) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Model` object.

        Args:
            model: The `Model` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {**count_module_params(model)}
