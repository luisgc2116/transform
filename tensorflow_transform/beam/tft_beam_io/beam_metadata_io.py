# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Transforms to read/write metadata from disk.

A write/read cycle will render all metadata deferred, but in general users
should avoid doing this anyway and pass around live metadata objects.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

import apache_beam as beam
from tensorflow_transform.beam import common
from tensorflow_transform.tf_metadata import metadata_io


class BeamDatasetMetadata(
    collections.namedtuple(
        'BeamDatasetMetadata',
        ['dataset_metadata', 'deferred_metadata'])):
  """A class like DatasetMetadata that also holds a dict of `PCollection`s.

  `deferred_metadata` is a PCollection containing a single DatasetMetadata.
  """

  @property
  def schema(self):
    return self.dataset_metadata.schema


class WriteMetadata(beam.PTransform):
  """A PTransform to write Metadata to disk.

  Input can either be a DatasetMetadata or a tuple of properties.

  Depending on the optional `write_to_unique_subdirectory`, writes the given
  metadata to either `path` or a new unique subdirectory under `path`.

  Returns a singleton with the path to which the metadata was written.
  """

  # NOTE: The pipeline metadata is required by PTransform given that all the
  # inputs may be non-deferred.
  def __init__(self, path, pipeline, write_to_unique_subdirectory=False):
    """Init method.

    Args:
      path: A str, the default path that the metadata should be written to.
      pipeline: A beam Pipeline.
      write_to_unique_subdirectory: (Optional) A bool indicating whether to
        write the metadata out to `path` or a unique subdirectory under `path`.
    """
    super(WriteMetadata, self).__init__()
    self._path = path
    self._write_to_unique_subdirectory = write_to_unique_subdirectory
    self.pipeline = pipeline

  def _extract_input_pvalues(self, metadata):
    pvalues = []
    if isinstance(metadata, BeamDatasetMetadata):
      pvalues.append(metadata.deferred_metadata)
    return metadata, pvalues

  def expand(self, metadata):
    if hasattr(metadata, 'deferred_metadata'):
      metadata_pcoll = metadata.deferred_metadata
    else:
      metadata_pcoll = self.pipeline | beam.Create([metadata])

    def write_metadata_output(metadata):
      output_path = self._path
      if self._write_to_unique_subdirectory:
        output_path = common.get_unique_temp_path(self._path)
      metadata_io.write_metadata(metadata, output_path)
      return output_path

    return metadata_pcoll | 'WriteMetadata' >> beam.Map(write_metadata_output)
