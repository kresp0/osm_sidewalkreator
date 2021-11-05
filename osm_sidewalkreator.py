# -*- coding: utf-8 -*-
"""
/***************************************************************************
 sidewalkreator
                                 A QGIS plugin
 Plugin designated to create the Geometries of Sidewalks (separated from streets) based on OpenStreetMap Streets, given a bounding polygon, outputting to JOSM format. It is mostly intended for acessibility Mapping.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-09-29
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Kaue de Moraes Vestena
        email                : kauemv2@gmail.com
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

# import os.path
import os, requests, codecs, time
# from os import environ

# standard libraries
# import codecs # for osm2geojson

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgsMapLayerComboBox, QgsMapCanvas
from qgis.PyQt.QtWidgets import QAction
# additional qgis/qt imports:
from qgis import processing
from qgis.core import QgsMapLayerProxyModel, QgsFeature, QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject, QgsApplication, edit

# pure Qt imports, keep at minimun =P
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QDialogButtonBox


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .osm_sidewalkreator_dialog import sidewalkreatorDialog


# for third-party libraries installation
import subprocess
import sys


def install_pypi(packagename):
    subprocess.check_call([sys.executable, "-m", "pip", "install", packagename])


# importing or installing third-party libraries
try:
    # import geopandas as gpd
    import osm2geojson
except:
    pkg_to_be_installed = ['osm2geojson'] #'geopandas'

    for packagename in pkg_to_be_installed:
        install_pypi(packagename)


# # then again, because its best to raise an error
# import geopandas as gpd
import osm2geojson

# # internal dependencies:
from .osm_fetch import *
from .generic_functions import *
from .parameters import *



############################
##### GLOBAL-SCOPE
###########################

# to path stuff don't get messy:

# homepath = os.environ['HOME']
# homepath = os.path.expanduser('~')

# user_profile = 'default' #TODO: read from session

# TODO: adapt for windows aswell

# basepathp1 = '.local/share/QGIS/QGIS3/profiles'
# basepath = os.path.join(homepath,basepathp1,user_profile,basepathp2)

profilepath = QgsApplication.qgisSettingsDirPath()
base_pluginpath_p2 = 'python/plugins/osm_sidewalkreator'
basepath = os.path.join(profilepath,base_pluginpath_p2)
temps_path = os.path.join(basepath,'temporary')

print(basepath)
reports_path = os.path.join(basepath,'reports')


class sidewalkreator:
    """QGIS Plugin Implementation."""

    # to control current language:
    current_lang = 'en'

    # variables to control wheter change in language should change labels
    change_input_labels = True

    # to control wheter one shall ignore a "sidewalks already drawn" warning:
    ignore_sidewalks_already_drawn = False

    # no buildings is the most general situation
    no_buildings = True

    # if method to split sidewalks using addrs and/or building centroids (HERE NAMED POIS) are avaliable (unavaliable is the most general situation, there's lots of areas without a single one)
    POI_split_avaliable = False

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'sidewalkreator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&OSM SidewalKreator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None



        ###############################################
        ####    My code on __init__
        #########################################
        # language_selector
        # self.dlg.opt_ptbr.checked.connect(self.change_language)


        self.session_debugpath = os.path.join(reports_path,'session_debug.txt')

        with open(self.session_debugpath,'w+') as session_report:
            session_report.write('session_report:\n')
            # session_report.write(session_debugpath+'\n')
            # session_report.write(homepath)



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
        return QCoreApplication.translate('sidewalkreator', message)


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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):


        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/osm_sidewalkreator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create Sidewalks for OSM'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&OSM SidewalKreator'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = sidewalkreatorDialog()

            # setting items that should not be visible at beginning:
            self.dlg.sidewalks_warning.setHidden(True)
            self.dlg.widths_hint.setHidden(True)
            self.dlg.ignore_already_drawn_btn.setHidden(True)


            # # # THE FUNCTION CONNECTIONS
            self.dlg.datafetch.clicked.connect(self.call_get_osm_data)
            self.dlg.clean_data.clicked.connect(self.data_clean)
            self.dlg.generate_sidewalks.clicked.connect(self.draw_sidewalks)
            self.dlg.ignore_already_drawn_btn.clicked.connect(self.ignore_already_drawn_fcn)


            # cancel means reset AND close
            self.dlg.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_fields)
            self.dlg.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.reset_fields)


            # language stuff
            self.dlg.opt_ptbr.clicked.connect(self.change_language_ptbr)
            self.dlg.opt_en.clicked.connect(self.go_back_to_english)
            self.dlg.input_layer_selector.layerChanged.connect(self.get_input_layer)


            # # # handles and modifications/ors:


            self.dlg.input_layer_selector.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            self.dlg.input_layer_selector.setAllowEmptyLayer(True)
            self.dlg.input_layer_selector.setLayer(None)
            # thx: https://github.com/qgis/QGIS/issues/38472

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    ##################################
    ##### THE CLASS SCOPE
    ##################################

    def add_layer_canvas(self,layer):
        # canvas = QgsMapCanvas()
        QgsProject.instance().addMapLayer(layer)
        QgsMapCanvas().setExtent(layer.extent())
        # canvas.setLayerSet([QgsMapCanvasLayer(layer)])

    def change_language_ptbr(self):
        self.current_lang = 'ptbr'

        # # frozing selection if you opt for ptbr:
        # self.dlg.opt_ptbr.setEnabled(False)
        # self.dlg.opt_en.setEnabled(False)

        self.change_all_labels_bylang()

    def go_back_to_english(self):
        self.current_lang = 'en'

        self.change_all_labels_bylang()

    def change_all_labels_bylang(self):
        info_tuples = [
            # tuples: (qt-dlg_element,english_text,ptbr_text)
            (self.dlg.lang_label,"Language: ","Idioma: "),
            (self.dlg.input_pol_label,"Input Polygon: ","Polígono de Entrada" ),
            (self.dlg.table_txt1,'default widths for tag values','larguras-padrão para valores'),
            (self.dlg.table_txt2,'"0" means ignore feature','"0": ignorar feições'),
            (self.dlg.output_file_label,'Output File:','Arquivo de Saída:'),
            (self.dlg.datafetch,'Fetch Data','Obter Dados'),
            (self.dlg.input_status,'waiting a valid input...','aguardando uma entrada válida...',self.change_input_labels),
            (self.dlg.input_status_of_data,'waiting for data...','aguardando dados...',self.change_input_labels),
            (self.dlg.button_box.button(QDialogButtonBox.Cancel),"Cancel","Cancelar"),
            (self.dlg.button_box.button(QDialogButtonBox.Reset),"Reset","Reiniciar"),
            (self.dlg.clean_data,'Clean OSM Data and\nCompute Intersections','Limp. dados OSM e\nGerar Interseções'),
            (self.dlg.sidewalks_warning,"Some Sidewalks are already drawn!!! You must reshape your input polygon!!!","Já há algumas calçadas mapeadas!! Você deverá Redesenhar seu polígono de entrada!!"),
            (self.dlg.check_if_overlaps_buildings,'Check if Overlaps Buildings','Testar se Sobrepõe Edificações'),
            (self.dlg.widths_hint,'Hint: You Can Set Widths\nfor Each Segment...','Dica: Você pode Inserir uma Largura\nPara Cada Segmento'),
            (self.dlg.generate_sidewalks,'Generate Sidewalks','Gerar Calçadas'),
            (self.dlg.ignore_already_drawn_btn,"I Have Reviewed the Data\nAnd It's OK!!\n(or want to draw anyway)",'Eu Revisei os Dados\nE está tudo certo!!\n(ou gerar de qualquer jeito)'),
            (self.dlg.ch_ignore_buildings,'ignore buildings\n(much faster)','ignorar edificações\n(mais rápido)'),

            # (self.dlg.,'',''),
            # (self.dlg.,'',''),
            # (self.dlg.,'',''),
            # (self.dlg.,'',''),

        ]



        for info_set in info_tuples:
            # What an elegant solution!!! 
            self.set_text_based_on_language(*info_set)

    def data_clean(self):

        # getting table values, before table deactivation
        higway_valuestable_dict = {}

        for i,val in enumerate(self.unique_highway_values):
            # self.dlg.higway_values_table
            higway_valuestable_dict[val] = float(self.dlg.higway_values_table.item(i,1).text())


        # disabling what should not be used afterwards
        self.dlg.clean_data.setEnabled(False)
        self.dlg.higway_values_table.setEnabled(False)

        # removing undesired tag values:
        for i,value in enumerate(self.unique_highway_values):
            # if a too small value is set, then also remove it
            if float(self.dlg.higway_values_table.item(i,1).text()) < 0.5:
                remove_features_byattr(self.clipped_reproj_datalayer,highway_tag,value)#self.unique_highway_values[i])

        
        # creating points of intersection:
        intersection_points = get_intersections(self.clipped_reproj_datalayer,self.clipped_reproj_datalayer,'TEMPORARY_OUTPUT')

        intersection_points.setCrs(self.custom_localTM_crs)


        self.filtered_intersection_name = self.string_according_language('Road_Intersections','Intersecoes_Ruas')

        self.filtered_intersection_points = remove_duplicate_geometries(intersection_points,'memory:'+self.filtered_intersection_name)

        self.filtered_intersection_points.setCrs(self.custom_localTM_crs)


        # splitting into segments:
        self.splitted_lines_name = self.string_according_language('Splitted_OSM_Lines','OSM_subdividido')

        self.splitted_lines = split_lines(self.clipped_reproj_datalayer,self.clipped_reproj_datalayer,'memory:'+self.splitted_lines_name)

        self.splitted_lines.setCrs(self.custom_localTM_crs)

        # removing lines that does not serve to form a block ('quarteirão')
        remove_lines_from_no_block(self.splitted_lines)

        # checking if there's a "width" column, adding if not:
        if not widths_fieldname in get_column_names(self.splitted_lines):
            create_new_layerfield(self.splitted_lines,widths_fieldname)

        # filling empty widths with values in the table:
        widths_index = self.splitted_lines.fields().indexOf(widths_fieldname)
        higway_index = self.splitted_lines.fields().indexOf(highway_tag)


        with edit(self.splitted_lines):
            for feature in self.splitted_lines.getFeatures():
                feature_attrs_list = feature.attributes()

                # only fill if no value is present
                if not feature_attrs_list[widths_index]:
                    highway_tag_val = feature_attrs_list[higway_index]
                    self.splitted_lines.changeAttributeValue(feature.id(),widths_index,higway_valuestable_dict[highway_tag_val])
                    """
                        THX: https://gis.stackexchange.com/a/133669/49900

                        NEVER USE index from enumeration (ordinal) as feature key (ID), as sometimes it's not the actual feature key (ID)

                        index (idx) =/= id
                
                    """




        # adding layers to canvas:
        self.add_layer_canvas(self.filtered_intersection_points)
        self.add_layer_canvas(self.splitted_lines)


        # always cleaning stuff user does not need anymore
        remove_layerlist([osm_higway_layer_finalname])

        # enabling next button and stuff:
        self.dlg.generate_sidewalks.setEnabled(True)
        self.dlg.widths_hint.setHidden(False)
        if not self.no_buildings:
            self.dlg.check_if_overlaps_buildings.setEnabled(True)

        

        # self.replace_vectorlayer(osm_higway_layer_finalname,outputpath_splitted)

    def draw_sidewalks(self):

        # disabling what should not be used afterwards:
        self.dlg.check_if_overlaps_buildings.setEnabled(False)
        self.dlg.generate_sidewalks.setEnabled(False)



        # if no buildings, we can directly generate a simply dissolved-big_buffer
        if self.no_buildings or not self.dlg.check_if_overlaps_buildings.isChecked():
            dissolved_buffer = generate_buffer(self.splitted_lines)
            dissolved_buffer.setCrs(self.custom_localTM_crs)


            self.add_layer_canvas(dissolved_buffer)
        else:
            pass

    def string_according_language(self,en_str,ptbr_str):
        if self.current_lang == 'en':
            return en_str
        else:
            return ptbr_str

    def remove_temporary_layers(self):

        is_temporary = [layer.isTemporary() for layer in QgsProject.instance().mapLayers().values()]

        layer_fullnames = [layer for layer in QgsProject.instance().mapLayers()]

        for i,status in enumerate(is_temporary):
            if status:
                QgsProject.instance().removeMapLayer(layer_fullnames[i])


    # # def replace_vectorlayer(self,layername,newpath):
    # #     remove_layerlist([layername])

    # #     replaced =  QgsVectorLayer(newpath,layername,'ogr')

    # #     self.add_layer_canvas(replaced)

    def disable_all_because_sidewalks(self):
        # DISABLING STUFF, if there are sidewalks already drawn, one must step back!!

        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.dlg.datafetch.setEnabled(False)
        self.dlg.ch_ignore_buildings.setEnabled(False)
        self.dlg.ch_ignore_buildings.setChecked(False)
        self.dlg.input_layer_selector.setEnabled(False)
        self.dlg.higway_values_table.setEnabled(False)
        self.dlg.clean_data.setEnabled(False)
        self.dlg.output_file_selector.setEnabled(False)



        # objects that must be hidden:
        self.dlg.generate_sidewalks.setHidden(True)
        self.dlg.check_if_overlaps_buildings.setHidden(True)
        self.dlg.widths_hint.setHidden(True)




        # but enable the warning and the button:
        self.dlg.sidewalks_warning.setHidden(False)
        self.dlg.sidewalks_warning.setGeometry(270,180, 331, 281)

        self.dlg.ignore_already_drawn_btn.setHidden(False)
        self.dlg.ignore_already_drawn_btn.setEnabled(True)
        self.dlg.ignore_already_drawn_btn.setGeometry(300,450, 261, 71)
        # values from Qt Designer

    def ignore_already_drawn_fcn(self):
        self.ignore_sidewalks_already_drawn = True

        self.reset_fields(reset_ignore_alreadydrawn=False)





    def reset_fields(self,reset_ignore_alreadydrawn=True):
        # to be activated/deactivated/changed:
        self.dlg.input_layer_selector.setLayer(None)
        self.dlg.input_layer_selector.setEnabled(True)
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.dlg.datafetch.setEnabled(False)
        self.dlg.ch_ignore_buildings.setEnabled(False)
        self.dlg.ch_ignore_buildings.setChecked(False)
        self.dlg.higway_values_table.setEnabled(False)
        self.dlg.clean_data.setEnabled(False)
        self.dlg.sidewalks_warning.setHidden(True)
        self.dlg.widths_hint.setHidden(True)
        self.dlg.output_file_selector.setEnabled(False)
        self.dlg.generate_sidewalks.setEnabled(False)
        self.dlg.check_if_overlaps_buildings.setEnabled(False)
        self.dlg.ignore_already_drawn_btn.setEnabled(False)
        self.dlg.ignore_already_drawn_btn.setHidden(True)


        self.dlg.higway_values_table.setRowCount(0)
        self.dlg.higway_values_table.setColumnCount(0)

        # objects that always shall be visible
        self.dlg.generate_sidewalks.setHidden(False)
        self.dlg.check_if_overlaps_buildings.setHidden(False)
        self.dlg.widths_hint.setHidden(False)
        
        # control variables:
        if reset_ignore_alreadydrawn:
            self.ignore_sidewalks_already_drawn = False


        # texts, for appearance:
        self.set_text_based_on_language(self.dlg.input_status,'waiting a valid input...','aguardando uma entrada válida...',self.change_input_labels)
        self.set_text_based_on_language(self.dlg.input_status_of_data,'waiting for data...','aguardando dados...',self.change_input_labels)

        # also wipe data:
        self.remove_layers_and_wipe_files([osm_higway_layer_finalname,buildings_layername],temps_path)

        # remove temporary layers:
        self.remove_temporary_layers()

        # and refresh canvas:
        self.iface.mapCanvas().refresh()






    def get_input_layer(self):
        # self.input_layer = QgsMapLayerComboBox.currentLayer()
        self.input_layer = self.dlg.input_layer_selector.currentLayer()

        # .next()

        if self.input_layer:
            self.write_to_debug(self.input_layer.dataProvider().dataSourceUri())


            # assuring 4326 as EPSG code for layer
            layer_4326 = reproject_layer(self.input_layer)



            input_feature = QgsFeature()


            iterat = layer_4326.getFeatures()

            iterat.nextFeature(input_feature)

            if input_feature.hasGeometry():
                # TODO: beware of qgis bugs...


                if input_feature.isValid():
                    self.input_polygon = input_feature.geometry()

                    # self.write_to_debug(self.input_polygon.toWkt())

                    bbox = self.input_polygon.boundingBox()

                    # in order to create a local custom projection
                    self.bbox_center = bbox.center()

                    self.minLgt = bbox.xMinimum()
                    self.minLat = bbox.yMinimum()
                    self.maxLgt = bbox.xMaximum()
                    self.maxLat = bbox.yMaximum()


                    if self.input_polygon.isGeosValid():
                        # zooming to inputlayer:
                        self.iface.mapCanvas().setExtent(self.input_layer.extent())
                        self.iface.mapCanvas().refresh()



                        self.dlg.datafetch.setEnabled(True)
                        self.dlg.ch_ignore_buildings.setEnabled(True)

                        # self.change_input_labels = False
                        # self.dlg.input_status.setText('Valid Input!')
                        self.set_text_based_on_language(self.dlg.input_status,'Valid Input!','Entrada Válida!')
                        # self.dlg.input_status_of_data.setText('waiting for data...')
                        self.set_text_based_on_language(self.dlg.input_status_of_data,'waiting for data...','Aguardando Dados...')


                        for item in [self.minLgt,self.minLat,self.maxLgt,self.maxLat]:
                            self.write_to_debug(item)
            else:
                # self.dlg.input_status.setText('no geometries on input!!')
                self.set_text_based_on_language(self.dlg.input_status,'no geometries on input!!','Entrada sem geometrias!!')
                self.dlg.datafetch.setEnabled(False)
                self.dlg.ch_ignore_buildings.setEnabled(False)

        else:

            # self.dlg.input_status.setText('waiting a valid for input...')
            self.set_text_based_on_language(self.dlg.input_status,'Waiting for a valid input...','Aguardando entrada válida...')
            self.dlg.datafetch.setEnabled(False)
            self.dlg.ch_ignore_buildings.setEnabled(False)







        

    def remove_layers_and_wipe_files(self,layernamelist,folderpath=None):
        '''
            one can also pass no folderpath to just remove layerlist
        '''
       
        remove_layerlist(layernamelist)

        if folderpath:
            wipe_folder_files(folderpath)


    def call_get_osm_data(self):
        """
        Function to call the functions from "osm fetch" module
        """

        # PART 1 : wiping old stuff
        # delete files from previous session:
        #   and remove layers from project

        self.remove_layers_and_wipe_files([osm_higway_layer_finalname,buildings_layername],temps_path)
        self.remove_temporary_layers() # also temporary layers that can be around

        # PART 2: Getting and transforming the data
        self.dlg.datafetch.setEnabled(False)
        self.dlg.ch_ignore_buildings.setEnabled(False)


        # OSM query
        roads_layername = "osm_road_data"
        query_string = osm_query_string_by_bbox(self.minLat,self.minLgt,self.maxLat,self.maxLgt)
        # acquired file
        data_geojsonpath = get_osm_data(query_string,roads_layername)

        # self.dlg.input_status_of_data.setText('data acquired!')
        self.set_text_based_on_language(self.dlg.input_status_of_data,'data acquired!','Dados Obtidos!!')

        # to prevent user to loop
        self.dlg.input_layer_selector.setEnabled(False)


        clipped_path = data_geojsonpath.replace('.geojson','_clipped.geojson')

        clip_polygon_path = path_from_layer(self.input_layer)

        self.write_to_debug(clip_polygon_path)

        # adding as layer
        osm_data_layer = QgsVectorLayer(data_geojsonpath,roads_layername,"ogr")

        cliplayer(osm_data_layer,self.input_layer,clipped_path)


        clipped_datalayer = QgsVectorLayer(clipped_path,roads_layername,"ogr")

        # # Custom CRS, to use metric stuff with minimal distortion
        self.clipped_reproj_path = data_geojsonpath.replace('.geojson','_clipped_reproj.geojson')


        self.clipped_reproj_datalayer, self.custom_localTM_crs = reproject_layer_localTM(clipped_datalayer,self.clipped_reproj_path,osm_higway_layer_finalname,lgt_0=self.bbox_center.x())


        # # not the prettier way to get also the buildings (yes, could create a function, its not lazyness, I swear...):
        # # no need for clipping the buildings layer 

        if not self.dlg.ch_ignore_buildings.isChecked() and use_buildings:
            query_string_buildings = osm_query_string_by_bbox(self.minLat,self.minLgt,self.maxLat,self.maxLgt,'building',relation=include_relations)
            buildings_geojsonpath = get_osm_data(query_string_buildings,'osm_buildings_data','Polygon')
            buildings_brutelayer = QgsVectorLayer(buildings_geojsonpath,'brute_buildings','ogr')

            self.no_buildings = check_empty_layer(buildings_brutelayer) # asserts if there are buildings in the area

            # do not add buildings if there's no need
            if not self.no_buildings:
                
                self.dlg.check_if_overlaps_buildings.setChecked(True) # set as default option, since sidewalks can overlap buildings

                reproj_buildings_path = buildings_geojsonpath.replace('.geojson','_reproj.geojson')
                self.reproj_buildings, _ = reproject_layer_localTM(buildings_brutelayer,reproj_buildings_path,buildings_layername,lgt_0=self.bbox_center.x())
                if draw_buildings:
                    self.add_layer_canvas(self.reproj_buildings)

                buildings_centroids = gen_centroids_layer(self.reproj_buildings)
                # self.add_layer_canvas(centroids)

            # # # else:
            # # #     # as there's no problem in an empty layer, mostly for ease posterior merging
            #####       also, mergelayers function can accept a list with only one 
            # # #     centroids = centroids_layer(buildings_brutelayer)
            

            """
            # adresses parts (there are just points in osm database, generally from mapping agencies i.e. IBGE), 
            # should be joined with centroids 
            # and be the default method for sidewalk splitting
            """

            # mostly a clone of get buildings snippet
            query_string_addrs = osm_query_string_by_bbox(self.minLat,self.minLgt,self.maxLat,self.maxLgt,'addr:housenumber',node=True)
            addrs_geojsonpath = get_osm_data(query_string_addrs,'osm_addrs_data','Point')
            addrs_brutelayer = QgsVectorLayer(addrs_geojsonpath,'brute_buildings','ogr')

            self.no_addrs = check_empty_layer(addrs_brutelayer)

            if not self.no_addrs:
                reproj_addrs_path = addrs_geojsonpath.replace('.geojson','_reproj.geojson')
                self.reproj_addrs, _ = reproject_layer_localTM(addrs_brutelayer,reproj_addrs_path,'addrs_points',lgt_0=self.bbox_center.x())
                # self.add_layer_canvas(self.reproj_addrs)


            '''             
            now the cases to create combined layer w/wout centroids and adresses:
            both unavaliable: nothing to do, as there a variable @POI_split_avaliable already set for that case 
            both avaliable: merge 
            if only addrs, merge 
            if only centoids, merge
            '''

            if not self.no_buildings or not self.no_addrs:
                self.POI_split_avaliable = True

                layersto_merge = []

                if not self.no_buildings:
                    layersto_merge.append(buildings_centroids)

                if not self.no_addrs:
                    layersto_merge.append(self.reproj_addrs)

                pois_splitting_name = self.string_according_language('addrs_and_buildings_centroids','enderecos_e_centroides')

                self.POIs_for_splitting_layer = mergelayers(layersto_merge,self.custom_localTM_crs,'memory:'+pois_splitting_name)

                self.add_layer_canvas(self.POIs_for_splitting_layer)





            # elif self.no_buildings and not self.no_addrs:
            #     self.POI_split_avaliable = True

            # elif self.no_buildings and not self.no_addrs:
            #     self.POI_split_avaliable = True


        


            



                    

        # a little cleaning:
        remove_unconnected_lines(self.clipped_reproj_datalayer)


        # adding to canvas
        self.add_layer_canvas(self.clipped_reproj_datalayer)

        # PART 3: Getting Attributes and drawing table:
        higway_list = get_layercolumn_byname(self.clipped_reproj_datalayer,highway_tag)


        # Table Filling
        self.dlg.higway_values_table.setEnabled(True)

        self.unique_highway_values = list(set(higway_list))

        self.dlg.higway_values_table.setRowCount(len(self.unique_highway_values))
        self.dlg.higway_values_table.setColumnCount(2)

        if self.current_lang == 'en':
            self.dlg.higway_values_table.setHorizontalHeaderLabels(['tag value','width'])
        else:
            self.dlg.higway_values_table.setHorizontalHeaderLabels(['valor','largura'])


        # filling first colum --> higway:values and second --> defalt_values
        for i,item in enumerate(self.unique_highway_values):
            vvalue = self.unique_highway_values[i]

            self.dlg.higway_values_table.setItem(i,0,QTableWidgetItem(vvalue))

            self.dlg.higway_values_table.setItem(i,1,QTableWidgetItem(str(default_widths[vvalue])))


        


        # Finally, enabling next button:
        self.dlg.clean_data.setEnabled(True)

        # BUT... if there are sidewalks already drawn, one must step back!!
        if sidewalk_tag_value in self.unique_highway_values:
            # DISABLING STUFF
            if not self.ignore_sidewalks_already_drawn:
                self.disable_all_because_sidewalks()


        # # # testing if inverse transformation is working:
        # # self.add_layer_canvas(reproject_layer(self.clipped_reproj_datalayer))


    def set_text_based_on_language(self,qt_object,en_txt,ptbr_txt,extra_control_bool=True):
        if extra_control_bool:
            if self.current_lang == 'en':
                qt_object.setText(en_txt)
            else:
                qt_object.setText(ptbr_txt)


    def write_to_debug(self,input_stringable,add_newline=True):
        with open(self.session_debugpath,'a+') as session_report:
            session_report.write(str(input_stringable))
            if add_newline:
                session_report.write('\n')


