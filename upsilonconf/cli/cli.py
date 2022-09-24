import argparse
import json
import pathlib
from typing import Any, Sequence, Mapping, overload, Tuple

from ..config import Configuration


def assignment_expr(s: str) -> Tuple[str, Any]:
    """Parse assignment expression argument."""
    key, val = s.split("=", maxsplit=1)
    try:
        val = json.loads(val)
    except json.JSONDecodeError:
        pass

    return key, val


class CLI:
    """Inject configuration group into an argument parser."""

    def __init__(self, loaders: Mapping[str, Any] = None):
        """
        Initialize the `CLI` class.

        Parameters
        ----------
        loaders : mapping, optional
            A dictionary with the supported configuration file suffixes as keys
            and their corresponding file loaders.
            If not specified, no configuration files are supported!
        """
        self._loaders = loaders or {}

    @overload
    def from_cli(self) -> Configuration:
        ...

    @overload
    def from_cli(selfargs: Sequence[str]) -> Configuration:
        ...

    @overload
    def from_cli(
        self, args: Sequence[str], parser: argparse.ArgumentParser
    ) -> Tuple[Configuration, argparse.Namespace]:
        ...

    def from_cli(
        self, args: Sequence[str] = None, parser: argparse.ArgumentParser = None
    ):
        """
        Construct a configuration from a Command Line Interface.

        This function adds a `configuration` group to an argument parser
        and adds two extra options to the parser: `overrides` and `--config`.
        The `--config` flag allows to specify a config file to read a basic
        config from. The appropriate loader will be found from the file's
        suffix and can be set with
        `CLI(loaders={'.json': JSONLoader(), '.yaml': YAMLLoader()})`. An usage
        message is printed, if the suffix cannot be found.
        The `overrides` option allows to specify one or more key value pairs
        that will overwrite any config values from the specified config file.
        If no loaders were specified, the `--config` argument will not be
        available (but the `overrides` can still be used.)

        Parameters
        ----------
        args : sequence of str, optional
            The list of arguments to parse.
            If not specified, they are taken from `sys.argv`.
        parser : argparse.ArgumentParser, optional
            The CLI parser to use as a base for retrieving configuration
            options.
            The parser can not (already) expect a variable number of positional
            args.
            Moreover, the parser should not already use the names `config` or
            `overrides`.
            If not specified, an empty parser will be created.

        Returns
        -------
        config : Configuration
            The configuration as specified by the command line arguments.
        ns : argparse.Namespace
            The namespace with additional arguments from the command line
            arguments.
        """
        _parser = argparse.ArgumentParser() if parser is None else parser

        group = _parser.add_argument_group("configuration")
        if self._loaders:
            group.add_argument(
                "--config",
                type=pathlib.Path,
                help="path to configuration file",
                metavar="FILE",
                dest="config",
            )
        group.add_argument(
            "overrides",
            nargs="*",
            type=assignment_expr,
            help="configuration options to override in the config file",
            metavar="KEY=VALUE",
        )

        # Load configuration file
        ns = _parser.parse_args(args)
        if ns.config is None:
            config = Configuration()
        else:
            try:
                loader = self._loaders[ns.config.suffix]
            except KeyError:
                # Print error and exit
                argparse.error(
                    f"Configuration file format '{ns.config.suffix}' not supported. "
                    f"Supported file formats are: {', '.join(self._loaders)}"
                )
            config = loader.load(ns.config)

        # Update with override values
        config.overwrite_all(ns.overrides)

        if parser is None:
            return config

        del ns.config
        del ns.overrides
        return config, ns
