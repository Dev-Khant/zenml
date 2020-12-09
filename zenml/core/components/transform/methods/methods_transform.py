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

import tensorflow as tf


def one_hot_encode(custom_value):
    """
    Args:
        custom_value:
    """
    def apply(input_):
        return tf.one_hot(input_,
                          custom_value,
                          on_value=1, off_value=0,
                          axis=None,
                          dtype=None,
                          name=None)

    return apply


def image_reshape(image, height, width, num_channels):
    """
    Args:
        image:
        height:
        width:
        num_channels:
    """
    shape = [-1, height, width, num_channels]
    return tf.reshape(image, shape=shape)


def load_binary_image(image):
    """
    Args:
        image:
    """
    return tf.io.decode_image(image).numpy()
