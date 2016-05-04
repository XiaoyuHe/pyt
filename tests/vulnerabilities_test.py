import os
import sys

sys.path.insert(1, os.path.abspath('../pyt'))
import vulnerabilities
from base_test_case import BaseTestCase
from cfg import CFG, generate_ast, Node
from fixed_point import analyse
from reaching_definitions import ReachingDefinitionsAnalysis


class EngineTest(BaseTestCase):
    def run_empty(self):
        return
    
    def test_parse(self):
        definitions = vulnerabilities.parse(trigger_word_file=os.path.join(os.getcwd().replace('tests','pyt'), 'trigger_definitions', 'test_triggers.pyt'))

        self.assert_length(definitions.sources, expected_length=1)
        self.assert_length(definitions.sinks, expected_length=3)
        self.assert_length(definitions.sinks[0][1], expected_length=1)
        self.assert_length(definitions.sinks[1][1], expected_length=3)

    def test_parse_section(self):
        l = list(vulnerabilities.parse_section(iter(['get'])))
        self.assert_length(l, expected_length=1)
        self.assertEqual(l[0][0], 'get')
        self.assertEqual(l[0][1], list())

        l = list(vulnerabilities.parse_section(iter(['get', 'get -> a, b, c d s aq     a'])))
        self.assert_length(l, expected_length=2)
        self.assertEqual(l[0][0], 'get')
        self.assertEqual(l[1][0], 'get')
        self.assertEqual(l[1][1], ['a', 'b', 'c d s aq     a'])
        self.assert_length(l[1][1], expected_length=3)

    def test_label_contains(self):
        cfg_node = Node('label', None, None, line_number=None)
        trigger_words = [('get', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=0)

        cfg_node = Node('request.get("stefan")', None, None, line_number=None)
        trigger_words = [('get', []), ('request', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=2)

        trigger_node_1 = l[0]
        trigger_node_2 = l[1]
        self.assertEqual(trigger_node_1.trigger_word, 'get')
        self.assertEqual(trigger_node_1.cfg_node, cfg_node)
        self.assertEqual(trigger_node_2.trigger_word, 'request')
        self.assertEqual(trigger_node_2.cfg_node, cfg_node)
        
        cfg_node = Node('request.get("stefan")', None, None, line_number=None)
        trigger_words = [('get', []), ('get', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=2)

    def test_find_triggers(self):
        cfg = CFG()
        tree = generate_ast('../example/vulnerable_code/XSS.py')
        cfg.create(tree)

        trigger_words = [('get', [])]

        l = vulnerabilities.find_triggers(cfg.functions['XSS1'], trigger_words)
        self.assert_length(l, expected_length=1)
        

    def test_find_sanitiser_nodes(self):
        cfg_node = Node(None, None, None, line_number=None)
        sanitiser_tuple  = vulnerabilities.Sanitiser('escape', cfg_node)
        sanitiser = 'escape'

        result = list(vulnerabilities.find_sanitiser_nodes(sanitiser, [sanitiser_tuple]))
        self.assert_length(result, expected_length=1)
        self.assertEqual(result[0], cfg_node)
        
        
    def test_build_sanitiser_node_dict(self):
        cfg = CFG()
        tree = generate_ast('../example/vulnerable_code/XSS_sanitised.py')
        cfg.create(tree)
        cfg = cfg.functions['XSS1']
        cfg_node = Node(None, None, None, line_number=None)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node)]

        sanitiser_dict = vulnerabilities.build_sanitiser_node_dict(cfg, sinks_in_file)
        self.assert_length(sanitiser_dict, expected_length=1)
        self.assertIn('escape', sanitiser_dict.keys())
        self.assertEqual(sanitiser_dict['escape'][0], cfg.nodes[2])

    def test_is_sanitized_false(self):
        cfg_node_1 = Node('Not sanitising at all', None, None, line_number=None)
        cfg_node_2 = Node('something.replace("this", "with this")', None, None, line_number=None)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node_2)]
        sanitiser_dict = {'escape': [cfg_node_1]}

        result = vulnerabilities.is_sanitized(sinks_in_file[0], sanitiser_dict)
        self.assertEqual(result, False)

    def test_is_sanitized_true(self):
        cfg_node_1 = Node('Awesome sanitiser', None, None, line_number=None)
        cfg_node_2 = Node('something.replace("this", "with this")', None, None, line_number=None)
        cfg_node_2.new_constraint.add(cfg_node_1)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node_2)]
        sanitiser_dict = {'escape': [cfg_node_1]}

        result = vulnerabilities.is_sanitized(sinks_in_file[0], sanitiser_dict)
        self.assertEqual(result, True)

    def test_find_vulnerabilities_sanitised(self):
        cfg = CFG()
        tree = generate_ast('../example/vulnerable_code/XSS_sanitised.py')
        cfg.create(tree)
        cfg_list = [cfg, cfg.functions['XSS1']]

        analyse(cfg_list, analysis_type=ReachingDefinitionsAnalysis)

        vulnerability_log = vulnerabilities.find_vulnerabilities(cfg_list)
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=0)
        
    def test_find_vulnerabilities_vulnerable(self):
        cfg = CFG()
        tree = generate_ast('../example/vulnerable_code/XSS.py')
        cfg.create(tree)
        cfg_list = [cfg, cfg.functions['XSS1']]

        analyse(cfg_list, analysis_type=ReachingDefinitionsAnalysis)

        vulnerability_log = vulnerabilities.find_vulnerabilities(cfg_list)
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)