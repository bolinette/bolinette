# Profile

The profile determine which env files are loaded during the initialization phase.
Define the profile on the first line of the `env/.profile` file.
The default profile is `"development"`.

# Init variables

Init variables are a kind of environment variables that are statically available at script top level.
They are used to customize class declarations when the context is not initialized yet.

Init variables are defined inside the `env/init.yaml` file.

## Example

```yaml
# init.yaml
UNIQUE_BOOK_NAME: true
DEFAULT_BOOK_PRICE: 14.99
```

```python
from bolinette import core, blnt, types
from bolinette.decorators import model

@model('book')
class Book(blnt.Model):
    name = types.defs.Column(types.db.String, unique=core.init['UNIQUE_BOOK_NAME'])
    price = types.defs.Column(types.db.Float, nullable=False, default=core.init['DEFAULT_BOOK_PRICE'])
```

# Environment variables

Environment variables are loaded from env files and available in the [context](./context.md#environment).
The first file loaded is `env/env.<profile>.yaml` where `<profile>` is the current profile in `env/.profile`.

Variables inside `env/env.local.<profile>.yaml` override the ones previously loaded.
This file is meant to be excluded from your VCS to override variables on specific deployment systems.

Then Bolinette iterates through os variables to find those that start with `BLNT_` and overwrite variables from files, without the `BLNT_` prefix.

Finally, you can pass overrides to the Bolinette constructor. These will be on top of everything else.

```python
from bolinette import Bolinette

bolinette = Bolinette(profile='temp', overrides={'PORT': 1337})
```
