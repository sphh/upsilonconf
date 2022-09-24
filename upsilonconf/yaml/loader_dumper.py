import re
import yaml
from pathlib import Path
from collections.abc import Mapping as ABCMapping
from typing import Any, Mapping


# Modify `SafeLoader`
# FIXME: Is this modification still needed?
_yaml_float_tag = "tag:yaml.org,2002:float"
_missing_yaml_floats = r"""^[-+]?(
    [0-9][0-9_]*\.[0-9_]*(?:[eE][0-9]+)?
   |\.[0-9][0-9_]*(?:[eE][0-9]+)?
   |[0-9][0-9_]*[eE][-+]?[0-9]+
)$"""
yaml.SafeLoader.add_implicit_resolver(
    _yaml_float_tag,
    re.compile(_missing_yaml_floats, re.X),
    list("-+0123456789."),
)

# Modify `SafeDumper`
yaml.SafeDumper.add_multi_representer(ABCMapping, yaml.SafeDumper.represent_dict)


class YAMLLoader:
    """The loader to read YAML files."""

    def load(self, path: Path) -> Mapping[str, Any]:
        """
        Read config from a JSON file.

        Parameters
        ----------
        path : Path
            Path to a readable JSON file.

        Returns
        -------
        config: Mapping
            A mapping constructed from the data in the file.
        """
        with open(path, "r") as f:
            return yaml.load(f, Loader=yaml.SafeLoader)


class YAMLDumper:
    """The dumper to save YAML files."""

    def __init__(self, indent: int = 2, sort_keys: bool = False):
        """Initialize the `YAMLDumper` class.

        Parameters
        ----------
        indent : int, optional
            The number of spaces to use for indentation in the output file.
        sort_keys : bool, optional
            Whether keys should be sorted before writing to the output file.
        """
        self._indent = indent
        self._sort_keys = sort_keys

    def save(self, conf: Mapping[str, Any], path: Path) -> None:
        """
        Write config to a JSON file.

        Parameters
        ----------
        conf : Mapping
            The configuration object to save.
        path : Path
            Path to a writeable JSON file.
        """
        kwargs = {
            "indent": self._indent,
            "sort_keys": self._sort_keys,
        }

        with open(path, "w") as f:
            yaml.dump(conf, f, Dumper=yaml.SafeDumper, **kwargs)
