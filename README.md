<img src="https://user-images.githubusercontent.com/12154190/199075915-04265c49-5392-4126-b34f-21bdff5cdc28.png" align="right" width="300">

# sixelcrop

[![PyPI - Version](https://img.shields.io/pypi/v/sixelcrop.svg)](https://pypi.org/project/sixelcrop)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sixelcrop.svg)](https://pypi.org/project/sixelcrop)


**Crop sixel images in sixel-space!**

sixelcrop is a Python library and command line tool to crop [sixel](https://en.wikipedia.org/wiki/Sixel) images

-----

## Installation

```console
pipx install sixelcrop
# OR
pip install sixelcrop
```

## Usage

### Command Line

```
usage: sixelcrop [--help] [-x int] [-y int] [-w int] [-h int] Path

Crop a sixel image in sixel space

positional arguments:
  Path                  Path to sixel image file (use '-' to read data from standard input)

options:
  --help
  -x int, --left int    The offset of the left edge of the target region
  -y int, --top int     The offset of the top edge of the target region
  -w int, --width int   The width of the target region
  -h int, --height int  The height of the target region

```

Example:

```bash
curl https://www.python.org/static/img/python-logo@2x.png | img2sixel | sixelcrop -x 10 -y 15 -w 120 -h 125 -
```

### Python API

```python
import sys
from sixelcrop import sixelcrop

with open("snake.six") as f:
    data = f.read()

sys.stdout.write(sixelcrop(data, x=300, y=50, w=200, h=150))
```

## License

`sixelcrop` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
