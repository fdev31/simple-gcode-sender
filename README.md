# A simple gcode sender

Features:

- fast (buffered)
- simple to use
- easy to tune to your device (one simple & clean Python file)
- works well on a raspberry pi (tested with "old" Python versions)

Usage: `sgs <gcode_filename> <serial_device>`

Note: if you see any output, it means there are errors occurring, try tweaking those two values:

```python
BUFFER_SIZE = 10 # you can try to reduce this
BUFFER_FULL_PAUSE_DURATION = 0.01 # you can try to increase that
```

On the other hand, if you have a really fast hardware, you can do the opposite until you get some errors (prioritize `BUFFER_FULL_PAUSE_DURATION` over `BUFFER_SIZE`: buffered data may get replayed on error which may lead to undesired behavior (duplicate gcodes).
