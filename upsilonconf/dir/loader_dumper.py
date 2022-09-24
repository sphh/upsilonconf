from pathlib import Path
from typing import Any, Mapping

from ..config import Configuration


DEFAULT_GLOB = "config.*"
DEFAULT_NAME = "config.json"


class DirLoader:
    """Read configuration files from a directory."""

    def __init__(self, loader, glob: str = None):
        """
        Initialize the `DirDumper` class.

        Parameters
        ----------
        dumper : IDumper
            The dumper to be used to write the config file.
        glob : str, optional
            The globbing pattern to use to find the config files.
        """
        self._loader = loader
        self._glob = glob or DEFAULT_GLOB

    def load(self, path: Path) -> Mapping[str, Any]:
        """
        Read config from a directory.

        A config directory can hold any combination of the following three
        elements:
         1. The base configuration file with the name `config` (e.g.
            `config.json`)
         2. Config files/directories with sub-configs to be added to the base
            config.
            These sub-configs are directly added to the base config.
            The filename of this sub-config will be a new(!) key in the base
            config.
         3. Config files/directories with config options for the base config.
            These sub-configs provide one or more sub-config options
            for an existing(!) key in the base config.
            Therefore, the filename must match one of the keys in the base
            config.

        Parameters
        ----------
        path : Path
            Path to a readable directory with one or more configuration files.

        Returns
        -------
        config : Mapping
            The configuration represented by the directory at the given path.
        """
        try:
            base_path = next(path.glob(self._glob))
            base_conf = self._loader.load(base_path)
        except StopIteration:
            base_path = None
            base_conf = Configuration()

        for sub in path.iterdir():
            if sub == base_path:
                continue

            key, sub_conf = sub.stem, self._loader.load(sub)
            if key in base_conf:
                option = base_conf.pop(key)
                try:
                    sub_conf = sub_conf[option]
                except (KeyError, TypeError):
                    raise ValueError(
                        f"value corresponding to '{key}' in the base config "
                        f"does not match any of the options in '{sub.name}'"
                    )

            base_conf[key] = sub_conf

        return base_conf


class DirDumper:
    """Save configuration to a directory."""

    def __init__(self, dumper, name: str = None):
        """
        Initialize the `DirDumper` class.

        Parameters
        ----------
        dumper : IDumper
            The dumper to be used to write the config file.
        name : str, optional
            The filename to use for the output config file.
        """
        self._dumper = dumper
        self._name = name or DEFAULT_NAME

    def dump(self, conf: Mapping[str, Any], path: Path) -> None:
        """
        Write config to a directory.

        Parameters
        ----------
        conf : Mapping
            The configuration object to save.
        path : Path
            Path to a writeable directory.
        """
        path.mkdir(exist_ok=True)
        self._dumper.save(conf, path / self._name)
