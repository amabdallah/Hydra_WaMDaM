# (c) Copyright 2013, 2014, University of Manchester
#
# HydraPlatform is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HydraPlatform is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with HydraPlatform.  If not, see <http://www.gnu.org/licenses/>
#
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import server
from lxml import etree
from subprocess import Popen, PIPE
import logging
import os
log = logging.getLogger(__name__)


class ServerPluginsTest(server.SoapServerTest):
    """
        Tests for server-side plugins.
    """
    def call_advanced_dataset_search(self):
        """
            Call the advanced dataset retrieval function.
        """

        network = self.create_network_with_data()

        scenario = network.scenarios.Scenario[0] 
        clone = self.client.service.clone_scenario(scenario.id)
        node_ids = [n.id for n in network.nodes.Node]
        link_ids = [l.id for l in network.links.Link]
        scenario_ids = [scenario.id, clone.id]
        attr_ids = [a.attr_id for a in network.nodes.Node[0].attributes.ResourceAttr]

        n_result_matrix = self.client.service.get_node_dataset_matrix(node_ids,
                                                                    attr_ids,
                                                                    scenario_ids)

        for nd in n_result_matrix[0]:
            for n in nd.nodes.MatrixResourceData:
                for a in n.attributes.MatrixResourceAttribute:
                    if not hasattr(a,  'dataset'):
                        print a

        l_result_matrix = self.client.service.get_link_dataset_matrix(link_ids,
                                                                    attr_ids,
                                                                    scenario_ids)

        for nd in l_result_matrix[0]:
            for l in nd.links.MatrixResourceData:
                for a in l.attributes.MatrixResourceAttribute:
                    if not hasattr(a,  'dataset'):
                        print a


        g_result_matrix = self.client.service.get_link_dataset_matrix(link_ids,
                                                                    attr_ids,
                                                                    scenario_ids)

        for nd in g_result_matrix[0]:
            for l in nd.groups.MatrixResourceData:
                for a in l.attributes.MatrixResourceAttribute:
                    if not hasattr(a,  'dataset'):
                        print a


class PluginsTest(server.SoapServerTest):
    """
        Test which runs a number of plugins 
    """
    def get_plugins(self):
        plugins = self.client.service.get_plugins()

        assert len(plugins[0]) > 0, "Plugins not retrieved correctly."

    def run_plugin(self):
        plugins = self.client.service.get_plugins()


        plugin_etrees = []
        for plugin in plugins[0]:
            plugin_etrees.append(etree.XML(plugin))

        for ptree in plugin_etrees:
            plugin_name = ptree.find('plugin_name').text
            print plugin_name
            if plugin_name == 'Test Plugin':
                #call the plugin
                plugin = self.client.factory.create('ns1:Plugin')

                plugin.name = plugin_name
                plugin.location = ptree.find('plugin_dir').text

                mandatory_args = ptree.find('mandatory_args')
                args = mandatory_args.findall('arg')

                for arg in args:
                    plugin_param = self.client.factory.create('ns1:PluginParam')
                    plugin_param.name = arg.find('name').text
                    plugin_param.value = 1
                    plugin.params.PluginParam.append(plugin_param)

                PID = self.client.service.run_plugin(plugin)
                print PID

                #Give the plugin a chance to execute.
                import time
                time.sleep(1)

                result = self.client.service.check_plugin_status(plugin_name, PID)

                print result

                break
        else:
            self.fail("Test plugin not found!")

    def test_CSV_Import_Export(self):
        #Import a network
        #Popen chosen instead of os.popen because it has greater control over waiting for
        #subprocesses to finish. (Important when waiting for files to be written before starting the next
        #piece of work
        if os.name == 'nt':
       	    stream = Popen('cd ..\\..\\..\\..\\HydraPlugins\\CSVplugin\\testdata\\hydro-econ & import_data', shell=True, stdout=PIPE)
       	else:
       	    stream = Popen('cd ../../../../HydraPlugins/CSVplugin/testdata/hydro-econ; ./import_data.sh', shell=True, stdout=PIPE)

        stream.wait()
        result_text = stream.stdout.readlines()
        xml_start = 1
        xml_end   = -1
        for i, r in enumerate(result_text):
            if r.find('<plugin_result>') == 0:
                xml_start = i
            if r.find('</plugin_result>') == 0:
                xml_end = i+1
        result = ''.join(result_text[xml_start:xml_end])
        tree = etree.XML(result.strip())
        print result
        assert tree.find('errors').getchildren() == []
        assert tree.find('warnings').getchildren() == []

        network_id = int(tree.find('network_id').text)
        #Export the network
        stream = Popen('python ../../../../HydraPlugins/CSVplugin/ExportCSV/ExportCSV.py -t %s'%network_id, shell=True); 
        stream.wait()
       
        #Re-import the network (this ensures that export csv worked correctly).
        network_file = "~/Desktop/network_hydro-econ/CSV_import/network.csv"
        stream = Popen('python ../../../../HydraPlugins/CSVplugin/ImportCSV/ImportCSV.py -t %s -x'%(network_file), shell=True, stdout=PIPE)
        stream.wait()
        updated_result_text = stream.stdout.readlines()
        xml_start = 1
        for i, r in enumerate(updated_result_text):
            if r.find('<plugin_result>') == 0:
                xml_start = i
                updated_result = ''.join(updated_result_text[xml_start:])
                break
        print updated_result
        updated_tree = etree.XML(updated_result)
        assert updated_tree.find('errors').getchildren() == []
        assert updated_tree.find('warnings').getchildren() == []

        Popen("rm -r ~/Desktop/network_*", shell=True)

        

if __name__ == '__main__':
    server.run()
