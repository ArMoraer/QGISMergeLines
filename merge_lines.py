# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MergeLines
								 A QGIS plugin
 Simplifies the topology of a line network by merging adjacent lines
							  -------------------
		begin                : 2016-01-09
		git sha              : $Format:%H$
		copyright            : (C) 2016 by Alexandre Delahaye
		email                : menoetios <at> gmail <dot> com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import pyqtSignal, pyqtSlot, QObject, QSettings, QThread, QTranslator, qVersion, QCoreApplication, QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox
from qgis.core import *
import math
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from merge_lines_dialog import MergeLinesDialog
import os.path
import time


class MergeLines(QObject):
	"""QGIS Plugin Implementation."""

	partDone = pyqtSignal(int)
	allDone = pyqtSignal()

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""

		super(MergeLines, self).__init__() # necessary for pyqtSignal

		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'MergeLines_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		# Create the dialog (after translation) and keep reference
		self.dlg = MergeLinesDialog()

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&MergeLines')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar(u'MergeLines')
		self.toolbar.setObjectName(u'MergeLines')

	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('MergeLines', message)

	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToVectorMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/MergeLines/img/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Merge lines'),
			callback=self.run,
			parent=self.iface.mainWindow())
		self.dlg.runButton.clicked.connect( self.onStart )
		# self.dlg.toleranceCheckBox.clicked.connect( self.setTolerance )
		self.partDone.connect( self.updateProgressBar )
		self.allDone.connect( self.onFinished )

	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginVectorMenu(
				self.tr(u'&MergeLines'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar

	@pyqtSlot()
	def onStart(self):
		self.dlg.runButton.setEnabled(False)
		self.dlg.closeButton.setEnabled(False)
		self.dlg.layerComboBox.setEnabled(False)
		self.dlg.mergingComboBox.setEnabled(False)

		# input params
		inputLayer = self.dlg.layerComboBox.itemData( self.dlg.layerComboBox.currentIndex() )
		# if self.dlg.toleranceCheckBox.isChecked(): tolerance = self.dlg.toleranceSpinBox.value()
		# else: tolerance = 0
		params = {'mergingMethod': self.dlg.mergingComboBox.currentIndex(),
			'outputLayerName': self.dlg.outputLayerEdit.text(),
			'tolerance': 0} # removed option
		self.v = False # verbose

		# ! Performance evaluation
		# start_time = time.time()
		# n_sim = 10
		# for i in range(0, n_sim):
		# 	print "sim #%s" % i
		# 	self.joinLines( inputLayer, params )
		# print "Time: %s seconds " % ( (time.time() - start_time) / n_sim)

		self.joinLines( inputLayer, params )

	@pyqtSlot()
	def onFinished(self):
		self.dlg.progressBar.setValue( 100 )
		# self.dlg.runButton.setEnabled(True)
		self.dlg.closeButton.setEnabled(True)
		self.dlg.layerComboBox.setEnabled(True)
		self.dlg.mergingComboBox.setEnabled(True)

	@pyqtSlot()
	def setTolerance(self):
		if self.dlg.toleranceCheckBox.isChecked():
			self.dlg.toleranceSpinBox.setEnabled(True)
		else:
			self.dlg.toleranceSpinBox.setEnabled(False)


	def joinLines( self, layer, params ):
		"""Main function"""

		origPr = layer.dataProvider()

		# create output layer
		crs = layer.crs().authid()
		if params['outputLayerName']:
			outputLayerName = params['outputLayerName']
		else:
			outputLayerName = "output"
		self.outLyr = QgsVectorLayer("LineString?crs={0}&index=yes".format(crs), outputLayerName, "memory")
		outPr = self.outLyr.dataProvider()
		outPr.addAttributes( origPr.fields().toList() )
		self.outLyr.updateFields() # tell the vector layer to fetch changes from the provider
		self.outLyr.startEditing()
		self.outLyr.commitChanges()

		# featureAdded signal (address feature insertion bug)
		self.outLyr.featureAdded.connect( self.updateAfterFeatureAdded )

		# copy input layer to output layer
		outPr.addFeatures( list(layer.getFeatures()) )

		deletedFeaturesID = []
		# TODO future improvment: first list features whose both endpoints are connected, then list the others (affluents)
		featureList = sorted( list(self.outLyr.getFeatures()), key=lambda feature: feature.geometry().length(), reverse=True ) # sort lines by descending length
		featureNumber = len(featureList)

		# if mergingMethod is 'alignment', construct a dict with the orientation of each line
		if params['mergingMethod'] == 1:
			orientationDict = {}
			for feature in featureList:
				if not feature.geometry().isMultipart(): # multipart lines are ignored
					orientationDict[feature.id()] = self.getOrientation( feature )
			params['orientationDict'] = orientationDict

		# Build the spatial index for faster lookup.
		self.spatialIdx = QgsSpatialIndex()
		map( self.spatialIdx.insertFeature, featureList )

		# iterates on lines
		for idx, feature in enumerate(featureList):

			if self.v: print "Line %d: " % feature.id()

			if feature.geometry().isMultipart(): # multipart lines are ignored
				if self.v: print "| is multipart, continue"
				continue

			if feature.id() in deletedFeaturesID:
				if self.v: print "| already deleted, continue"
				continue

			# print "main::features={0}".format([f.id() for f in list(self.outLyr.getFeatures())])	

			# get lines connected to current feature (i.e. lines that share one extremity)
			connectedLines = self.getConnectedLines( feature, deletedFeaturesID, params )
			if self.v: print "| %d connected lines" % len(connectedLines)

			# merging
			if len(connectedLines) > 1:
				# Line is connected to several lines -> merging current line with one of the connected lines
				mergingLine = self.chooseMergingLine( feature, connectedLines, params )
				if self.v: print "| Merging with line %d" % mergingLine.id()
				delFeaturesID, mergedFeature = self.mergeLines( feature, mergingLine, outPr, params )

			elif len(connectedLines) == 1:
				# Line is connected to one line -> merging current line with it
				if self.v: print "| Merging with line %d" % connectedLines[0].id()
				delFeaturesID, mergedFeature = self.mergeLines( feature, connectedLines[0], outPr, params )

			else:
				# Line is not connected to anything -> just keep current line
				if self.v: print "| No merging"
				delFeaturesID = None
				# outPr.deleteFeatures( [feature.id()] ) # fix a bug (feature does not appear)
				# outPr.addFeatures( [feature] )

			if delFeaturesID is not None:
				deletedFeaturesID += delFeaturesID
			# print "deletedFeaturesID={0}".format( deletedFeaturesID )
			self.partDone.emit( float(idx)/featureNumber*100 )
		# end for

		# Commit changes to self.outLyr and display layer
		# self.outLyr.commitChanges()
		QgsMapLayerRegistry.instance().addMapLayer(self.outLyr)

		self.allDone.emit()


	def getConnectedLines( self, feature, deletedFeaturesID, params ):
		"""Get all lines which are connected to <feature> by one endpoint"""
	
		connectedLines = []

		# if feature.geometry().isMultipart(): # multipart lines are ignored
		#   if self.v: print "Line {} is multipart, ignored".format(feature.id())
		#   return []

		points = feature.geometry().asPolyline()
		endPt0 = points[0]
		endPt1 = points[-1]

		# Get the ids of all the features in the index that are within
		# the bounding box of the current feature because these are the ones
		# that will be connected.
		ids = self.spatialIdx.intersects( feature.geometry().boundingBox() )
		allfeatures = {feature.id(): feature for feature in list(self.outLyr.getFeatures())}
		
		# if self.v: 
		# 	print "| getConnectedLines::allfeatures={0}".format([f.id() for f in list(self.outLyr.getFeatures())])
		# 	spatialList = sorted( list(self.spatialIdx.intersects( self.outLyr.extent() )) )
		# 	print "| getConnectedLines::spatialIdx={0} {1}".format( len( spatialList ), spatialList )
		
		# for ifeature in self.outLyr.getFeatures():
		for id in ids:
			
			ifeature = allfeatures[id]
			if ifeature == feature: continue

			if ifeature.geometry().isMultipart(): # multipart lines are ignored
				continue

			ipoints = ifeature.geometry().asPolyline()
			iendPt0 = ipoints[0]
			iendPt1 = ipoints[-1]

			# check if one endpoint of <feature> is equal to one endpoint of <ifeature>
			tol = params['tolerance']
			d = QgsDistanceArea()
			if tol == 0:
				if ( (endPt0 == iendPt0) or (endPt0 == iendPt1) or (endPt1 == iendPt0) or (endPt1 == iendPt1) ) \
					and (feature.id() != ifeature.id()) and not (ifeature.id() in deletedFeaturesID):
					connectedLines.append(ifeature)
			else:
				if ( (d.measureLine(endPt0, iendPt0) <= tol) or (d.measureLine(endPt0, iendPt1) <= tol) \
					or (d.measureLine(endPt1, iendPt0) <= tol) or (d.measureLine(endPt1, iendPt1) <= tol) ) \
					and (feature.id() != ifeature.id()) and not (ifeature.id() in deletedFeaturesID):
					connectedLines.append(ifeature)
				
		return connectedLines
	
	
	def chooseMergingLine( self, feature, connectedLines, params ):
		"""Choose a line among <connectedLines> to be merged with <feature>"""
		
		mergingLine = connectedLines[0] # default

		if params['mergingMethod'] == 0: # max length

			maxLength = 0
			for line in connectedLines:
				# if self.v: print "| | ID {}: len={}".format(line.id(), line.geometry().length())
				if line.geometry().length() > maxLength:
					mergingLine = line
					maxLength = line.geometry().length()

		elif params['mergingMethod'] == 1: # best alignment

			orientationDict = params['orientationDict']
			minDiff = 180
			featureOrientation = orientationDict[feature.id()]
			featureEndPt0 = feature.geometry().asPolyline()[0]
			featureEndPt1 = feature.geometry().asPolyline()[-1]

			if self.v: print "| Orient. of line {0}: {1}".format(feature.id(), featureOrientation)

			for line in connectedLines:

				# line.id() may be missing from orientationDict
				# Adding line.id() in mergeLines() causes issues (id not yet initialized)
				# TODO: eventually put this part into <updateAfterFeatureAdded> (issue with params scope)
				if not line.id() in orientationDict:
					orientationDict = params['orientationDict']
					orientationDict[line.id()] = self.getOrientation( line )
					params['orientationDict'] = orientationDict

				# Processing line orientation to avoid reverse orientation issue
				# If <feature> and <line> are connected with the same enpoint (i.e. first with first or last with last), then reverse <line> orientation
				orient = orientationDict[line.id()]
				lineEndPt0 = line.geometry().asPolyline()[0]
				lineEndPt1 = line.geometry().asPolyline()[-1]

				if ( (featureEndPt0 == lineEndPt0) or (featureEndPt1 == lineEndPt1) ):
					orient = orient + 180 % 360

				if self.v: print "| | ID {}: orient={}".format(line.id(), orient)

				# Finally
				if abs( orient - featureOrientation ) < minDiff:
					mergingLine = line
					minDiff = abs( orientationDict[line.id()] - featureOrientation )

		return mergingLine
	
	
	def mergeLines( self, feature1, feature2, dataProvider, params ):
		"""Merge 2 lines and their attributes. Update <params.orientationDict>"""
		
		# For now, the rule is simply to overwrite <feature2> attributes with <feature1> attributes
		mergedFeature = QgsFeature()
		mergedFeature.setGeometry( feature1.geometry().combine(feature2.geometry()) )
		mergedFeature.setAttributes( feature1.attributes() )
		
		#if self.v: print "| {} deleted".format(feature2.id())

		# Update spatial index. <mergedFeature> is added to the index in the updateAfterFeatureAdded function.
		self.spatialIdx.deleteFeature( feature1 )
		self.spatialIdx.deleteFeature( feature2 )

		# Update self.outLyr
		# Features are updated via QgsVectorLayer instead of QgsDataProvider in order to emit the featureAdded signal, 
		# which then allows to properly update spatialIdx and orientationDict (issue with fids)
		self.outLyr.startEditing()
		self.outLyr.deleteFeature( feature1.id() )
		self.outLyr.deleteFeature( feature2.id() )
		self.outLyr.addFeature( mergedFeature )
		self.outLyr.commitChanges()

		# Update params.orientationDict (delete <feature1> and <feature2>). <mergedFeature> is added to the dict in the updateAfterMerge function.
		if params['mergingMethod'] == 1:

			orientationDict = params['orientationDict']
			if feature1.id() in orientationDict: del orientationDict[feature1.id()] # delete <feature1>
			if feature2.id() in orientationDict: del orientationDict[feature2.id()] # delete <feature2>
			# orientationDict[mergedFeature.id()] = self.getOrientation( feature1 ) # update orientation of <mergedFeature> NOT WORKING (mergedFeature.id()==0)
			params['orientationDict'] = orientationDict

		return ([feature1.id(), feature2.id()], mergedFeature) #[feature2.id()] in v0.2.0 ?

	
	def updateAfterFeatureAdded( self, fid ):
		"""Adds feature with id <fid> to <params.orientationDict> and spatial index."""

		if fid < 0: # temporary id
			return

		if self.v: print "| updateAfterFeatureAdded called for fid=%d" % fid

		feature = list( self.outLyr.getFeatures( QgsFeatureRequest(fid) ) )[0]
		self.spatialIdx.insertFeature( feature )

	def getOrientation( self, feature ):
		"""Gets the orientation (direction) of a line"""

		points = feature.geometry().asPolyline()
		x1, y1 = points[0]
		x2, y2 = points[-1]
		x = x2-x1
		y = y2-y1
		if x == 0:
			angle = 90
		else:
			angle = math.atan( y/x ) * 180/math.pi % 180

		return angle

	def updateProgressBar( self, progress ):
		self.dlg.progressBar.setValue( progress )

	def run( self ):
		"""Run method that performs all the real work"""
		
		# BEGIN
		mapCanvas = self.iface.mapCanvas() 
		
		# some elements are disabled by default
		# self.dlg.toleranceCheckBox.setChecked(False)
		# self.dlg.toleranceSpinBox.setEnabled(False)
		self.dlg.runButton.setEnabled(True)
		
		# list layers for input combobox
		self.dlg.layerComboBox.clear() # clear the combobox
		layers = QgsMapLayerRegistry.instance().mapLayers().values() # Create list with all layers
		for layer in layers:
			if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line: # check if layer is vector & line type
				self.dlg.layerComboBox.addItem( layer.name(), layer ) 

		# merging methods combobox
		self.dlg.mergingComboBox.clear() # clear the combobox
		self.dlg.mergingComboBox.addItems( [self.tr("Length"), self.tr("Alignment")] )

		# show the dialog
		self.dlg.show() 

		# Run the dialog event loop
		self.dlg.exec_() 
		self.dlg.progressBar.setValue(0)
