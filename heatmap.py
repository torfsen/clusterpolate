#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

# Copyright (c) 2015 Florian Brucker (mail@florianbrucker.de).
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Simple heat maps.
"""

from __future__ import division

import math

from PIL import Image


__all__ = ['bounding_box', 'gradient', 'heatmap', 'interpolate']


def _gauss(rx, ry, sdx=None, sdy=None):
    """
    Create Gaussian blob image.

    ``rx`` and ``ry`` are the image radii in ``x`` and ``y`` direction,
    respectively. The actual image width and height are ``2 * rx + 1``
    and ``2 * ry + 1``, respectively. The returned image has mode ``F``.
    Values are normalized so that the image center has value ``1``.

    ``sdx`` and ``sdy`` are the standard deviations in ``x`` and ``y``
    direction, respectively. If they are not given then they are chosen
    so that the border pixels have values smaller than ``0.5 / 255``.
    """
    def sd_for_r(r):
        return r / (-2 * math.log(0.5 / 255))**0.5

    sdx = sdx or sd_for_r(rx)
    sdy = sdy or sd_for_r(ry)
    quarter = Image.new('F', (rx + 1, ry + 1), 0)
    dx = 1 / sdx**2
    dy = 1 / sdy**2
    data = []
    for y in range(ry + 1):
        vy = dy * (y - ry)**2
        for x in range(rx + 1):
            vx = dx * (x - rx)**2
            data.append(math.exp(-0.5 * (vx + vy)))
    quarter.putdata(data)
    img = Image.new('F', (2 * rx + 1, 2 * ry + 1), 0)
    img.paste(quarter, (0, 0))
    img.paste(quarter.transpose(Image.FLIP_TOP_BOTTOM), (0, ry + 1))
    img.paste(quarter.transpose(Image.ROTATE_180), (rx + 1, ry + 1))
    img.paste(quarter.transpose(Image.FLIP_LEFT_RIGHT), (rx + 1, 0))
    return img


def _add_image(img1, img2, p=(0, 0), factor=1):
    """
    Add one image to another.

    The data of ``img2`` is added to that of ``img1``, which is
    updated in-place. Both images are assumed to contain a single band.

    The data of ``img2`` is translated by ``p`` and multiplied by
    ``factor`` before adding it to ``img1``. ``p`` can contain negative
    values. ``img2`` itself is not modified.
    """
    pix1 = img1.load()
    pix2 = img2.load()
    p0, p1 = map(int, p)
    start_x = max(0, p0)
    stop_x = min(img1.size[0], img2.size[0] + p0)
    start_y = max(0, p1)
    stop_y = min(img1.size[1], img2.size[1] + p1)
    for x in range(start_x, stop_x):
        for y in range(start_y, stop_y):
            pix1[x, y] += factor * pix2[x - p0, y - p1]


def heatmap(points, area=None, size=(100, 100), radius=5, default_intensity=1,
            colorize=None, mode='RGBA'):
    """
    Create a heat map image.

    ``points`` is a list of points, each of which is a tuple or list
    with at least 2 entries (the x and y coordinates). An optional third
    entry specifies the point's intensity, which defaults to
    ``default_intensity``.

    The area covered by the heat map is given by the 2x2 array ``area``:
    The upper left pixel of the image corresponds to the coordinates
    ``(area[0][0], area[0][1])`` while the lower right pixel corresponds
    to ``(area[1][0], area[1][1])``. If ``area`` is not given then the
    bounding box of the points is used.

    The size of the image in pixels is given by the 2-tuple ``size``.

    ``radius`` specifies the radius of the blobs, in point coordinate
    units.

    ``colorize`` is an optional callback that converts raw (i.e. float)
    intensity values into color tuples. The length of the color tuples
    must match the number of bands in ``mode``, e.g. if ``mode`` is
    ``'RGBA'`` then ``colorize`` must return tuples of length 4. If
    ``colorize`` is not given then the return value of ``heatmap`` is
    a single-band image of mode ``F`` (``mode`` is ignored in that
    case). You can use :py:func:`gradient` to create gradient callbacks
    suitable for ``colorize``.

    All coordinates are in the image coordinate system, i.e. the upper
    left corner has the coordinates ``(0, 0)``.

    The return value is an :py:class:`Image` instance.
    """
    if area is None:
        points = list(points)  # In case ``points`` is a generator
        if len(points) < 2:
            raise ValueError('Need at least 2 points for automatic area ' +
                             'calculation.')
        area = bounding_box(points)
    img = Image.new('F', size, 0)
    width_factor = size[0] / (area[1][0] - area[0][0])
    height_factor = size[1] / (area[1][1] - area[0][1])
    rx = int(radius * width_factor)
    ry = int(radius * height_factor)
    kernel = _gauss(rx, ry)
    for point in points:
        try:
            intensity = point[2]
        except IndexError:
            intensity = default_intensity
        x = (point[0] - area[0][0]) * width_factor
        y = (point[1] - area[0][1]) * height_factor
        _add_image(img, kernel, (x - rx - 1, y - ry - 1), intensity)
    if colorize:
        data = map(colorize, img.getdata())
        if mode != 'F':
            data = [tuple(int(x) for x in t) for t in data]
        img = Image.new(mode, size)
        img.putdata(data)
    return img


def interpolate(t1, t2, x):
    """
    Linear interpolation between two tuples.

    Returns a tuple containing the linear interpolations between the
    values in the two tuples. If ``x`` is ``0``, ``t1`` is returned.
    If ``x`` is ``1``, ``t2`` is returned. Values between ``0`` and
    ``1`` return intermediate tuples.

    ``t1`` and ``t2`` must have the same length.
    """
    return tuple(x * t2[i] + (1 - x) * t1[i] for i in range(len(t1)))


def gradient(stops):
    """
    Create a gradient function.

    ``stops`` is a dictionary that maps floats to tuples.

    The return value is a function that interpolates between the
    stops, mapping floats to tuples::

        >>> f = gradient({0.0: (255, 0, 0),
        ...               0.5: (0, 255, 0),
        ...               1.0: (0, 0, 255)})
        >>> f(0.25)
        (127.5, 127.5, 0.0)

    Values smaller than the lowest stop are mapped to the lowest stop,
    and values larger than the largest stop are mapped to the largest
    stop::

        >>> f(-1)
        (255, 0, 0)
        >>> f(2)
        (0, 0, 255)
    """
    if not stops:
        raise ValueError('You must specify at least one stop.')
    stops = sorted(stops.items())

    def colorize(v):
        if v <= stops[0][0]:
            return stops[0][1]
        for i, stop in enumerate(stops[1:], start=1):
            if v <= stop[0]:
                previous = stops[i - 1]
                x = (v - previous[0]) / float(stop[0] - previous[0])
                return interpolate(previous[1], stop[1], x)
        return stops[-1][1]

    return colorize


def bounding_box(points):
    """
    Compute a point cloud's bounding box.

    Returns the bounding box of the given points. Each point is a tuple
    or list with at least 2 entries (its x and y coordinates).

    The return value is a 2x2 tuple containing the upper left and the
    lower right bounding box corners.
    """
    left = top = float('Inf')
    right = bottom = float('-Inf')
    for point in points:
        if point[0] < left:
            left = point[0]
        if point[0] > right:
            right = point[0]
        if point[1] < top:
            top = point[1]
        if point[1] > bottom:
             bottom = point[1]
    return ((left, top), (right, bottom))


if __name__ == '__main__':

    from random import uniform

    n = 100
    i = (0.5, 1)
    s = 100

    points = [(uniform(0, s), uniform(0, s), uniform(*i)) for _ in range(n)]

    colorize = gradient({
        0.0: (0, 0, 0, 0),
        0.5: (255, 0, 0, 255),
        1.0: (0, 255, 0, 255)}
    )

    img = heatmap(
        points,
        area=((0, 0), (100, 200)),
        size=(400, 400),
        radius=10,
        colorize=colorize
    )
    img.show()

