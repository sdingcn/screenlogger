# screenlogger

automatically capturing "important" screenshots over long time periods

## algorithm

The program uses three parameters `x`, `a`, `b`.
Currently `x = max(2 * screenshot_time_on_this_machine, 1.0)`, `a = 1.0`, `b = 10.0`.

It maintains and updates two screenshots separated by `x` seconds;
if the screen pixel difference is `< a%` during `x` seconds,
the program regards the screen as an "event",
and tries to add it to an event queue if its difference with the previous event is `> b%`.

## requirements

`Python >= 3.12`, and see `requirements.txt`

## usage

Run `python3 screenlogger.py` to see the help message.
