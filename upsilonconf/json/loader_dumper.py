import json
from pathlib import Path
from typing import Any, Mapping


class JSONLoader:
    """The loader to read JSON files."""

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
            return json.load(f)


class JSONDumper:
    """The dumper to save JSON files."""

    def __init__(self, indent: int = 2, sort_keys: bool = False):
        """Initialize the `JSONDumper` class.

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
            "default": lambda o: o.__getstate__(),
            "indent": self._indent,
            "sort_keys": self._sort_keys,
        }

        with open(path, "w") as f:
            json.dump(conf, f, **kwargs)
