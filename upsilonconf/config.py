import copy
from pathlib import Path
from typing import MutableMapping, Any, Iterator, Iterable, Union, Tuple, Dict, Mapping

__all__ = ["Configuration", "InvalidKeyError"]

_MappingLike = Union[Mapping[str, Any], Iterable[Tuple[str, Any]]]


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


class InvalidKeyError(ValueError):
    """Raised when a key can not be used in a configuration object."""

    pass


class Configuration(MutableMapping[str, Any]):
    """
    Configuration mapping (variable) names to their corresponding values.

    A `Configuration` should provide a convenient way to store
    (hyper-)parameters for your code and/or experiments.
    Any configuration value that represents a mapping is also automagically
    converted to a `Configuration` to build arbitrary config hierarchies.

    This class provides an interface that is similar to that of a dictionary.
    Additionally, it allows to access parameters as attributes.
    This means that you can simply use attribute syntax,
    instead of writing brackets and strings everywhere.
    To allow easy access to values in sub-configurations,
    sequences of indices can be used instead of chained indexing.
    Similarly, a string with parameter names separated by dots
    will be automagically split in a tuple index for easy access.

    Additional parameter values can be added to the mapping as needed.
    However, to avoid unwanted changes to configuration values,
    it is not possible to directly set the value for existing parameters.
    If you deliberately wish to set the value for existing parameters,
    you should use the `overwrite` method instead.

    Methods
    -------
    overwrite(key, value)
        Explicitly overwrite an existing parameter value in the configuration.
    overwrite_all(m, **kwargs)
        Explicitly overwrite multiple existing parameter values in the configuration.

    Examples
    --------
    >>> conf = Configuration(foo=0, bar="bar", baz={'a': 1, 'b': 2})
    >>> print(conf)
    {foo: 0, bar: bar, baz: {a: 1, b: 2}}
    >>> conf['bar']
    'bar'
    >>> conf['baz']['a']
    1

    Values can also be accessed as attributes, tuples or a string with dots

    >>> conf.bar
    'bar'
    >>> conf.baz.a
    1
    >>> conf['baz', 'a']
    1
    >>> conf['baz.a']
    1

    Values for new parameters can be added directly.
    To avoid inadvertadly overwriting values, the `overwrite` method must be used.

    >>> conf.new = "works"
    >>> conf['new'] = "won't work"
    Traceback (most recent call last):
        ...
    ValueError: key 'new' already defined, use 'overwrite' methods instead
    >>> conf.overwrite('new', "will work")
    'works'
    >>> conf.new
    'will work'
    """

    def __init__(self, **kwargs):
        self._content: MutableMapping[str, Any] = {}

        for k, v in kwargs.items():
            self.__setitem__(k, v)

    def __repr__(self) -> str:
        kwargs = ["=".join([k, "{!r}".format(v)]) for k, v in self.items()]
        return f"{self.__class__.__name__}({', '.join(kwargs)})"

    def __str__(self) -> str:
        kwargs = [": ".join([k, "{!s}".format(v)]) for k, v in self.items()]
        return f"{{{', '.join(kwargs)}}}"

    def __getstate__(self) -> Dict[str, Any]:
        return {k: v for k, v in self.items()}

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__init__(**state)

    def __copy__(self):
        return Configuration(**self)

    def __deepcopy__(self, memo: Dict = None):
        if memo is None:
            memo = {}

        result = Configuration()
        for k, v in self.items():
            result[k] = copy.deepcopy(v, memo=memo)

        return result

    # # # Mapping Interface # # #

    def __getitem__(self, key: Union[str, Iterable[str]]) -> Any:
        conf, key = self._resolve_key(key)
        return conf._content.__getitem__(key)

    def __setitem__(self, key: Union[str, Iterable[str]], value: Any) -> None:
        conf, key = self._resolve_key(key, create=True)
        conf._validate_key(key)
        if key in conf._content:
            msg = f"key '{key}' already defined, use 'overwrite' methods instead"
            raise ValueError(msg)

        try:
            value = Configuration(**value)
        except TypeError:
            pass

        return conf._content.__setitem__(key, value)

    def __delitem__(self, key: Union[str, Iterable[str]]) -> None:
        conf, key = self._resolve_key(key)
        return conf._content.__delitem__(key)

    def __len__(self) -> int:
        return self._content.__len__()

    def __iter__(self) -> Iterator[Any]:
        return self._content.__iter__()

    # # # Merging # # #

    def __or__(self, other: Mapping[str, Any]):
        result = Configuration(**self)
        result.update(other)
        return result

    def __ror__(self, other: Mapping[str, Any]):
        result = Configuration(**other)
        result.update(self)
        return result

    def __ior__(self, other: Mapping[str, Any]):
        self.update(**other)
        return self

    # # # Attribute Access # # #

    def __getattr__(self, name: str) -> Any:
        try:
            self._validate_key(name)
            return self.__getitem__(name)
        except InvalidKeyError:
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from None
        except KeyError:
            raise AttributeError(f"no config entry with key '{name}'") from None

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            self._validate_key(name)
            self.__setitem__(name, value)
        except InvalidKeyError:
            super().__setattr__(name, value)
        except ValueError as e:
            raise AttributeError(f"config entry with key " + str(e)) from None

    def __delattr__(self, name: str) -> None:
        try:
            self._validate_key(name)
            self.__delitem__(name)
        except InvalidKeyError:
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from None
        except KeyError:
            raise AttributeError(f"no config entry with key '{name}'") from None

    def __dir__(self) -> Iterable[str]:
        yield from super().__dir__()
        yield from self._content

    # # # Other Stuff # # #

    def _validate_key(self, key: str) -> True:
        """
        Check if a key respects a set of simple rules.

        Raises
        ------
        InvalidKeyError
            If the key does not respect the rules.
        """
        if len(key) == 0 or not key[0].isalpha():
            raise InvalidKeyError(f"'{key}' does not start with a letter")
        if not key.isidentifier():
            raise InvalidKeyError(f"'{key}' contains symbols that are not allowed")
        if key in super().__dir__():
            raise InvalidKeyError(f"'{key}' is not allowed as key, it is special")

        return True

    def _resolve_key(
        self, keys: Union[str, Iterable[str]], create: bool = False
    ) -> Tuple["Configuration", str]:
        """
        Resolve dot-string and iterable keys

        Parameters
        ----------
        keys : str or iterable of str
            The key(s) to be resolved.
        create : bool, optional
            If `True`, non-existent sub-configurations will be created.

        Returns
        -------
        config: Configuration
            The sub-configuration that should host the final key (and value).
        key : str
            The final key that should correspond to the actual value.

        Raises
        ------
        KeyError
            If any of the sub-keys (apart from the final key)
            point to a value that is not a configuration.
        """
        try:
            *parents, final = keys.split(".")
        except AttributeError:
            *parents, final = keys

        root = self
        for k in parents:
            try:
                root = root[k]
            except KeyError:
                if not create:
                    raise

                root[k] = {}
                root = root[k]
            else:
                if not isinstance(root, Configuration):
                    raise KeyError(k)

        return root, final

    def overwrite(self, key: Union[str, Iterable[str]], value: Any) -> Any:
        """
        Overwrite a possibly existing parameter value in the configuration.

        Parameters
        ----------
        key : str or iterable of str
            The parameter name to overwrite the value for.
        value
            The new value for the parameter.

        Returns
        -------
        old_value
            The value that has been overwritten or `None` if no value was present.

        See Also
        --------
        overwrite_all : overwrite multiple values in one go.
        """
        old_value = self.pop(key, None)
        try:
            sub_conf = Configuration(**old_value)
            old_value = sub_conf.overwrite_all(value)
            value = sub_conf
        except TypeError:
            pass

        self.__setitem__(key, value)
        return old_value

    def overwrite_all(self, other: _MappingLike = (), **kwargs) -> Mapping[str, Any]:
        """
        Overwrite multiple possibly existing parameter value in this configuration.

        This method makes it possible to overwrite multiple values in one go.
        It should produce the same results as calling `update`
        when none of the keys are already contained in this configuration.
        Unlike `update`, however, this method will not raise an error
        if one or more of the keys already exist.

        Parameters
        ----------
        other : Mapping or iterable of tuples
            Dictionary-like object with values to overwrite.
        **kwargs
            Additional key-value pairs for overwrites.

        Returns
        -------
        old_values : Mapping
            Mapping from keys to the values that have been overwritten.
            If the key did not exist, the corresponding value is `None`.

        See Also
        --------
        overwrite : overwrite single values.
        update : same functionality, but raises errors for duplicate keys.
        """
        old_values = {}

        try:
            for k in other.keys():
                old_values[k] = self.overwrite(k, other[k])
        except AttributeError:
            for k, v in other:
                old_values[k] = self.overwrite(k, v)

        for k, v in kwargs.items():
            old_values[k] = self.overwrite(k, v)

        return old_values

    def save(
        self,
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
        dumper : Dumper
            Class used to write file.
        key_modifiers : dict, optional
            A dictionary with replacement strings: The configuration keys will be
            modified, by replacing the string from the key_modifiers key with its
            value.
        """
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(exist_ok=True, parents=True)
        config = _replace_in_keys(config, key_modifiers)
        dumper.save(config, path)

    @classmethod
    def load(
        cls, path: Union[Path, str], loader, key_modifiers: Mapping[str, str] = {}
    ):
        """
        Read configuration from a file or directory.

        Parameters
        ----------
        path : Path or str
            Path to a readable file.
        loader : Loader
            Class used to read file.
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
        return cls(**config)
