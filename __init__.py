# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MergeLines
                                 A QGIS plugin
 Simplifies the topology of a line network by merging adjacent lines
                             -------------------
        begin                : 2016-01-09
        copyright            : (C) 2016 by Alexandre Delahaye
        email                : menoetios <at> gmail <dot> com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MergeLines class from file MergeLines.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .merge_lines import MergeLines
    return MergeLines(iface)
