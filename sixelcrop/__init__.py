"""Crop a sixel image in sixel space."""

from typing import Generator, Optional

__version__ = "0.1.4"
__author__ = "Josiah Outram Halstead"
__email__ = "josiah@halstead.email"
__copyright__ = f"© 2023, {__author__}"


def sixelcrop(
    data: "str",
    x: "int" = 0,
    y: "int" = 0,
    w: "Optional[int]" = None,
    h: "Optional[int]" = None,
) -> "str":
    """Crop sixel data.

    Args:
        data: The input sixel image as a string
        x: The horizontal offset of the left edge of the target region
        y: The vertical offset of the left edge of the target region
        w: The width of the target region
        h: The height of the target region

    """

    def _crop(
        data: "str",
        x: "int" = 0,
        y: "int" = 0,
        w: "Optional[int]" = None,
        h: "Optional[int]" = None,
    ) -> "Generator[str, None, None]":
        # Store the sixel data character number
        i = 0
        # The current pixel row number
        pixel_row = 0
        # Stores the current pixel column number
        pixel_col = 0
        # Store the current parsed line
        line = ""
        # Stores the most recent color selection
        color_prev = ""

        # Skip to the first instance of "\x1bP"
        if not data.startswith("\x1bP"):
            if (start := data.find("\x1bP")) > 0:
                data = data[start:]
            else:
                # We do not have any sixel data, so return nothing
                yield ""
                return

        while True:
            # Retrieve the next character from the input sixel image string
            char = data[i]
            i += 1

            if char == "\x1b":
                yield char
                char = data[i]
                i += 1
                if char == "P":
                    yield char
                    # Parse device control string parameters. We want to set P2 to 1 by
                    # default, as we do not shift pixels between sixel lines, and we
                    # want skipped parts of sixel lines to be transparent
                    params = ["", "", ""]
                    p = 0
                    char = data[i]
                    i += 1
                    while char in "0123456789;":
                        if char == ";":
                            p += 1
                        else:
                            params[p] += char
                        char = data[i]
                        i += 1

                    # Set default control string parameters
                    # Set pixel aspect ratio to 1:1 by default
                    # if not params[0]:
                    #     params[0] = "7"
                    # P2 == 1 sets pixel positions specified as 0 to remain at their
                    # current color - this makes skipped cropped regions transparent
                    if not params[1]:
                        params[1] = "1"
                    # Do not set default for horizontal grid size
                    # if not params[2]:
                        # params[2] = "0"
                    yield from ";".join(params)

                    # The device control string should end with a "q"
                    assert char == "q"
                    yield char

                # If we are at the end of the image collect and add the footer
                elif char == "\\":
                    yield "\\"
                    return
                continue

            # Process raster attribute commands
            if char == '"':
                yield char
                # Adjust width and height parameters
                params = [""]
                char = data[i]
                i += 1
                while char in "0123456789;":
                    if char == ";":
                        params.append("")
                    else:
                        params[-1] += char
                    char = data[i]
                    i += 1
                # Adjust image width
                if len(params) >= 3:
                    if w is None:
                        w = int(params[2]) - x
                # Adjust image height
                if len(params) >= 4 and h is None:
                    h = int(params[3]) - y

                while len(params) < 4:
                    params.append("")

                if h is not None:
                    params[3] = str(y + h - (y - y % 6))
                if w is not None:
                    params[2] = str(w)

                yield from ";".join(params)

            # For type checking
            # assert h is not None

            # Collect color commands
            if char == "#":
                while True:
                    # Color definitions start with the color introducer "#", and
                    # consist of semi-colon separated digits
                    color_cmd = char
                    while True:
                        char = data[i]
                        i += 1
                        if char not in "0123456789;":
                            break
                        else:
                            color_cmd += char

                    # If this is a color palette definition, always include it
                    if ";" in color_cmd:
                        yield from color_cmd
                        continue

                    # If this is a color set command, remember it in case the first line
                    # of the cropped region does not set the color
                    else:
                        color_prev = color_cmd

                    # If the next command is not a color command, carry on parsing
                    if char != "#":
                        break

            # Continue parsing the line until we encounter a new-line character
            if char != "-":

                # If this line is before the top of the retained region, skip it quickly
                if pixel_row < y - 6:
                    while char != "-":
                        char = data[i]
                        i += 1
                        # Check if we unexpectedly reached the end of the image
                        if char == "\x1b":
                            return

                # If we are only cropping the image's height, we don't need to parse each
                # line in the cropped region
                elif w is None:

                    # Edit the first row of sixels to remove unrequired upper pixel rows
                    if pixel_row < y < pixel_row + 6:
                        n = y - pixel_row
                        while char != "-":
                            # Transform each sixel character in the sixel row to mask
                            # the first n rows of pixels
                            if (sixel := ord(char)) >= 63:
                                char = chr(((sixel - 63) & (63 - (2**n - 1))) + 63)
                            line += char
                            char = data[i]
                            i += 1
                        line += char

                    # Edit the last row of sixels to remove unrequired lower pixel rows
                    elif h is not None and pixel_row > 0 and pixel_row < y + h < pixel_row + 6:
                        n = y + h - pixel_row
                        while char != "-":
                            # Transform each sixel character in the sixel row to mask
                            # the last n rows of pixels
                            if (sixel := ord(char)) >= 63:
                                char = chr(((sixel - 63) & ((2**n - 1))) + 63)
                            line += char
                            char = data[i]
                            i += 1
                        line += char

                    # Otherwise copy the whole line exactly
                    else:
                        while char != "-":
                            line += char
                            char = data[i]
                            i += 1
                        line += char

                # Otherwise, we need to parse and modify the lines in the target region to
                # crop in the x-direction
                elif h:
                    first_row = pixel_row < y < pixel_row + 6
                    last_row = pixel_row < y + h < pixel_row + 6

                    # Keep track of the last selected color
                    color = ""
                    # Keep track of the currently horizontal position in pixels
                    pixel_col = 0

                    # Keep parsing until we reach the end of the sixel row or the end
                    # of the image
                    while char not in "-\x1b":

                        # The color introducer ("#") start a color selection sequence
                        # Record the current color selection
                        if char == "#":
                            color = ""
                            while char in "#0123456789":
                                color += char
                                char = data[i]
                                i += 1
                            continue

                        # If we encounter a graphics repeat introducer "!", we may need
                        # to adjust the number of repeats
                        repeat_s = ""
                        # `repeats` stores the number of repeats in the original image
                        # `n_repeats` stores the adjusted number of repeats
                        repeats = n_repeats = 1

                        # Check for graphics repeat introducers
                        if char == "!":
                            # A graphics repeat introducer is followed by a number
                            char = data[i]
                            i += 1
                            while char in "0123456789":
                                repeat_s += char
                                char = data[i]
                                i += 1

                            n_repeats = repeats = int(repeat_s or "1")

                            # If this repeat takes us into the target region, only keep the
                            # encroaching part
                            if x < pixel_col + repeats < x + w:
                                n_repeats = min(
                                    pixel_col + repeats - x,
                                    n_repeats,
                                )

                            # If this repeat takes us out of the target region, add just
                            # enough repeats to take us to the end of the target region
                            elif x + w < pixel_col + repeats:
                                n_repeats = min(n_repeats, x + w - pixel_col)

                            # Ensure we never have more repeats than the width of the image
                            n_repeats = min(n_repeats, w)

                            # Generate the transformed graphics repeat control function
                            repeat_s = f"!{n_repeats}"

                        # If we encounter a graphics carriage return ($), reset the
                        # pixel position back to the start of the line
                        if char == "$":
                            line += char
                            char = data[i]
                            i += 1
                            pixel_col = 0
                            continue

                        # If this is the first sixel row of the target region, we may
                        # have to mask pixels at the top of the row
                        elif first_row:
                            n = y - pixel_row
                            if (sixel := ord(char)) >= 63:
                                char = chr(((sixel - 63) & (63 - (2**n - 1))) + 63)

                        # If this is the first sixel row of the target region, we may
                        # have to mask pixels at the bottom of the row
                        elif last_row:
                            n = y + h - pixel_row
                            if (sixel := ord(char)) >= 63:
                                char = chr(((sixel - 63) & ((2**n - 1))) + 63)

                        # If the last encountered sixel is within the target region, we
                        # need to add it to the output
                        if (
                            n_repeats
                            and x < pixel_col + repeats
                            and pixel_col + n_repeats <= x + w
                        ):
                            # If we are at the start of a new line of sixels, we always
                            # the last encountered color command, as the original color
                            # command may be cropped out
                            if not line:
                                line += color_prev
                            # Add the new color command if the color has been changed
                            if color != color_prev:
                                color_prev = color
                                line += color
                            # Add the character(s)
                            line += repeat_s + char

                        # Shift the current pixel position on the current row of sixels
                        pixel_col += repeats

                        # Grab the next character
                        char = data[i]
                        i += 1

                        # End the output if we reach the end of the input
                        if char == "\x1b":
                            yield from "\x1b\\"
                            return

                        # If we are now outside the the target region on the current
                        # row, we can skip the remaining characters up until the next
                        # carriage return or new line
                        if pixel_col >= x + w:
                            # Skip to the end of the current line
                            while char not in "-$":
                                char = data[i]
                                i += 1

                    # Add the line break character to the line
                    line += char

            # If this line is within the target region, yield the line
            if h and  y - 6 < pixel_row < y + h:
                yield from line
            pixel_row += 6

            # Do not bother parsing lines beyond the end of the target region
            if h and pixel_row >= y + h:
                yield from "\x1b\\"
                return

            # Reset the current line
            line = ""

    return "".join(_crop(data, x, y, w, h))


def cli() -> None:
    """Defines a command line interface for cropping sixel images."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Crop a sixel image in sixel space",
        epilog=__copyright__,
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser.add_argument("--help", action="help")
    parser.add_argument(
        "-x",
        "--left",
        type=int,
        default=0,
        help="The offset of the left edge of the target region",
    )
    parser.add_argument(
        "-y",
        "--top",
        type=int,
        default=0,
        help="The offset of the top edge of the target region",
    )
    parser.add_argument(
        "-w", "--width", type=int, default=None, help="The width of the target region"
    )
    parser.add_argument(
        "-h", "--height", type=int, default=None, help="The height of the target region"
    )
    parser.add_argument(
        "filename",
        type=Path,
        default=Path("/dev/stdin"),
        help="Path to sixel image file (use '-' to read data from standard input)",
    )

    args = parser.parse_args()
    if str(args.filename) == "-":
        args.filename = Path("/dev/stdin")
    data = args.filename.read_text()

    sys.stdout.write(sixelcrop(data, args.left, args.top, args.width, args.height))


if __name__ == "__main__":
    cli()
