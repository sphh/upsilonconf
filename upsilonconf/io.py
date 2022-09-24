from pathlib import Path
from typing import Union, Any, Mapping

from .config import Configuration


__all__ = ["load", "save"]


def __replace_in_keys(
    mapping: Union[Mapping[str, Any], Any], s: str, r: str
) -> Union[Mapping[str, Any], Any]:
    """
    Take a mapping object and replace all occurrencies of `s` with `r` in any
    of its keys.

    This function is called recursively.

    Modelled after the Stack Overflow answer by Farhan Haider:
    https://stackoverflow.com/questions/21650850/pyyaml-replace-dash-in-keys-with-underscore#answer-55986782

    Parameters
    ----------
    mapping : Mapping
        The mapping object to be modified.
    s : str
        The string to be replaced in the keys.
    r : str
        The replacement string.

    Returns
    -------
        The dictionary with all strings `s` replaced with `r` in the keys.
    """
    # Traverse all the keys and replace `s` with `r`
    dictionary = {}
    for key, value in mapping.items():
        try:
            # Call this method recursively
            value = __replace_in_keys(value, s, r)
        except AttributeError:
            # `value` is not of the mapping type
            pass
        dictionary[key.replace(s, r)] = value

    return dictionary


def _replace_in_keys(
    config: Mapping[str, Any], key_modifiers: Mapping[str, str]
) -> Mapping[str, Any]:
    """
    Replace strings in the keys of a mapping object.

    Parameters
    ----------
    config : Mapping
        The configuration object (or dictionary) to be modified.
    key_modifiers : dict
        The dictionary with the replacements.

    Returns
    -------
    dict
        A dictionary with the modified keys.

    """
    _config = config
    # Replace longest strings first
    # - `sorted(..., reverse=True)` takes care of that
    for key in sorted(key_modifiers.keys(), key=lambda k: len(k), reverse=True):
        _config = __replace_in_keys(_config, key, key_modifiers[key])
    return _config


def load(
    path: Union[Path, str], loader, key_modifiers: Mapping[str, str] = {}
) -> Configuration:
    """
    Read configuration from a file or directory.

    Parameters
    ----------
    path : Path or str
        Path to a readable file.
    key_modifiers : dict, optional
        A dictionary with replacement strings: The configuration keys will be
        modified, by replacing the string from the key_modifiers key with its
        value.

    Returns
    -------
    config : Configuration
        A configuration object with the values as provided in the file.
    """
    path = Path(path).expanduser().resolve()
    config = _replace_in_keys(loader.load(path), key_modifiers)
    return Configuration(**config)


def save(
    config: Mapping[str, Any],
    path: Union[Path, str],
    dumper,
    key_modifiers: Mapping[str, str] = {},
) -> None:
    """
    Write configuration to a file or directory.

    Parameters
    ----------
    config : Mapping
        The configuration object to save.
    path : Path or str
        Path to a writeable file.
    key_modifiers : dict, optional
        A dictionary with replacement strings: The configuration keys will be
        modified, by replacing the string from the key_modifiers key with its
        value.
    """
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(exist_ok=True, parents=True)
    config = _replace_in_keys(config, key_modifiers)
    return dumper.save(config, path)
